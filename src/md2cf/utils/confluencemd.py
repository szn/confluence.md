import re
import os

from typing import List, Tuple, Union, Any

import atlassian
import markdown2

from .log import logger

CF_URL = re.compile(r"(?P<host>https?://[^/]+)/.*/(?P<page_id>\d+)")
IMAGE_PATTERN = re.compile(r"\!\[(?P<alt>.*)\]\((?P<path>.*)\)")


class ConfluenceMD(atlassian.Confluence):
    def __init__(
        self,
        username: str,
        token: str,
        md_file: str,
        url: str = None,
        add_meta: bool = False,
        add_info_panel: bool = False,
        add_label: str = None,
    ) -> None:
        self.username = username
        self.token = token
        self.md_file = md_file
        self.url = url
        self.add_meta = add_meta
        self.add_info_panel = add_info_panel
        self.add_label = add_label

        if url:
            self.init()

    def init(self):
        super().__init__(url=self.url, username=self.username, password=self.token)

    def rewrite_images(
        self, page_id: str, html: str, images: List[Tuple[str, str]]
    ) -> str:
        for (alt, path) in images:
            logger.debug("register image file `%s`", path)
            self.attach_file(filename=path, page_id=page_id)
            old = f'<img src="{path}" alt="{alt}" />'
            new = f'<ac:image> <ri:attachment ri:filename="{os.path.basename(path)}" /> </ac:image>'
            if html.find(old) != -1:
                logger.debug("replace image tag `%s` with `%s`", old, new)
                html = html.replace(old, new)
            else:
                logger.warning("image tag `%s` not found in html", old)
        return html

    def update_existing(self, page_id: str = None) -> None:
        logger.debug("Updating page `%s` based on `md_file` file", page_id)
        html, images, page_id_from_meta, url = self.md_file_to_html()

        if page_id is None:
            logger.debug("Using `page_id` from `%s` file", self.md_file)
            page_id = page_id_from_meta

        assert page_id, (
            f"Can't update page without page_id given either by "
            f"`--page_id` parameter or via `confluence-url` tag in `{self.md_file}` file"
        )

        if self.url is None:
            logger.debug("Using URL (%s) from `%s` file", url, self.md_file)
            self.url = url
            assert self.url, (
                f"Can't update page without url given either by "
                f"`--url` parameter or via `confluence-url` tag in `{self.md_file}` file`"
            )
            self.init()

        title = self.get_page_title_by_id(page_id)
        html = self.rewrite_images(page_id, html, images)

        logger.debug("Updating page_id `%s` titled `%s`", page_id, title)
        response = self.update_page(
            page_id,
            title,
            html,
            parent_id=None,
            type="page",
            representation="storage",
            minor_edit=True,
        )

        if self.add_meta:
            confluence_url = ConfluenceMD.get_link_from_response(response)
            self.add_meta_to_file(confluence_url)

        if self.add_label:
            self.add_label_to_page(page_id)

    def create_page(self, parent_id: str, title: str, overwrite: bool) -> None:
        assert title, "Provide a title for a newly created page"
        assert parent_id, "Provide parent_id for a newly created page"
        space = self.get_page_space(parent_id)

        page_id = None
        if self.page_exists(space, title):
            page_id = self.get_page_id(space, title)
            assert overwrite, (
                f"Page titled `{title}` already exists in "
                f"the `{space}` space. Use --overwrite to force it."
            )

        html, images, page_id_from_meta, _url = self.md_file_to_html()
        assert not page_id_from_meta or overwrite, (
            f"Metadata pointing to an existing page "
            f"id `{page_id_from_meta}` present in the given markdown file. "
            f"Use --overwrite to force it."
        )

        overwrite = page_id or page_id_from_meta

        if overwrite:
            logger.debug(
                "Overwriting existing page `%s` based on `%s` file", title, self.md_file
            )
            html = self.rewrite_images(page_id or page_id_from_meta, html, images)
            response = self.update_page(
                page_id or page_id_from_meta,
                title,
                html,
                parent_id=None,
                type="page",
                representation="storage",
                minor_edit=True,
            )
        else:
            logger.debug("Creating new page `%s` based on `%s` file", title, self.md_file)
            response = atlassian.Confluence.create_page(
                self,
                space,
                title,
                body=html,
                parent_id=parent_id,
                type="page",
                representation="storage",
                editor="v2",
            )
            if len(images) > 0:
                logger.debug("Uploading images to newly created page")
                page_id = ConfluenceMD.get_page_id_from_response(response)
                html = self.rewrite_images(page_id, html, images)
                response = self.update_page(
                    page_id,
                    title,
                    html,
                    parent_id=None,
                    type="page",
                    representation="storage",
                    minor_edit=True,
                )

        confluence_url = ConfluenceMD.get_link_from_response(response)
        logger.debug(
            "%s %s", 'Page overwritten' if overwrite else 'New page created', confluence_url
        )

        self.add_meta_to_file(confluence_url)

        page_id = ConfluenceMD.get_page_id_from_response(response)
        self.add_label_to_page(page_id)

    @staticmethod
    def get_link_from_response(response) -> str:
        return response["_links"]["base"] + response["_links"]["webui"]

    @staticmethod
    def get_page_id_from_response(response) -> str:
        return response["id"]

    def add_meta_to_file(self, confluence_url: str) -> None:
        if not self.add_meta:
            return

        md = ConfluenceMD.get_file_contents(self.md_file)
        md = ("---\n" f"confluence-url: {confluence_url}\n" "---\n") + md

        with open(self.md_file, "w", encoding="utf-8") as stream:
            stream.write(md)

    def get_page_title_by_id(self, page_id: str) -> str:
        logger.debug("Getting page title from page id `%s`", page_id)
        return self.get_page_by_id(page_id)["title"]

    @staticmethod
    def get_file_contents(file: str) -> str:
        with open(file, "r", encoding="utf-8") as stream:
            return stream.read()

    def md_file_to_html(self) -> Tuple[Any, List[Tuple[str, str]], Union[str, Any], Union[str, Any]]:
        logger.debug("Converting MD to HTML")
        content = self.get_file_contents(self.md_file)
        images = []
        for image in IMAGE_PATTERN.finditer(content):
            images.append((image.group("alt"), image.group("path")))

        html = markdown2.markdown_path(
            path=self.md_file,
            extras=[
                "metadata",
                "strike",
                "tables",
                "wiki-tables",
                "code-friendly",
                "fenced-code-blocks",
                "footnotes",
            ],
        )

        page_id_from_meta, url = ConfluenceMD.parse_confluence_url(html.metadata)
        if self.add_info_panel:
            html = self.get_info_panel() + html
        return html, images, page_id_from_meta, url

    @staticmethod
    def parse_confluence_url(meta: str) -> Tuple[Union[str, None], Union[str, None]]:
        if "confluence-url" not in meta:
            return (None, None)

        url = meta["confluence-url"]

        logger.debug("Looking for host and page_id in %s url", url)
        cf_url = CF_URL.search(url)
        if cf_url:
            page_id = cf_url.group("page_id")
            host = cf_url.group("host")
            logger.debug("  found page_id `%s` and host `%s`", page_id, host)
            return (page_id, host)
        logger.debug("  no valid Confluence url found")
        return (None, None)

    def add_label_to_page(self, page_id: str) -> None:
        if not self.add_label:
            return
        self.set_page_label(page_id, self.add_label)

    def get_info_panel(self):
        return f"""<p><strong>Automatic content</strong> This page was generated automatically from <code>{self.md_file}</code> file.
        Do not edit it on Confluence.</p><hr />
        """

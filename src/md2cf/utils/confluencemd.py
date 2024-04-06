import re
import os

from typing import Any, List, Tuple, Optional, Dict

import atlassian
import markdown2

from .log import logger
import requests
from  urllib import parse

CF_URL = re.compile(r"(?P<host>https?://[^/]+)/.*/(?P<page_id>\d+)")
IMAGE_PATTERN = re.compile(r"\!\[(?P<alt>.*)\]\((?P<path>[^:)]+)\)")
ISSUE_PATTERN = re.compile(r"\[(?P<key>\w[\w\d]*-\d+)\]")
ISSUE_PATTERN_URL = re.compile(r"(?P<domain>https:\/\/\w+\.atlassian\.net)\/browse\/(?P<key>\w[\w\d]*-\d+)")

class ConfluenceMD(atlassian.Confluence):
    def __init__(
        self,
        username: str,
        md_file: str,
        token: str = '',
        password: str = '',
        url: str = None,
        verify_ssl: bool = True,
        add_meta: bool = False,
        add_info_panel: bool = False,
        add_label: str = None,
        convert_jira: bool = False
    ) -> None:
        
        super().__init__(
            url=url,
            username=username,
            password=(password or token),
            verify_ssl=verify_ssl,
            cloud=bool(token),
            token=token,
        )

        if convert_jira:
            self.__init_jira(
                url=url,
                username=username,
                password=(password or token),
                verify_ssl=verify_ssl,
                token=token
            )
        self.md_file = md_file
        self.add_meta = add_meta
        self.add_info_panel = add_info_panel
        self.add_label = add_label
        self.md_file_dir = os.path.dirname(md_file)
        self.convert_jira = convert_jira

    def rewrite_issues(self, html: str) -> str:
        if not self.convert_jira:
            return html
        logger.debug("Replacing [ISSUE-KEY] with html links")
        issues = []
        for issue in ISSUE_PATTERN.finditer(html):
            issues.append((issue.group(), issue.group("key")))
        for issue in ISSUE_PATTERN_URL.finditer(html):
            if self.url.startswith(issue.group("domain")):
                issues.append((issue.group(), issue.group("key")))
            else:
                logger.info("Ignoring %s - domain mismatch (%s != %s)", issue.group(), issue.group("domain"), self.url)

        for (replace, key) in issues:
            logger.debug(f"  - [{key}] with html link")
            (summary, status, issuetypeurl) = self.__get_jira_issue(key)
            if summary:
                html = html.replace(replace,
                    f"<a href=\"{self.url}/browse/{key}\"><ac:image><ri:url ri:value=\"{issuetypeurl}\" /></ac:image> {key}: {summary} [{status}]</a>")
        return html

    def __get_jira_issue(self, key: str) -> tuple:
        try:
            issue = self.jira.issue(key)
            summary = issue['fields']['summary']
            status = issue['fields']['status']['name']
            issuetypeurl = issue['fields']['issuetype']['iconUrl']
            return (summary, status, issuetypeurl)
        except (RuntimeError, AssertionError, Exception) as error:
            logger.info("Unable to convert %s to Jira link: %s", key, error)
            return (None, None, None)

    def __rewrite_images(
        self, html: str, images: List[Tuple[str, str]]
    ) -> str:
        """Replaces <img> html tags with Confluence specific <ac:image> and uploads
           images as attachements"""
        for (alt, path) in images:
            rel_path = os.path.join(self.md_file_dir, path)
            if not os.path.isfile(rel_path):
                assert os.path.isfile(path), f"File `{path}` does not exist"
                logger.warning("file `%s` does not exist, using file relative to current dir `%s`", rel_path, path)
                rel_path = path

            old = f'<img src="{path}" alt="{alt}" />'
            new = f'<ac:image> <ri:attachment ri:filename="{os.path.basename(rel_path)}" /> </ac:image>'
            if html.find(old) != -1:
                logger.debug("replace image tag `%s` with `%s`", old, new)
                html = html.replace(old, new)
            else:
                logger.warning("image tag `%s` not found in html", old)
        return html

    def __attach_images(
            self, page_id: str, images: List[Tuple[str, str]]
    ) -> None:
        self.jira = atlassian.Jira(
                url=url,
                username=username,
                password=(password or token),
                verify_ssl=verify_ssl,
                cloud=bool(token),
                token=token
            )
        self.license = False
        try:
            uri = parse.urljoin(url, 'wiki/rest/atlassian-connect/1/addons/confluence.md')
            res = requests.get(uri, auth=(username, password or token))
            license = res.json()
            if res.status_code != 200:
                logger.error(license)
                return
            self.license = license["license"]["active"]
        except (RuntimeError, AssertionError, Exception) as error:
            logger.error(error)

    def update_existing(self, page_id: str = None) -> None:
        """Updates an existing page by given page_id"""
        logger.debug("Updating page `%s` based on `md_file` file", page_id)
        html, page_id_from_meta, url, _has_images = self.__md_file_to_html()
        images = self.__get_images_from_file()
        self.__attach_images(page_id, images)

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

        title = self.__get_page_title_by_id(page_id)

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
            confluence_url = ConfluenceMD.__get_link_from_response(response)
            self.__add_meta_to_file(confluence_url)

        if self.add_label:
            self.__add_label_to_page(page_id)

    def create_page(self, parent_id: str, title: str, overwrite: bool) -> None:
        """Creates a new page under give parent_id"""
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

        html, page_id_from_meta, _url, has_images = self.__md_file_to_html()
        assert not page_id_from_meta or overwrite, (
            f"Metadata pointing to an existing page "
            f"id `{page_id_from_meta}` present in the given markdown file. "
            f"Use --overwrite to force it."
        )

        overwrite_id = page_id if page_id else page_id_from_meta

        if overwrite_id:
            logger.debug(
                "Overwriting existing page `%s` based on `%s` file", title, self.md_file
            )
            response = self.update_page(
                overwrite_id,
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
            if has_images:
                logger.debug("Uploading images to newly created page")
                page_id = ConfluenceMD.__get_page_id_from_response(response)
                images = self.__get_images_from_file()
                self.__attach_images(page_id, images)

        confluence_url = ConfluenceMD.__get_link_from_response(response)
        logger.debug(
            "%s %s", 'Page overwritten' if overwrite_id else 'New page created', confluence_url
        )

        self.__add_meta_to_file(confluence_url)

        page_id = ConfluenceMD.__get_page_id_from_response(response)
        self.__add_label_to_page(page_id)

    def __rewrite_issues(self, html):
        if self.convert_jira:
            logger.debug("Replacing [ISSUE-KEY] with html links")

        issues = []
        for issue in ISSUE_PATTERN.finditer(html):
            issues.append((issue.group(), issue.group("key")))
        for issue in ISSUE_PATTERN_URL.finditer(html):
            if self.url.startswith(issue.group("domain")):
                issues.append((issue.group(), issue.group("key")))
            else:
                if self.convert_jira:
                    logger.info("Ignoring %s - domain mismatch (%s != %s)", issue.group(), issue.group("domain"), self.url)
        
        if len(issues) and not self.convert_jira:
            (replace, key) = issues[0]
            logger.info("Use --convert_jira to replace %i Jira link(s) (such as %s) with issue snippets - KEY: summary [status]",
                        len(issues), key)
            return html

        for (replace, key) in issues:
            logger.debug(f"  - [{key}] with html link")
            (summary, status, issuetypeurl) = self.__get_jira_issue(key)
            if summary:
                html = html.replace(replace,
                    f"<a href=\"{self.url}/browse/{key}\"><ac:image><ri:url ri:value=\"{issuetypeurl}\" /></ac:image> {key}: {summary} [{status}]</a>")
        return html

    def __get_jira_issue(self, key: str) -> tuple:
        try:
            issue = self.jira.issue(key)
            summary = issue['fields']['summary']
            status = issue['fields']['status']['name']
            issuetypeurl = issue['fields']['issuetype']['iconUrl']
            return (summary, status, issuetypeurl)
        except (RuntimeError, AssertionError, Exception) as error:
            logger.info("Unable to convert %s to Jira link: %s", key, error)
            return (None, None, None)

    def __rewrite_images(
        self, html: str, images: List[Tuple[str, str]]
    ) -> str:
        """Replaces <img> html tags with Confluence specific <ac:image> and uploads
           images as attachements"""
        for (alt, path) in images:
            rel_path = os.path.join(self.md_file_dir, path)
            if not os.path.isfile(rel_path):
                assert os.path.isfile(path), f"File `{path}` does not exist"
                logger.warning("file `%s` does not exist, using file relative to current dir `%s`", rel_path, path)
                rel_path = path

            old = f'<img src="{path}" alt="{alt}" />'
            new = f'<ac:image> <ri:attachment ri:filename="{os.path.basename(rel_path)}" /> </ac:image>'
            if html.find(old) != -1:
                logger.debug("replace image tag `%s` with `%s`", old, new)
                html = html.replace(old, new)
            else:
                logger.warning("image tag `%s` not found in html", old)
        return html

    def __attach_images(
            self, page_id: str, images: List[Tuple[str, str]]
    ) -> None:
        """Replaces <img> html tags with Confluence specific <ac:image> and uploads
           images as attachements"""
        for (alt, path) in images:
            rel_path = os.path.join(self.md_file_dir, path)
            if not os.path.isfile(rel_path):
                assert os.path.isfile(path), f"File `{path}` does not exist"
                logger.warning("file `%s` does not exist, using file relative to current dir `%s`", rel_path, path)
                rel_path = path

            logger.debug("register image file `%s`", rel_path)
            self.attach_file(filename=rel_path, page_id=page_id)

    @staticmethod
    def __get_link_from_response(response) -> str:
        """Returns URL to page from Confluence API response"""
        return response["_links"]["base"] + response["_links"]["webui"]

    @staticmethod
    def __get_page_id_from_response(response) -> str:
        """Returns page_id from Confluence API response"""
        return response["id"]

    def __add_meta_to_file(self, confluence_url: str) -> None:
        """Decorates markdown file with metadata in comments"""
        if not self.add_meta:
            return

        markdown = ConfluenceMD.__get_file_contents(self.md_file)
        markdown = ("---\n" f"confluence-url: {confluence_url}\n" "---\n") + markdown

        with open(self.md_file, "w", encoding="utf-8") as stream:
            stream.write(markdown)

    def __get_page_title_by_id(self, page_id: str) -> str:
        """Returns page title by given page_id"""
        logger.debug("Getting page title from page id `%s`", page_id)
        page = self.get_page_by_id(page_id)
        assert "title" in page, f"Expected page-object while getting page by id, got {page}"
        return page["title"]

    @staticmethod
    def __get_file_contents(file: str) -> str:
        """Return file contents"""
        with open(file, "r", encoding="utf-8") as stream:
            return stream.read()

    def __md_file_to_html(self) -> Tuple[Any, Optional[str], Optional[str], bool]:
        """Converts given md_file to html"""

        logger.debug("Converting MD to HTML")
        images = self.__get_images_from_file()

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
        page_id_from_meta, url = ConfluenceMD.__parse_confluence_url(html.metadata)
        if self.add_info_panel:
            html = self.__get_info_panel() + html

        html = self.__rewrite_issues(html)
        html = self.__rewrite_images(html, images)
        return html, page_id_from_meta, url, len(images) > 0

    @staticmethod
    def __parse_confluence_url(meta: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
        """Parses Confluence page URL and returns page_id and host"""
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

    def __get_images_from_file(self) -> List:
        logger.debug("Getting list of images from MD file")
        content = self.__get_file_contents(self.md_file)
        images = []
        for image in IMAGE_PATTERN.finditer(content):
            images.append((image.group("alt"), image.group("path")))
        return images

    def __add_label_to_page(self, page_id: str) -> None:
        """Selfdescriptive"""
        if not self.add_label:
            return
        self.set_page_label(page_id, self.add_label)

    def __get_info_panel(self) -> str:
        """Returns str with html info page to be placed on a Confluence page if --add_info is added"""
        return f"""<p><strong>Automatic content</strong> This page was generated automatically from <code>{self.md_file}</code> file.
        Do not edit it on Confluence.</p><hr />
        """

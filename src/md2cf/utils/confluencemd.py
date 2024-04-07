"""
Confluence to Markdown utility
"""
import os
import re
from  urllib import parse
from typing import List, Tuple
import requests

import atlassian

from .log import logger
from .md2html import md_to_html

ISSUE_PATTERN_KEY = re.compile(r"\[(?P<key>\w[\w\d]*-\d+)\]")
ISSUE_PATTERN_URL = re.compile(r"(?P<domain>https:\/\/\w+\.atlassian\.net)"
                               r"\/browse\/(?P<key>\w[\w\d]*-\d+)")

class ConfluenceMD(atlassian.Confluence):
    """Confluence to Markdown utility class"""

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

    def __init_jira(self,
                    url: str,
                    username: str,
                    password: str,
                    verify_ssl: bool,
                    token: str):
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
            res = requests.get(uri, auth=(username, password or token), timeout=30)
            license_obj = res.json()
            if res.status_code != 200:
                logger.error(license_obj)
                return
            self.license = license_obj["license"]["active"]
        # pylint: disable=broad-exception-caught
        except (RuntimeError, AssertionError, Exception) as error:
            logger.error(error)

    def update_existing(self, page_id: str = None) -> None:
        """Updates an existing page by given page_id"""
        logger.debug("Updating page `%s` based on `md_file` file", page_id)
        html, page_id_from_meta, url, images = md_to_html(self.md_file, self.add_info_panel)
        html = self.__rewrite_issues(html)
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

        html, page_id_from_meta, _url, images = md_to_html(self.md_file, self.add_info_panel)
        html = self.__rewrite_issues(html)
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
            if images:
                logger.debug("Uploading images to newly created page")
                page_id = ConfluenceMD.__get_page_id_from_response(response)
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
        for issue in ISSUE_PATTERN_KEY.finditer(html):
            issues.append((issue.group(), issue.group("key")))
        for issue in ISSUE_PATTERN_URL.finditer(html):
            if self.url.startswith(issue.group("domain")):
                issues.append((issue.group(), issue.group("key")))
            else:
                if self.convert_jira:
                    logger.info("Ignoring %s - domain mismatch (%s != %s)",
                                issue.group(),
                                issue.group("domain"),
                                self.url)

        if issues and not self.convert_jira:
            (replace, key) = issues[0]
            logger.info("Use --convert_jira to replace %i Jira link(s) (such as %s) "
                        "with issue snippets - KEY: summary [status]",
                        len(issues), key)
            return html

        for (replace, key) in issues:
            logger.debug("  - [%s] with html link", key)
            (summary, status, issuetypeurl) = self.__get_jira_issue(key)
            if summary:
                html = html.replace(replace,
                    f"<a href=\"{self.url}/browse/{key}\"><ac:image>"
                    f"<ri:url ri:value=\"{issuetypeurl}\" />"
                    f"</ac:image> {key}: {summary} [{status}]</a>")
        return html

    def __get_jira_issue(self, key: str) -> tuple:
        try:
            issue = self.jira.issue(key)
            summary = issue['fields']['summary']
            status = issue['fields']['status']['name']
            issuetypeurl = issue['fields']['issuetype']['iconUrl']
            return (summary, status, issuetypeurl)
        # pylint: disable=broad-exception-caught
        except (RuntimeError, AssertionError, Exception) as error:
            logger.info("Unable to convert %s to Jira link: %s", key, error)
            return (None, None, None)

    def __attach_images(
            self, page_id: str, images: List[Tuple[str, str]]
    ) -> None:
        """Replaces <img> html tags with Confluence specific <ac:image> and uploads
           images as attachements"""
        for (_alt, path) in images:
            rel_path = os.path.join(self.md_file_dir, path)
            if not os.path.isfile(rel_path):
                assert os.path.isfile(path), f"File `{path}` does not exist"
                logger.warning("File `%s` does not exist, using file relative "
                               "to current dir `%s`", rel_path, path)
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


    def __add_label_to_page(self, page_id: str) -> None:
        """Selfdescriptive"""
        if not self.add_label:
            return
        self.set_page_label(page_id, self.add_label)

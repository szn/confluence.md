"""
Automatic tests for Confluence.md
"""
import logging
from  urllib import parse

import pytest
import requests

from atlassian.errors import ApiError
from src.md2cf.utils.confluencemd import ConfluenceMD


log = logging.getLogger("net.dirtyagile.confluence.md")
log.setLevel('DEBUG')

# pylint: disable=missing-function-docstring,missing-class-docstring
class TestConfluenceMD:
    url: str = None
    auth = None

    def __confluence_request(self, method: str, endpoint: str):
        response = requests.request(
            method,
            parse.urljoin(self.url, endpoint),
            headers={ "Accept": "application/json" },
            auth=self.auth,
            timeout=10
        )
        if response.text:
            return response.json()
        return None

    def __get_child_pages(self, parent_id: str) -> list:
        return self.__confluence_request("GET", f'api/v2/pages/{parent_id}/children')

    def __delete_page(self, page_id: str) -> None:
        self.__confluence_request("DELETE", f"api/v2/pages/{page_id}")

    def __get_page(self, page_id: str):
        page = self.__confluence_request("GET", f'api/v2/pages/{page_id}?body-format=storage')
        return page['body']['storage']['value']

    @pytest.fixture(autouse=True)
    def cleanup(self, url, user, token):
        self.url = url
        self.auth = requests.auth.HTTPBasicAuth(user, token)
        # https://dirtyagile.atlassian.net/wiki/spaces/AD/pages/1115881473/Pytests
        pytests_id = 1115881473
        test_pages = self.__get_child_pages(pytests_id)
        for page in test_pages['results']:
            if page['status'] == 'current':
                self.__delete_page(page['id'])

    @staticmethod
    def init_confluencemd(user: str, token: str, url: str, md_file: str,
                          convert_jira: bool=False) -> None:
        return ConfluenceMD(username=user,
                            md_file=md_file,
                            token=token,
                            url=url,
                            convert_jira=convert_jira)

    def test_create_page(self, capsys, caplog, user, token, url):
        md_file = "src/tests/test_basic.md"
        title = "Basic test"
        conf_md = TestConfluenceMD.init_confluencemd(user=user, token=token, url=url,
                                                     md_file=md_file)
        with pytest.raises(AssertionError, match=r"Provide parent_id for a newly created page"):
            conf_md.create_new("", title, None)

        with pytest.raises(AssertionError, match=r"Provide a title for a newly created page"):
            conf_md.create_new("1115881473", "", None)

        with pytest.raises(ApiError, match=r"There is no content with the given id.*"):
            conf_md.create_new("1", title, False)

        page_id = conf_md.create_new("1115881473", title, False)
        page_content = self.__get_page(page_id)
        assert title in page_content

        with pytest.raises(AssertionError, match=r"Page titled `Basic test` already exists.*"):
            conf_md.create_new("1115881473", title, False)

        captured = capsys.readouterr()
        assert captured.out == ""

        for record in caplog.records:
            assert record.levelname == "DEBUG"
        assert f"Creating new page `{title}` based on `{md_file}` file"
        assert "New page created" in caplog.text
        assert f"{page_id}" in caplog.text

    def test_create_page_metadata(self, user, token, url):
        conf_md = TestConfluenceMD.init_confluencemd(user=user, token=token, url=url,
                                                     md_file="src/tests/test_metadata.md")
        with pytest.raises(AssertionError, match=r"Metadata pointing to an existing page id.*"):
            conf_md.create_new("1115881473", "Basic test 2", False)

    def test_jira_links(self, capsys, caplog, user, token, url):
        title = "Jira test"
        conf_md = TestConfluenceMD.init_confluencemd(user=user, token=token, url=url,
                                                     md_file="src/tests/test_jira.md")

        page_id = conf_md.create_new("1115881473", title, False)
        page_content = self.__get_page(page_id)
        assert title in page_content
        assert '<p>[KEY-1]</p>' in page_content

        captured = capsys.readouterr()
        assert captured.out == ""

        for record in caplog.records:
            assert record.levelname in ["INFO", "DEBUG"]
        assert "Use `--convert_jira` to replace 3 Jira link" in caplog.text

        conf_md = TestConfluenceMD.init_confluencemd(user=user, token=token, url=url,
                                                     md_file="src/tests/test_jira.md",
                                                     convert_jira=True)
        page_id = conf_md.create_new("1115881473", title, True)
        page_content = self.__get_page(page_id)
        assert title in page_content
        assert '<p>[KEY-1]</p>' in page_content
        assert 'AD-120: Atlassian Bug Bounty programm [In Progress]' in page_content


    def test_wrong_images(self, user, token, url):
        conf_md = TestConfluenceMD.init_confluencemd(user=user, token=token, url=url,
                                                     md_file="src/tests/test_images.md")

        with pytest.raises(FileNotFoundError,
                           match=r"No such file or directory: 'src/tests/test_images.md'"):
            conf_md.create_new("1115881473", "Images test", True)

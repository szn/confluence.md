"""
Automatic tests for Confluence.md
"""
import logging
import pytest


from atlassian.errors import ApiError
from src.md2cf.utils.confluencemd import ConfluenceMD

logging.getLogger("net.dirtyagile.confluence.md").setLevel('DEBUG')

# pylint: disable=missing-function-docstring,missing-class-docstring
class TestConfluenceMD:

    @staticmethod
    def init_confluencemd(user, token, md_file):
        return ConfluenceMD(username=user,
                            md_file=md_file,
                            token=token,
                            url="https://dirtyagile.atlassian.net/wiki/")

    def test_create_page(self, capsys, caplog, user, token):
        conf_md = TestConfluenceMD.init_confluencemd(user, token, "src/tests/test_basic.md")
        with pytest.raises(AssertionError, match=r"Provide parent_id for a newly created page"):
            conf_md.create_page("", "Basic test", None)

        with pytest.raises(AssertionError, match=r"Provide a title for a newly created page"):
            conf_md.create_page("1115881473", "", None)

        with pytest.raises(AssertionError, match=r"Page titled `Basic test` already exists.*"):
            conf_md.create_page("1115881473", "Basic test", False)

        with pytest.raises(ApiError, match=r"There is no content with the given id.*"):
            conf_md.create_page("1", "Basic test", False)

        with pytest.raises(AssertionError, match=r"Metadata pointing to an existing page id.*"):
            conf_md.create_page("1115881473", "Basic test 2", False)

        captured = capsys.readouterr()
        assert captured.out == ""

        for record in caplog.records:
            assert record.levelname == "DEBUG"
        assert "found page_id `1117683721`" in caplog.text

    def test_jira_links(self, capsys, caplog, user, token):
        conf_md = TestConfluenceMD.init_confluencemd(user, token, "src/tests/test_jira.md")

        conf_md.create_page("1115881473", "Jira test", True)

        captured = capsys.readouterr()
        assert captured.out == ""

        for record in caplog.records:
            assert record.levelname in ["INFO", "DEBUG"]
        assert "Use --convert_jira to replace 2 Jira link" in caplog.text

    def test_images(self, capsys, caplog, user, token):
        conf_md = TestConfluenceMD.init_confluencemd(user, token, "src/tests/test_images.md")

        conf_md.create_page("1115881473", "Images test", True)

        captured = capsys.readouterr()
        assert captured.out == ""

        for record in caplog.records:
            assert record.levelname in ["INFO", "DEBUG"]
        assert "Use --convert_jira to replace 2 Jira link" in caplog.text

import pytest
import logging

from src.md2cf.utils.confluencemd import ConfluenceMD
from atlassian.errors import ApiError
logging.getLogger("net.dirtyagile.confluence.md").setLevel('DEBUG')

class TestConfluenceMD:
    
    @staticmethod
    def init_confluencemd(user, token, md_file):
        return ConfluenceMD(username=user, md_file=md_file, token=token, url="https://dirtyagile.atlassian.net/wiki/")

    def test_create_page1(self, capsys, caplog, user, token):
        conf_md = TestConfluenceMD.init_confluencemd(user, token, "src/tests/sample_1.md")
        with pytest.raises(AssertionError, match=r"Provide parent_id for a newly created page"):
            conf_md.create_page("", "sample 1", None)

        with pytest.raises(AssertionError, match=r"Provide a title for a newly created page"):
            conf_md.create_page("1115881473", "", None)
    
        with pytest.raises(AssertionError, match=r"Page titled `sample 1` already exists.*"):
            conf_md.create_page("1115881473", "sample 1", False)

        with pytest.raises(ApiError, match=r"There is no content with the given id.*"):
            conf_md.create_page("1", "sample 1", False)
        
        with pytest.raises(AssertionError, match=r"Metadata pointing to an existing page id.*"):
            conf_md.create_page("1115881473", "sample 2", False)
            
        captured = capsys.readouterr()
        assert captured.out == ""

        for record in caplog.records:
            assert record.levelname == "DEBUG"
        assert "found page_id `1115848706`" in caplog.text
        
    def test_create_page2(self, capsys, caplog, user, token):
        conf_md = TestConfluenceMD.init_confluencemd(user, token, "src/tests/sample_2.md")
        
        with pytest.raises(AssertionError, match=r"Metadata pointing to an existing page id.*"):
            conf_md.create_page("1115881473", "sample 2", False)
            
        captured = capsys.readouterr()
        assert captured.out == ""

        for record in caplog.records:
            assert record.levelname in ["INFO", "DEBUG"]
        assert "Use --convert_jira to replace 2 Jira link" in caplog.text
        
    
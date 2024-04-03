import pytest

from md2cf.utils.confluencemd import ConfluenceMD
from atlassian.errors import ApiError

class TestConfluenceMD:
    def test_parse_confluence_url(self, user, token):
        conf_md = ConfluenceMD(username=user, md_file="src/tests/sample_1.md", token=token, url="https://dirtyagile.atlassian.net/wiki/")
        with pytest.raises(AssertionError, match=r"Page titled `sample 1` already exists.*"):
            conf_md.create_page("1115881473", "sample 1", False)

        with pytest.raises(ApiError, match=r"There is no content with the given id.*"):
            conf_md.create_page("1", "sample 1", False)
import pytest

# pylint: disable=missing-function-docstring

def pytest_addoption(parser):
    parser.addoption("--user", action="store", required=True,
            help="Atlassian username/email")
    parser.addoption("--token", action="store", required=True,
            help="Atlassian API token (used in cloud instances)")
    parser.addoption("--url", action="store", required=False,
            default="https://dirtyagile.atlassian.net/wiki/",
            help="Atlassian instance URL")

@pytest.fixture(scope="class")
def user(request):
    return request.config.getoption("--user")

@pytest.fixture(scope="class")
def token(request):
    return request.config.getoption("--token")

@pytest.fixture(scope="class")
def url(request):
    return request.config.getoption("--url")

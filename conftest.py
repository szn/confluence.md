import pytest

def pytest_addoption(parser):
    parser.addoption("--user", action="store", required=True,
            help="Atlassian username/email")
    parser.addoption("--token", action="store", required=True,
            help="Atlassian API token (used in cloud instances)")
    parser.addoption("--url", action="store", required=False,
            help="Atlassian instance URL")

@pytest.fixture
def user(request):
    return request.config.getoption("--user")

@pytest.fixture
def token(request):
    return request.config.getoption("--token")

@pytest.fixture
def url(request):
    return request.config.getoption("--url")
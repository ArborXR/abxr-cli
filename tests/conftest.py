from unittest.mock import MagicMock

import pytest


BASE_URL = "https://api.xrdm.app"
TOKEN = "test-token"


@pytest.fixture
def base_url():
    return BASE_URL


@pytest.fixture
def token():
    return TOKEN


def make_response(json_data=None, status_code=200, content=b'{}', headers=None):
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.content = content
    response.headers = headers or {}
    response.json.return_value = json_data if json_data is not None else {}
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        from requests import HTTPError
        response.raise_for_status.side_effect = HTTPError(response=response)
    return response


@pytest.fixture
def mock_client(mocker):
    """Patch the `client` attribute on every ApiService subclass instance."""
    return mocker.MagicMock()


@pytest.fixture
def patched_requests(mocker):
    """Replace the module-level `requests` import used by ApiService."""
    return mocker.patch("abxr.api_service.requests")

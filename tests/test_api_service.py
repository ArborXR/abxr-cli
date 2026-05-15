import pytest

from abxr.api_service import ApiService
from tests.conftest import make_response


class TestUrlNormalization:
    def test_bare_origin(self):
        svc = ApiService("https://api.xrdm.app", "tok")
        assert svc._base_origin == "https://api.xrdm.app"

    def test_trailing_slash_origin(self):
        svc = ApiService("https://api.xrdm.app/", "tok")
        assert svc._base_origin == "https://api.xrdm.app"

    def test_strips_api(self):
        svc = ApiService("https://api.xrdm.app/api", "tok")
        assert svc._base_origin == "https://api.xrdm.app"

    def test_strips_api_v3(self):
        svc = ApiService("https://api.xrdm.app/api/v3", "tok")
        assert svc._base_origin == "https://api.xrdm.app"

    def test_strips_api_v3_with_trailing_slash(self):
        svc = ApiService("https://api.xrdm.app/api/v3/", "tok")
        assert svc._base_origin == "https://api.xrdm.app"

    def test_strips_api_internal(self):
        svc = ApiService("https://api.xrdm.app/api/internal", "tok")
        assert svc._base_origin == "https://api.xrdm.app"


class TestV2Rejection:
    def test_rejects_api_v2(self):
        with pytest.raises(ValueError, match="v2"):
            ApiService("https://api.xrdm.app/api/v2", "tok")

    def test_rejects_api_v2_with_trailing_slash(self):
        with pytest.raises(ValueError, match="v2"):
            ApiService("https://api.xrdm.app/api/v2/", "tok")

    def test_rejects_api_v2_with_extra_path(self):
        with pytest.raises(ValueError, match="v2"):
            ApiService("https://api.xrdm.app/api/v2/apps", "tok")

    def test_error_message_mentions_v3(self):
        with pytest.raises(ValueError, match=r"v3"):
            ApiService("https://api.xrdm.app/api/v2", "tok")


class TestUrlBuilder:
    def test_builds_v3_url(self):
        svc = ApiService("https://api.xrdm.app", "tok")
        assert svc._url("apps") == "https://api.xrdm.app/api/v3/apps"

    def test_joins_multiple_segments(self):
        svc = ApiService("https://api.xrdm.app", "tok")
        assert svc._url("apps", "abc", "versions") == "https://api.xrdm.app/api/v3/apps/abc/versions"

    def test_strips_segment_slashes(self):
        svc = ApiService("https://api.xrdm.app", "tok")
        assert svc._url("/apps/", "abc") == "https://api.xrdm.app/api/v3/apps/abc"


class TestAuthHeaders:
    def test_bearer_token(self):
        svc = ApiService("https://api.xrdm.app", "my-token")
        assert svc.headers["Authorization"] == "Bearer my-token"
        assert svc.headers["Content-Type"] == "application/json"
        assert svc.headers["Accept"] == "application/json"


class TestPagination:
    def test_single_page(self, mocker):
        svc = ApiService("https://api.xrdm.app", "tok")
        svc.client = mocker.MagicMock()
        svc.client.get.return_value = make_response({"data": [{"id": 1}, {"id": 2}]})

        result = svc._get_all_pages("https://api.xrdm.app/api/v3/apps")

        assert result == [{"id": 1}, {"id": 2}]
        assert svc.client.get.call_count == 1

    def test_follows_links_next(self, mocker):
        svc = ApiService("https://api.xrdm.app", "tok")
        svc.client = mocker.MagicMock()
        svc.client.get.side_effect = [
            make_response({
                "data": [{"id": 1}],
                "links": {"next": "https://api.xrdm.app/api/v3/apps?page=2"}
            }),
            make_response({
                "data": [{"id": 2}],
                "links": {"next": "https://api.xrdm.app/api/v3/apps?page=3"}
            }),
            make_response({"data": [{"id": 3}], "links": {"next": None}}),
        ]

        result = svc._get_all_pages("https://api.xrdm.app/api/v3/apps")

        assert result == [{"id": 1}, {"id": 2}, {"id": 3}]
        assert svc.client.get.call_count == 3


class TestParseResponse:
    def test_empty_content_returns_none(self, mocker):
        svc = ApiService("https://api.xrdm.app", "tok")
        response = mocker.MagicMock(content=b"")
        assert svc._parse_response(response) is None

    def test_non_empty_content_returns_json(self, mocker):
        svc = ApiService("https://api.xrdm.app", "tok")
        response = mocker.MagicMock(content=b'{"foo": "bar"}')
        response.json.return_value = {"foo": "bar"}
        assert svc._parse_response(response) == {"foo": "bar"}

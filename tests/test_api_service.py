import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import requests
from requests.adapters import Retry

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


class TestRetryClient:
    def test_client_is_a_session(self):
        svc = ApiService("https://api.xrdm.app", "tok")
        assert isinstance(svc.client, requests.Session)

    @pytest.mark.parametrize("url", ["https://api.xrdm.app/api/v3/apps", "http://portal.xrdm.local/api/v3/apps"])
    def test_retry_adapter_mounted_for_both_schemes(self, url):
        svc = ApiService("https://api.xrdm.app", "tok")
        retry = svc.client.get_adapter(url).max_retries
        assert isinstance(retry, Retry)
        assert retry.total == 5
        assert retry.backoff_factor == 1
        assert retry.raise_on_status is False

    @pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
    @pytest.mark.parametrize("status", [429, 502, 503, 504])
    def test_retries_transient_statuses_for_every_method_used(self, method, status):
        retry = ApiService("https://api.xrdm.app", "tok").client.get_adapter("https://x").max_retries
        assert retry.is_retry(method, status)

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 422, 500])
    def test_does_not_retry_non_transient_statuses(self, status):
        retry = ApiService("https://api.xrdm.app", "tok").client.get_adapter("https://x").max_retries
        assert not retry.is_retry("GET", status)


class ScriptedHandler(BaseHTTPRequestHandler):
    """Answers each request from server.script: a status code, or 'drop' to
    close the connection without responding (a pod terminating mid-request)."""

    def _handle(self):
        self.server.hits += 1
        self.rfile.read(int(self.headers.get('Content-Length') or 0))

        step = self.server.script.pop(0) if self.server.script else 200
        if step == 'drop':
            return

        body = b'{"ok": true}' if step == 200 else b''
        self.send_response(step)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PUT = _handle

    def log_message(self, *args):
        pass


@pytest.fixture
def scripted_server(mocker):
    mocker.patch.object(Retry, "sleep")
    server = HTTPServer(('127.0.0.1', 0), ScriptedHandler)
    server.script = []
    server.hits = 0
    server.url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


class TestRetryBehaviour:
    def test_get_recovers_from_transient_503s(self, scripted_server):
        scripted_server.script = [503, 503]
        svc = ApiService(scripted_server.url, "tok")

        response = svc.client.get(f"{scripted_server.url}/api/v3/apps", headers=svc.headers)

        assert response.status_code == 200
        assert scripted_server.hits == 3

    def test_post_recovers_from_transient_503(self, scripted_server):
        scripted_server.script = [503]
        svc = ApiService(scripted_server.url, "tok")

        response = svc.client.post(f"{scripted_server.url}/api/v3/files", json={"a": 1}, headers=svc.headers)

        assert response.status_code == 200
        assert scripted_server.hits == 2

    def test_presigned_put_recovers_from_transient_503(self, scripted_server):
        scripted_server.script = [503]
        svc = ApiService(scripted_server.url, "tok")

        response = svc.client.put(f"{scripted_server.url}/bucket/key?part=1", data=b"part-bytes")

        assert response.status_code == 200
        assert scripted_server.hits == 2

    def test_recovers_from_connection_dropped_before_response(self, scripted_server):
        scripted_server.script = ['drop', 'drop']
        svc = ApiService(scripted_server.url, "tok")

        response = svc.client.post(f"{scripted_server.url}/api/v3/files", json={"a": 1}, headers=svc.headers)

        assert response.status_code == 200
        assert scripted_server.hits == 3

    def test_gives_up_after_retries_and_returns_last_response(self, scripted_server):
        scripted_server.script = [503] * 10
        svc = ApiService(scripted_server.url, "tok")

        response = svc.client.get(f"{scripted_server.url}/api/v3/apps", headers=svc.headers)

        assert response.status_code == 503
        assert scripted_server.hits == 6
        with pytest.raises(requests.HTTPError):
            response.raise_for_status()

    def test_does_not_retry_client_errors(self, scripted_server):
        scripted_server.script = [404]
        svc = ApiService(scripted_server.url, "tok")

        response = svc.client.get(f"{scripted_server.url}/api/v3/apps/nope", headers=svc.headers)

        assert response.status_code == 404
        assert scripted_server.hits == 1

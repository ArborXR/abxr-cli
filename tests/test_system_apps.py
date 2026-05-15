"""Tests for SystemAppsService.

CRITICAL: SystemAppsService uses the non-versioned /api/internal/... endpoints
with org-scoped tokens for the system-app organization. After the v2 cleanup,
this code path must continue to work unchanged — these tests are the guard.
"""

import pytest

from abxr.system_apps import SystemAppsService
from tests.conftest import make_response


def _service(mocker, base_url="https://api.xrdm.app"):
    svc = SystemAppsService(base_url, "tok")
    svc.client = mocker.MagicMock()
    return svc


class TestConstructorAcceptsInternalUrls:
    def test_bare_origin(self):
        svc = SystemAppsService("https://api.xrdm.app", "tok")
        assert svc._internal_base == "https://api.xrdm.app/api/internal"

    def test_strips_api_internal_suffix(self):
        svc = SystemAppsService("https://api.xrdm.app/api/internal", "tok")
        assert svc._internal_base == "https://api.xrdm.app/api/internal"

    def test_strips_api_v3_suffix(self):
        svc = SystemAppsService("https://api.xrdm.app/api/v3", "tok")
        assert svc._internal_base == "https://api.xrdm.app/api/internal"


class TestUrlOverride:
    def test_builds_internal_path_not_v3(self, mocker):
        svc = _service(mocker)
        url = svc._url("apps", "client", "versions")
        assert url == "https://api.xrdm.app/api/internal/apps/client/versions"
        assert "/api/v3/" not in url

    def test_join_strips_segment_slashes(self, mocker):
        svc = _service(mocker)
        url = svc._url("/apps/", "client", "versions/")
        assert url == "https://api.xrdm.app/api/internal/apps/client/versions"


class TestVersionsList:
    def test_hits_internal_endpoint(self, mocker):
        svc = _service(mocker)
        svc.client.get.return_value = make_response({"data": [{"id": "v1"}], "links": {}})

        result = svc.get_all_app_versions_by_type("client")

        assert result == [{"id": "v1"}]
        url = svc.client.get.call_args[0][0]
        assert url == "https://api.xrdm.app/api/internal/apps/client/versions?per_page=20"


class TestReleaseChannels:
    def test_list_hits_internal_endpoint(self, mocker):
        svc = _service(mocker)
        svc.client.get.return_value = make_response({"data": [], "links": {}})

        svc.get_all_release_channels_for_app("client")

        url = svc.client.get.call_args[0][0]
        assert url == "https://api.xrdm.app/api/internal/apps/client/release-channels?per_page=20"

    def test_detail_hits_internal_endpoint(self, mocker):
        svc = _service(mocker)
        svc.client.get.return_value = make_response({"id": "rc1"})

        svc.get_release_channel_detail("client", "rc1")

        svc.client.get.assert_called_once_with(
            "https://api.xrdm.app/api/internal/apps/client/release-channels/rc1",
            headers=svc.headers,
        )


class TestAppCompatibilities:
    def test_list_hits_internal_endpoint(self, mocker):
        svc = _service(mocker)
        svc.client.get.return_value = make_response({"data": [], "links": {}})

        svc.get_all_app_compatibilities_for_app("client")

        url = svc.client.get.call_args[0][0]
        assert url == "https://api.xrdm.app/api/internal/apps/client/app-compatibilities?per_page=20"

    def test_detail_hits_internal_endpoint(self, mocker):
        svc = _service(mocker)
        svc.client.get.return_value = make_response({"id": "c1"})

        svc.get_app_compatibility_detail("client", "c1")

        svc.client.get.assert_called_once_with(
            "https://api.xrdm.app/api/internal/apps/client/app-compatibilities/c1",
            headers=svc.headers,
        )


class TestUploadFlow:
    def test_initiate_upload_hits_internal_endpoint(self, mocker):
        svc = _service(mocker)
        svc.client.post.return_value = make_response({
            "versionId": "v1", "uploadId": "u1", "key": "k1",
        })

        svc._initiate_upload("client", "client.apk", "compat-1", "1.0.0", 1)

        args, kwargs = svc.client.post.call_args
        assert args[0] == "https://api.xrdm.app/api/internal/apps/client/versions"
        assert kwargs["json"]["filename"] == "client.apk"
        assert kwargs["json"]["appCompatibilityId"] == "compat-1"
        assert kwargs["json"]["versionName"] == "1.0.0"
        assert kwargs["json"]["versionCode"] == 1

    def test_initiate_upload_omits_optional_fields(self, mocker):
        svc = _service(mocker)
        svc.client.post.return_value = make_response({
            "versionId": "v1", "uploadId": "u1", "key": "k1",
        })

        svc._initiate_upload("client", "client.apk", "compat-1")

        payload = svc.client.post.call_args.kwargs["json"]
        assert "versionName" not in payload
        assert "versionCode" not in payload

    def test_presigned_url_hits_internal_endpoint(self, mocker):
        svc = _service(mocker)
        svc.client.post.return_value = make_response([{"partNumber": 1, "presignedUrl": "https://s3..."}])

        svc._presigned_url("client", "v1", "u1", "k1", [1])

        args, kwargs = svc.client.post.call_args
        assert args[0] == "https://api.xrdm.app/api/internal/apps/client/versions/v1/pre-sign"
        assert kwargs["json"] == {"key": "k1", "uploadId": "u1", "partNumbers": [1]}


class TestFullSystemAppUpload:
    """End-to-end upload flow for system apps (e.g. client.apk to /api/internal/...)."""

    def _setup_fake_file(self, mocker):
        from abxr import system_apps as system_apps_module
        fake = mocker.MagicMock()
        fake.file_name = "client.apk"
        fake.get_size.return_value = 4
        fake.get_part_numbers.return_value = 1
        fake.get_part.return_value = b"apk!"
        mocker.patch.object(system_apps_module, "MultipartFileS3", return_value=fake)

    def test_resolves_compatibility_then_uploads(self, mocker):
        self._setup_fake_file(mocker)
        svc = _service(mocker)
        # get_all_app_compatibilities_for_app -> internal GET
        svc.client.get.return_value = make_response({
            "data": [{"id": "compat-1", "name": "Pico 4 Enterprise"}],
            "links": {},
        })
        svc.client.post.side_effect = [
            make_response({"versionId": "v1", "uploadId": "u1", "key": "k1"}),
            make_response([{"partNumber": 1, "presignedUrl": "https://s3/1"}]),
            make_response({"id": "v1", "status": "available"}),
        ]
        svc.client.put.return_value = make_response({}, headers={"ETag": '"e1"'})

        result = svc.upload_file(
            "client", "/fake/client.apk", "Pico 4 Enterprise",
            "2.0.0", 200, "release notes", silent=True,
        )

        assert result == {"id": "v1", "status": "available"}

        # All POSTs hit /api/internal/...
        for call in svc.client.post.call_args_list:
            assert "/api/internal/apps/client/versions" in call.args[0]
            assert "/api/v3/" not in call.args[0]

        # Initiate carries the resolved compatibility id and version metadata
        initiate_payload = svc.client.post.call_args_list[0].kwargs["json"]
        assert initiate_payload["appCompatibilityId"] == "compat-1"
        assert initiate_payload["versionName"] == "2.0.0"
        assert initiate_payload["versionCode"] == 200

        # Complete carries version + release notes
        complete_payload = svc.client.post.call_args_list[-1].kwargs["json"]
        assert complete_payload["parts"] == [{"partNumber": 1, "eTag": '"e1"'}]

    def test_raises_when_compatibility_not_found(self, mocker):
        self._setup_fake_file(mocker)
        svc = _service(mocker)
        svc.client.get.return_value = make_response({
            "data": [{"id": "compat-1", "name": "Other Headset"}],
            "links": {},
        })

        with pytest.raises(ValueError, match="App compatibility .* not found"):
            svc.upload_file(
                "client", "/fake/client.apk", "Pico 4 Enterprise",
                "2.0.0", 200, "notes", silent=True,
            )

import pytest

from abxr.apps import AppsService
from tests.conftest import make_response


def _service(mocker):
    svc = AppsService("https://api.xrdm.app", "tok")
    svc.client = mocker.MagicMock()
    return svc


class TestGetAllApps:
    def test_paginates(self, mocker):
        svc = _service(mocker)
        svc.client.get.return_value = make_response({"data": [{"id": "a"}, {"id": "b"}], "links": {}})

        result = svc.get_all_apps()

        assert result == [{"id": "a"}, {"id": "b"}]
        called_url = svc.client.get.call_args[0][0]
        assert called_url == "https://api.xrdm.app/api/v3/apps?per_page=20"


class TestGetAppDetail:
    def test_hits_v3_path(self, mocker):
        svc = _service(mocker)
        svc.client.get.return_value = make_response({"id": "abc"})

        result = svc.get_app_detail("abc")

        assert result == {"id": "abc"}
        svc.client.get.assert_called_once_with(
            "https://api.xrdm.app/api/v3/apps/abc",
            headers=svc.headers,
        )


class TestVersionsBySha256:
    def test_empty_input_returns_empty(self, mocker):
        svc = _service(mocker)
        assert svc.get_versions_by_sha256("app-id", []) == []
        svc.client.get.assert_not_called()

    def test_filters_to_available_only(self, mocker):
        svc = _service(mocker)
        svc.client.get.return_value = make_response({"data": [
            {"id": "v1", "status": "available"},
            {"id": "v2", "status": "processing"},
            {"id": "v3", "status": "error"},
            {"id": "v4", "status": "available"},
        ]})

        result = svc.get_versions_by_sha256("app-id", ["hash1"])

        assert [v["id"] for v in result] == ["v1", "v4"]

    def test_builds_sha256_query_params(self, mocker):
        svc = _service(mocker)
        svc.client.get.return_value = make_response({"data": []})

        svc.get_versions_by_sha256("app-id", ["h1", "h2"])

        called_url = svc.client.get.call_args[0][0]
        assert "sha256[]=h1" in called_url
        assert "sha256[]=h2" in called_url
        assert called_url.startswith("https://api.xrdm.app/api/v3/apps/app-id/versions?")


class TestFilesBySha512:
    def test_empty_input_returns_empty(self, mocker):
        svc = _service(mocker)
        assert svc.get_files_by_sha512("app-id", []) == []
        svc.client.get.assert_not_called()


class TestAppUpload:
    """End-to-end APK upload exercising the v3 lowercase status polling."""

    def _setup_fake_file(self, mocker):
        from abxr import apps as apps_module
        fake = mocker.MagicMock()
        fake.file_name = "translate.apk"
        fake.get_size.return_value = 4
        fake.get_part_numbers.return_value = 1
        fake.get_part.return_value = b"apk!"
        mocker.patch.object(apps_module, "MultipartFileS3", return_value=fake)
        return fake

    def test_full_upload_and_status_polling_available(self, mocker):
        self._setup_fake_file(mocker)
        svc = _service(mocker)
        svc.client.post.side_effect = [
            make_response({"versionId": "v1", "uploadId": "u1", "key": "k1"}),
            make_response([{"partNumber": 1, "presignedUrl": "https://s3/1"}]),
            make_response({"id": "v1"}),
        ]
        svc.client.put.return_value = make_response({}, headers={"ETag": '"e1"'})
        svc.client.get.return_value = make_response({
            "data": [{"id": "v1", "status": "available"}],
        })
        mocker.patch("abxr.apps.time.sleep")

        result = svc.upload_file(
            "app-1", "/fake/path.apk", "1.0.0", "notes",
            silent=True, wait=True, max_wait_time_sec=10,
        )

        assert result == {"id": "v1"}
        # initiate -> presign -> complete = 3 POSTs to API
        assert svc.client.post.call_count == 3
        # status polled at least once
        assert svc.client.get.called

    def test_status_polling_raises_on_error_status(self, mocker):
        self._setup_fake_file(mocker)
        svc = _service(mocker)
        svc.client.post.side_effect = [
            make_response({"versionId": "v1", "uploadId": "u1", "key": "k1"}),
            make_response([{"partNumber": 1, "presignedUrl": "https://s3/1"}]),
            make_response({"id": "v1"}),
        ]
        svc.client.put.return_value = make_response({}, headers={"ETag": '"e1"'})
        svc.client.get.return_value = make_response({
            "data": [{"id": "v1", "status": "error"}],
        })
        mocker.patch("abxr.apps.time.sleep")

        with pytest.raises(Exception, match="Upload failed server processing"):
            svc.upload_file(
                "app-1", "/fake/path.apk", "1.0.0", "notes",
                silent=True, wait=True, max_wait_time_sec=10,
            )

    def test_status_polling_handles_processing_then_available(self, mocker):
        """Verify polling loops while status is something other than available/error."""
        self._setup_fake_file(mocker)
        svc = _service(mocker)
        svc.client.post.side_effect = [
            make_response({"versionId": "v1", "uploadId": "u1", "key": "k1"}),
            make_response([{"partNumber": 1, "presignedUrl": "https://s3/1"}]),
            make_response({"id": "v1"}),
        ]
        svc.client.put.return_value = make_response({}, headers={"ETag": '"e1"'})
        svc.client.get.side_effect = [
            make_response({"data": [{"id": "v1", "status": "processing"}]}),
            make_response({"data": [{"id": "v1", "status": "processing"}]}),
            make_response({"data": [{"id": "v1", "status": "available"}]}),
        ]
        mocker.patch("abxr.apps.time.sleep")

        result = svc.upload_file(
            "app-1", "/fake/path.apk", "1.0.0", "notes",
            silent=True, wait=True, max_wait_time_sec=10,
        )

        assert result == {"id": "v1"}
        assert svc.client.get.call_count == 3

    def test_wait_false_skips_status_polling(self, mocker):
        self._setup_fake_file(mocker)
        svc = _service(mocker)
        svc.client.post.side_effect = [
            make_response({"versionId": "v1", "uploadId": "u1", "key": "k1",
                           "appBundleId": "bundle-123"}),
            make_response([{"partNumber": 1, "presignedUrl": "https://s3/1"}]),
            make_response({"id": "v1"}),
        ]
        svc.client.put.return_value = make_response({}, headers={"ETag": '"e1"'})

        result = svc.upload_file(
            "app-1", "/fake/path.apk", "1.0.0", "notes",
            silent=True, wait=False,
        )

        # appBundleId from initiate response is propagated into complete_response
        assert result["appBundleId"] == "bundle-123"
        svc.client.get.assert_not_called()

    def test_complete_payload_carries_version_and_notes(self, mocker):
        self._setup_fake_file(mocker)
        svc = _service(mocker)
        svc.client.post.side_effect = [
            make_response({"versionId": "v1", "uploadId": "u1", "key": "k1"}),
            make_response([{"partNumber": 1, "presignedUrl": "https://s3/1"}]),
            make_response({"id": "v1"}),
        ]
        svc.client.put.return_value = make_response({}, headers={"ETag": '"e1"'})

        svc.upload_file(
            "app-1", "/fake/path.apk", "1.0.0", "release notes",
            silent=True, wait=False,
        )

        complete_payload = svc.client.post.call_args_list[-1].kwargs["json"]
        assert complete_payload["versionName"] == "1.0.0"
        assert complete_payload["releaseNotes"] == "release notes"
        assert complete_payload["parts"] == [{"partNumber": 1, "eTag": '"e1"'}]


class TestAppBuildTypeOnInitiate:
    """For bundle uploads, AppsService.upload_file is called with app_build_type='app-bundle'."""

    def test_app_build_type_passed_through(self, mocker):
        from abxr import apps as apps_module
        fake = mocker.MagicMock()
        fake.file_name = "build.apk"
        fake.get_size.return_value = 1
        fake.get_part_numbers.return_value = 1
        fake.get_part.return_value = b"x"
        mocker.patch.object(apps_module, "MultipartFileS3", return_value=fake)

        svc = _service(mocker)
        svc.client.post.side_effect = [
            make_response({"versionId": "v1", "uploadId": "u1", "key": "k1"}),
            make_response([{"partNumber": 1, "presignedUrl": "https://s3/1"}]),
            make_response({"id": "v1"}),
        ]
        svc.client.put.return_value = make_response({}, headers={"ETag": '"e1"'})

        svc.upload_file(
            "app-1", "/fake/path.apk", "1.0.0", "notes",
            silent=True, wait=False, app_build_type="app-bundle",
        )

        initiate_payload = svc.client.post.call_args_list[0].kwargs["json"]
        assert initiate_payload["appBuildType"] == "app-bundle"

from abxr.files import FilesService
from tests.conftest import make_response


def _service(mocker):
    svc = FilesService("https://api.xrdm.app", "tok")
    svc.client = mocker.MagicMock()
    return svc


def test_get_all_files_uses_v3(mocker):
    svc = _service(mocker)
    svc.client.get.return_value = make_response({"data": [{"id": "f1"}], "links": {}})

    result = svc.get_all_files()

    assert result == [{"id": "f1"}]
    url = svc.client.get.call_args[0][0]
    assert url == "https://api.xrdm.app/api/v3/files?per_page=20"


def test_get_file_detail(mocker):
    svc = _service(mocker)
    svc.client.get.return_value = make_response({"id": "f1"})

    result = svc.get_file_detail("f1")

    assert result == {"id": "f1"}
    svc.client.get.assert_called_once_with(
        "https://api.xrdm.app/api/v3/files/f1",
        headers=svc.headers,
    )


def test_initiate_upload_posts_payload(mocker):
    svc = _service(mocker)
    svc.client.post.return_value = make_response({"fileId": "f1", "uploadId": "u1", "key": "k1"})

    result = svc._initiate_upload("config.json", "/sdcard")

    assert result == {"fileId": "f1", "uploadId": "u1", "key": "k1"}
    args, kwargs = svc.client.post.call_args
    assert args[0] == "https://api.xrdm.app/api/v3/files"
    assert kwargs["json"] == {"filename": "config.json", "path": "/sdcard"}


def test_initiate_upload_with_bundle_id(mocker):
    svc = _service(mocker)
    svc.client.post.return_value = make_response({"fileId": "f1", "uploadId": "u1", "key": "k1"})

    svc._initiate_upload("config.json", "/sdcard", app_bundle_id="b1")

    assert svc.client.post.call_args.kwargs["json"]["appBundleId"] == "b1"


def test_assign_file_to_device(mocker):
    svc = _service(mocker)
    svc.client.post.return_value = make_response({}, content=b"")

    svc.assign_file_to_device("f1", "d1")

    svc.client.post.assert_called_once_with(
        "https://api.xrdm.app/api/v3/devices/d1/files",
        json={"fileId": "f1"},
        headers=svc.headers,
    )


def test_remove_file_from_device(mocker):
    svc = _service(mocker)
    svc.client.delete.return_value = make_response({}, content=b"")

    svc.remove_file_from_device("f1", "d1")

    svc.client.delete.assert_called_once_with(
        "https://api.xrdm.app/api/v3/devices/d1/files",
        json={"fileId": "f1"},
        headers=svc.headers,
    )


class TestMultipartUpload:
    """End-to-end multipart upload: initiate -> presign -> PUT parts to S3 -> complete."""

    def test_uploads_single_part_file(self, mocker, tmp_path):
        # File smaller than MIN_PART_SIZE (5 MiB) -> exactly one part.
        f = tmp_path / "config.json"
        f.write_bytes(b'{"hello": "world"}')

        svc = _service(mocker)
        svc.client.post.side_effect = [
            make_response({"fileId": "file-1", "uploadId": "upload-1", "key": "key-1"}),
            make_response([{"partNumber": 1, "presignedUrl": "https://s3.example/part-1"}]),
            make_response({"id": "file-1", "status": "available"}),
        ]
        svc.client.put.return_value = make_response({}, headers={"ETag": '"etag-1"'})

        result = svc.upload_file(str(f), "/sdcard", silent=True)

        assert result == {"id": "file-1", "status": "available"}

        initiate_call, presign_call, complete_call = svc.client.post.call_args_list
        assert initiate_call.args[0] == "https://api.xrdm.app/api/v3/files"
        assert initiate_call.kwargs["json"] == {"filename": "config.json", "path": "/sdcard"}

        assert presign_call.args[0] == "https://api.xrdm.app/api/v3/files/file-1/pre-sign"
        assert presign_call.kwargs["json"] == {
            "key": "key-1", "uploadId": "upload-1", "partNumbers": [1],
        }

        svc.client.put.assert_called_once()
        put_call = svc.client.put.call_args
        assert put_call.args[0] == "https://s3.example/part-1"
        assert put_call.kwargs["data"] == b'{"hello": "world"}'

        assert complete_call.args[0] == "https://api.xrdm.app/api/v3/files/file-1/complete"
        assert complete_call.kwargs["json"] == {
            "key": "key-1",
            "uploadId": "upload-1",
            "parts": [{"partNumber": 1, "eTag": '"etag-1"'}],
            "conflictStrategy": "replace",
        }

    def test_batches_presigned_url_requests(self, mocker, tmp_path):
        """With >4 parts, presigning is batched into chunks of MAX_PARTS_PER_REQUEST."""
        # Create a file large enough for 5 parts (5 MiB minimum each = ~25 MiB to ensure 5 parts).
        # Cheaper: monkey-patch MultipartFileS3 to report 5 small parts.
        from abxr import files as files_module

        fake = mocker.MagicMock()
        fake.file_name = "big.bin"
        fake.get_size.return_value = 5
        fake.get_part_numbers.return_value = 5
        fake.get_part.return_value = b"x"
        mocker.patch.object(files_module, "MultipartFileS3", return_value=fake)

        svc = _service(mocker)
        svc.client.post.side_effect = [
            make_response({"fileId": "file-1", "uploadId": "u1", "key": "k1"}),
            # First presign batch (parts 1-4)
            make_response([
                {"partNumber": n, "presignedUrl": f"https://s3/{n}"} for n in [1, 2, 3, 4]
            ]),
            # Second presign batch (part 5)
            make_response([{"partNumber": 5, "presignedUrl": "https://s3/5"}]),
            # Complete
            make_response({"id": "file-1"}),
        ]
        svc.client.put.return_value = make_response({}, headers={"ETag": '"e"'})

        svc.upload_file("ignored", "/sdcard", silent=True)

        # 1 initiate + 2 presign + 1 complete = 4 POSTs
        assert svc.client.post.call_count == 4
        # 5 part PUTs to S3
        assert svc.client.put.call_count == 5

        # All 5 parts reported in complete payload
        complete_payload = svc.client.post.call_args_list[-1].kwargs["json"]
        assert [p["partNumber"] for p in complete_payload["parts"]] == [1, 2, 3, 4, 5]

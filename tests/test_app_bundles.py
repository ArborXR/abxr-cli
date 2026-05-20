from pathlib import Path

import pytest

from abxr.app_bundles import AppBundlesService
from tests.conftest import make_response


def _service(mocker):
    svc = AppBundlesService("https://api.xrdm.app", "tok")
    svc.client = mocker.MagicMock()
    return svc


class TestDevicePathComputation:
    def test_root_file_default(self, mocker, tmp_path):
        svc = _service(mocker)
        f = tmp_path / "config.json"
        f.touch()
        assert svc._compute_device_path(f, tmp_path) == "/sdcard"

    def test_subdir_file_default(self, mocker, tmp_path):
        svc = _service(mocker)
        (tmp_path / "data" / "cache").mkdir(parents=True)
        f = tmp_path / "data" / "cache" / "temp.dat"
        f.touch()
        assert svc._compute_device_path(f, tmp_path) == "/sdcard/data/cache"

    def test_root_file_with_base_path(self, mocker, tmp_path):
        svc = _service(mocker)
        f = tmp_path / "config.json"
        f.touch()
        assert svc._compute_device_path(f, tmp_path, "myapp/config") == "/sdcard/myapp/config"

    def test_subdir_file_with_base_path(self, mocker, tmp_path):
        svc = _service(mocker)
        (tmp_path / "data").mkdir()
        f = tmp_path / "data" / "user.json"
        f.touch()
        assert svc._compute_device_path(f, tmp_path, "myapp/config") == "/sdcard/myapp/config/data"

    def test_main_obb_routed_to_canonical_path(self, mocker, tmp_path):
        svc = _service(mocker)
        f = tmp_path / "main.123.com.example.testapp.obb"
        f.touch()
        assert svc._compute_device_path(f, tmp_path) == "/sdcard/Android/obb/com.example.testapp"

    def test_patch_obb_routed_to_canonical_path(self, mocker, tmp_path):
        svc = _service(mocker)
        f = tmp_path / "patch.123.com.example.testapp.obb"
        f.touch()
        assert svc._compute_device_path(f, tmp_path) == "/sdcard/Android/obb/com.example.testapp"

    def test_obb_in_subdir_ignores_folder_layout(self, mocker, tmp_path):
        svc = _service(mocker)
        (tmp_path / "extras").mkdir()
        f = tmp_path / "extras" / "main.1.com.example.app.obb"
        f.touch()
        assert svc._compute_device_path(f, tmp_path) == "/sdcard/Android/obb/com.example.app"

    def test_obb_bypasses_base_path(self, mocker, tmp_path):
        svc = _service(mocker)
        f = tmp_path / "main.7.com.foo.bar.obb"
        f.touch()
        assert svc._compute_device_path(f, tmp_path, "custom/path") == "/sdcard/Android/obb/com.foo.bar"

    def test_misnamed_obb_falls_back_with_warning(self, mocker, tmp_path, capsys):
        svc = _service(mocker)
        f = tmp_path / "weird.obb"
        f.touch()
        assert svc._compute_device_path(f, tmp_path) == "/sdcard"
        assert "does not match the expected naming convention" in capsys.readouterr().out

    def test_obb_with_non_numeric_version_falls_back(self, mocker, tmp_path, capsys):
        svc = _service(mocker)
        f = tmp_path / "main.notanumber.com.foo.bar.obb"
        f.touch()
        assert svc._compute_device_path(f, tmp_path) == "/sdcard"
        assert "does not match the expected naming convention" in capsys.readouterr().out

    def test_obb_with_single_segment_package_falls_back(self, mocker, tmp_path, capsys):
        svc = _service(mocker)
        f = tmp_path / "main.1.foo.obb"
        f.touch()
        assert svc._compute_device_path(f, tmp_path) == "/sdcard"
        assert "does not match the expected naming convention" in capsys.readouterr().out


class TestObbPackageConsistency:
    def test_no_warning_for_single_package_with_main_and_patch(self, mocker, tmp_path, capsys):
        svc = _service(mocker)
        files = [
            tmp_path / "main.1.com.example.app.obb",
            tmp_path / "patch.1.com.example.app.obb",
        ]
        for f in files:
            f.touch()
        svc._warn_on_mixed_obb_packages(files)
        out = capsys.readouterr().out
        assert "multiple packages" not in out

    def test_warns_when_obbs_declare_different_packages(self, mocker, tmp_path, capsys):
        svc = _service(mocker)
        files = [
            tmp_path / "main.1.com.foo.app.obb",
            tmp_path / "main.1.com.bar.app.obb",
        ]
        for f in files:
            f.touch()
        svc._warn_on_mixed_obb_packages(files)
        out = capsys.readouterr().out
        assert "multiple packages" in out
        assert "com.foo.app" in out
        assert "com.bar.app" in out
        assert "main.1.com.foo.app.obb" in out
        assert "main.1.com.bar.app.obb" in out

    def test_misnamed_obb_does_not_count_as_separate_package(self, mocker, tmp_path, capsys):
        svc = _service(mocker)
        files = [
            tmp_path / "main.1.com.example.app.obb",
            tmp_path / "weird.obb",
        ]
        for f in files:
            f.touch()
        svc._warn_on_mixed_obb_packages(files)
        out = capsys.readouterr().out
        assert "multiple packages" not in out

    def test_no_obbs_at_all(self, mocker, tmp_path, capsys):
        svc = _service(mocker)
        files = [tmp_path / "config.json", tmp_path / "data.bin"]
        for f in files:
            f.touch()
        svc._warn_on_mixed_obb_packages(files)
        assert capsys.readouterr().out == ""


class TestValidateBundleFilesMatch:
    def test_extracts_filename_and_checksum_from_v3_shape(self, mocker, tmp_path):
        svc = _service(mocker)
        f = tmp_path / "config.json"
        f.write_text("{}")

        bundle_files = [{
            "filename": "config.json",
            "location": "/sdcard",
            "checksum": {"value": "abc123", "type": "sha512"},
        }]
        local_hashes = {f: "abc123"}

        svc._validate_bundle_files_match(bundle_files, local_hashes, tmp_path)

    def test_raises_on_hash_mismatch(self, mocker, tmp_path):
        svc = _service(mocker)
        f = tmp_path / "config.json"
        f.write_text("{}")

        bundle_files = [{
            "filename": "config.json",
            "location": "/sdcard",
            "checksum": {"value": "remote-hash"},
        }]
        local_hashes = {f: "local-hash"}

        with pytest.raises(ValueError, match="content changed"):
            svc._validate_bundle_files_match(bundle_files, local_hashes, tmp_path)

    def test_raises_on_missing_local_file(self, mocker, tmp_path):
        svc = _service(mocker)

        bundle_files = [{
            "filename": "missing.json",
            "location": "/sdcard",
            "checksum": {"value": "h"},
        }]

        with pytest.raises(ValueError, match="not found locally"):
            svc._validate_bundle_files_match(bundle_files, {}, tmp_path)


class TestUrls:
    def test_list_uses_v3(self, mocker):
        svc = _service(mocker)
        svc.client.get.return_value = make_response({"data": [], "links": {}})

        svc.get_all_app_bundles_for_app("app-id")

        url = svc.client.get.call_args[0][0]
        assert url == "https://api.xrdm.app/api/v3/apps/app-id/app-bundles?per_page=20"

    def test_list_with_status_filter(self, mocker):
        svc = _service(mocker)
        svc.client.get.return_value = make_response({"data": [], "links": {}})

        svc.get_all_app_bundles_for_app("app-id", status="pending")

        url = svc.client.get.call_args[0][0]
        assert "status=pending" in url

    def test_detail_uses_v3(self, mocker):
        svc = _service(mocker)
        svc.client.get.return_value = make_response({"id": "b1"})

        svc.get_app_bundle_detail("b1")

        svc.client.get.assert_called_once_with(
            "https://api.xrdm.app/api/v3/app-bundles/b1",
            headers=svc.headers,
        )

    def test_update_label_uses_patch(self, mocker):
        svc = _service(mocker)
        svc.client.patch.return_value = make_response({"id": "b1", "label": "new"})

        svc.update_app_bundle_label("b1", "new")

        svc.client.patch.assert_called_once_with(
            "https://api.xrdm.app/api/v3/app-bundles/b1",
            json={"label": "new"},
            headers=svc.headers,
        )


def _setup_bundle_scan(mocker, tmp_path, file_names=("config.json", "data.bin")):
    """Build a folder with files and patch _scan_folder to return synthetic hashes."""
    folder = tmp_path / "bundle"
    folder.mkdir()
    apk = tmp_path / "build.apk"
    apk.write_bytes(b"apk-content")

    file_hashes = {}
    for i, name in enumerate(file_names):
        f = folder / name
        f.write_bytes(f"file{i}".encode())
        file_hashes[f] = f"file{i}-sha512"

    return folder, apk, file_hashes


class TestBundleUploadDedup:
    """upload_app_bundle is the headline customer feature — verify the dedup branches."""

    def test_full_dedup_existing_build_and_files(self, mocker, tmp_path):
        """When build AND all files exist, no APK or file uploads happen."""
        folder, apk, file_hashes = _setup_bundle_scan(mocker, tmp_path)
        svc = _service(mocker)

        mocker.patch.object(svc, "_scan_folder",
                            return_value=(folder, apk, "build-sha256", file_hashes))

        fake_apps_service = mocker.MagicMock()
        fake_apps_service.get_versions_by_sha256.return_value = [{"id": "existing-build"}]
        # All files exist
        existing_files = [
            {"id": f"file-{i}", "filename": path.name,
             "checksum": {"value": h, "type": "sha512"}}
            for i, (path, h) in enumerate(file_hashes.items())
        ]
        fake_apps_service.get_files_by_sha512.return_value = existing_files
        mocker.patch("abxr.app_bundles.AppsService", return_value=fake_apps_service)

        fake_files_service = mocker.MagicMock()
        mocker.patch("abxr.app_bundles.FilesService", return_value=fake_files_service)

        svc.create_app_bundle_from_existing = mocker.MagicMock(
            return_value={"id": "bundle-1"}
        )
        svc.finalize_app_bundle = mocker.MagicMock(
            return_value={"id": "bundle-1", "status": "processing"}
        )

        result = svc.upload_app_bundle(
            "app-1", str(folder), "1.0.0", "notes",
            silent=True, apk_path=str(apk),
        )

        assert result == {"id": "bundle-1", "status": "processing"}
        # No APK upload (build was reused)
        fake_apps_service.upload_file.assert_not_called()
        # No file uploads (all files were reused)
        fake_files_service.upload_file.assert_not_called()
        svc.create_app_bundle_from_existing.assert_called_once()
        svc.finalize_app_bundle.assert_called_once_with("bundle-1")

    def test_no_dedup_uploads_build_and_all_files(self, mocker, tmp_path):
        """When nothing exists, APK uploads, all files upload, bundle finalizes."""
        folder, apk, file_hashes = _setup_bundle_scan(mocker, tmp_path)
        svc = _service(mocker)

        mocker.patch.object(svc, "_scan_folder",
                            return_value=(folder, apk, "build-sha256", file_hashes))

        fake_apps_service = mocker.MagicMock()
        fake_apps_service.get_versions_by_sha256.return_value = []
        fake_apps_service.get_files_by_sha512.return_value = []
        fake_apps_service.upload_file.return_value = {
            "id": "v1", "appBundleId": "bundle-2",
        }
        mocker.patch("abxr.app_bundles.AppsService", return_value=fake_apps_service)

        fake_files_service = mocker.MagicMock()
        mocker.patch("abxr.app_bundles.FilesService", return_value=fake_files_service)

        svc.finalize_app_bundle = mocker.MagicMock(
            return_value={"id": "bundle-2", "status": "processing"}
        )

        result = svc.upload_app_bundle(
            "app-1", str(folder), "1.0.0", "notes",
            silent=True, apk_path=str(apk),
        )

        assert result == {"id": "bundle-2", "status": "processing"}
        # APK was uploaded with app_build_type='app-bundle'
        fake_apps_service.upload_file.assert_called_once()
        assert fake_apps_service.upload_file.call_args.kwargs["app_build_type"] == "app-bundle"
        # Every file was uploaded
        assert fake_files_service.upload_file.call_count == len(file_hashes)

    def test_partial_dedup_new_build_with_existing_files(self, mocker, tmp_path):
        """New build but some existing files: uploads APK + new files only, adds existing by ref."""
        folder, apk, file_hashes = _setup_bundle_scan(mocker, tmp_path,
                                                     file_names=("a.txt", "b.txt", "c.txt"))
        svc = _service(mocker)

        mocker.patch.object(svc, "_scan_folder",
                            return_value=(folder, apk, "build-sha256", file_hashes))

        paths = list(file_hashes.keys())
        existing_file_path = paths[0]
        existing_hash = file_hashes[existing_file_path]

        fake_apps_service = mocker.MagicMock()
        fake_apps_service.get_versions_by_sha256.return_value = []  # new build
        fake_apps_service.get_files_by_sha512.return_value = [{
            "id": "file-existing",
            "filename": existing_file_path.name,
            "checksum": {"value": existing_hash, "type": "sha512"},
        }]
        fake_apps_service.upload_file.return_value = {
            "id": "v1", "appBundleId": "bundle-3",
        }
        mocker.patch("abxr.app_bundles.AppsService", return_value=fake_apps_service)

        fake_files_service = mocker.MagicMock()
        mocker.patch("abxr.app_bundles.FilesService", return_value=fake_files_service)

        svc.add_files_to_app_bundle = mocker.MagicMock(return_value={"id": "bundle-3"})
        svc.finalize_app_bundle = mocker.MagicMock(
            return_value={"id": "bundle-3", "status": "processing"}
        )

        svc.upload_app_bundle(
            "app-1", str(folder), "1.0.0", "notes",
            silent=True, apk_path=str(apk),
        )

        # APK uploaded (new build)
        fake_apps_service.upload_file.assert_called_once()
        # One existing file added by reference
        svc.add_files_to_app_bundle.assert_called_once()
        added_files = svc.add_files_to_app_bundle.call_args[0][1]
        assert len(added_files) == 1
        assert added_files[0]["fileId"] == "file-existing"
        # Two new files uploaded (b.txt, c.txt)
        assert fake_files_service.upload_file.call_count == 2


class TestQueryExistingFilesByHash:
    """Direct test of the v3 checksum.value + filename access that this PR changed."""

    def test_matches_by_hash_and_filename(self, mocker, tmp_path):
        svc = _service(mocker)

        p1 = tmp_path / "a.json"
        p2 = tmp_path / "b.json"
        p1.touch()
        p2.touch()
        file_hashes = {p1: "hash-a", p2: "hash-b"}

        fake_apps_service = mocker.MagicMock()
        fake_apps_service.get_files_by_sha512.return_value = [
            {"id": "f1", "filename": "a.json",
             "checksum": {"value": "hash-a", "type": "sha512"}},
            {"id": "f2", "filename": "wrong-name.json",  # hash matches but name doesn't
             "checksum": {"value": "hash-b", "type": "sha512"}},
        ]
        mocker.patch("abxr.app_bundles.AppsService", return_value=fake_apps_service)

        result = svc._query_existing_files_by_hash("app-1", file_hashes, silent=True)

        # Only a.json matched (b.json's hash matched but filename didn't)
        assert p1 in result
        assert p2 not in result
        assert result[p1]["id"] == "f1"

    def test_empty_input_short_circuits(self, mocker):
        svc = _service(mocker)
        result = svc._query_existing_files_by_hash("app-1", {}, silent=True)
        assert result == {}


class TestBundleResume:
    """resume_app_bundle uses v3 'filename' and 'checksum.value' fields directly."""

    def test_happy_path_resumes_pending_bundle(self, mocker, tmp_path):
        folder, apk, file_hashes = _setup_bundle_scan(mocker, tmp_path,
                                                     file_names=("config.json",))
        svc = _service(mocker)

        mocker.patch.object(svc, "_scan_folder",
                            return_value=(folder, apk, "build-sha256", file_hashes))

        svc.get_app_bundle_detail = mocker.MagicMock(return_value={
            "id": "bundle-1",
            "status": "pending",
            "appBuild": {"checksum": {"value": "build-sha256", "type": "sha256"}},
        })
        # No existing files yet -> all need upload
        svc.get_all_files_for_app_bundle = mocker.MagicMock(return_value=[])

        fake_files_service = mocker.MagicMock()
        mocker.patch("abxr.app_bundles.FilesService", return_value=fake_files_service)
        svc.finalize_app_bundle = mocker.MagicMock(
            return_value={"id": "bundle-1", "status": "processing"}
        )

        result = svc.resume_app_bundle(
            "bundle-1", str(apk), str(folder), silent=True,
        )

        assert result == {"id": "bundle-1", "status": "processing"}
        # Single missing file gets uploaded
        assert fake_files_service.upload_file.call_count == 1

    def test_rejects_non_pending_bundle(self, mocker, tmp_path):
        svc = _service(mocker)
        svc.get_app_bundle_detail = mocker.MagicMock(return_value={
            "id": "bundle-1", "status": "available",
        })

        with pytest.raises(ValueError, match="Only 'pending' bundles can be resumed"):
            svc.resume_app_bundle(
                "bundle-1", "/fake.apk", str(tmp_path), silent=True,
            )

    def test_rejects_build_hash_mismatch(self, mocker, tmp_path):
        folder, apk, file_hashes = _setup_bundle_scan(mocker, tmp_path)
        svc = _service(mocker)

        mocker.patch.object(svc, "_scan_folder",
                            return_value=(folder, apk, "local-build-hash", file_hashes))

        svc.get_app_bundle_detail = mocker.MagicMock(return_value={
            "id": "bundle-1",
            "status": "pending",
            "appBuild": {"checksum": {"value": "different-remote-hash", "type": "sha256"}},
        })

        with pytest.raises(ValueError, match="build file mismatch"):
            svc.resume_app_bundle(
                "bundle-1", str(apk), str(folder), silent=True,
            )

    def test_skips_already_uploaded_files(self, mocker, tmp_path):
        """Files whose hash matches an existing bundle file should not be re-uploaded."""
        folder, apk, file_hashes = _setup_bundle_scan(mocker, tmp_path,
                                                     file_names=("a.txt", "b.txt"))
        svc = _service(mocker)

        mocker.patch.object(svc, "_scan_folder",
                            return_value=(folder, apk, "build-hash", file_hashes))

        paths = list(file_hashes.keys())
        # a.txt is already uploaded with matching hash + location
        existing_bundle_files = [{
            "filename": paths[0].name,
            "location": "/sdcard",
            "checksum": {"value": file_hashes[paths[0]], "type": "sha512"},
        }]

        svc.get_app_bundle_detail = mocker.MagicMock(return_value={
            "id": "bundle-1",
            "status": "pending",
            "appBuild": {"checksum": {"value": "build-hash"}},
        })
        svc.get_all_files_for_app_bundle = mocker.MagicMock(return_value=existing_bundle_files)

        fake_files_service = mocker.MagicMock()
        mocker.patch("abxr.app_bundles.FilesService", return_value=fake_files_service)
        svc.finalize_app_bundle = mocker.MagicMock(return_value={"id": "bundle-1"})

        svc.resume_app_bundle("bundle-1", str(apk), str(folder), silent=True)

        # Only b.txt should upload (a.txt was already there)
        assert fake_files_service.upload_file.call_count == 1
        uploaded_path = fake_files_service.upload_file.call_args[0][0]
        assert uploaded_path.endswith("b.txt")

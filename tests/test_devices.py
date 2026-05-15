from abxr.devices import DevicesService
from tests.conftest import make_response


def _service(mocker):
    svc = DevicesService("https://api.xrdm.app", "tok")
    svc.client = mocker.MagicMock()
    return svc


def test_get_all_devices_uses_v3(mocker):
    svc = _service(mocker)
    svc.client.get.return_value = make_response({"data": [{"id": "d1"}], "links": {}})

    result = svc.get_all_devices()

    assert result == [{"id": "d1"}]
    url = svc.client.get.call_args[0][0]
    assert url == "https://api.xrdm.app/api/v3/devices?per_page=20"


def test_get_device_detail(mocker):
    svc = _service(mocker)
    svc.client.get.return_value = make_response({"id": "d1"})

    result = svc.get_device_detail("d1")

    assert result == {"id": "d1"}
    svc.client.get.assert_called_once_with(
        "https://api.xrdm.app/api/v3/devices/d1",
        headers=svc.headers,
    )


def test_launch_app(mocker):
    svc = _service(mocker)
    svc.client.post.return_value = make_response({"status": "ok"})

    svc.launch_app("d1", "a1")

    svc.client.post.assert_called_once_with(
        "https://api.xrdm.app/api/v3/devices/d1/launch/a1",
        headers=svc.headers,
    )


def test_reboot_device(mocker):
    svc = _service(mocker)
    svc.client.post.return_value = make_response({}, content=b"")

    svc.reboot_device("d1")

    svc.client.post.assert_called_once_with(
        "https://api.xrdm.app/api/v3/devices/d1/reboot",
        headers=svc.headers,
    )


def test_factory_reset(mocker):
    svc = _service(mocker)
    svc.client.post.return_value = make_response({}, content=b"")

    svc.factory_reset_device("d1")

    svc.client.post.assert_called_once_with(
        "https://api.xrdm.app/api/v3/devices/d1/factory-reset",
        headers=svc.headers,
    )


def test_migrate_to_org(mocker):
    svc = _service(mocker)
    svc.client.post.return_value = make_response({"status": "ok"})

    svc.migrate_device_to_org("d1", "target-org", "target-token", "group-1")

    args, kwargs = svc.client.post.call_args
    assert args[0] == "https://api.xrdm.app/api/v3/devices/d1/migrate/target-org"
    assert kwargs["json"] == {
        "targetOrganizationToken": "target-token",
        "groupId": "group-1",
    }


def test_attach_tags(mocker):
    svc = _service(mocker)
    svc.client.post.return_value = make_response({"tags": ["a", "b"]})

    svc.attach_tags_to_device("d1", ["a", "b"])

    args, kwargs = svc.client.post.call_args
    assert args[0] == "https://api.xrdm.app/api/v3/devices/d1/tags/attach"
    assert kwargs["json"] == {"tags": ["a", "b"]}

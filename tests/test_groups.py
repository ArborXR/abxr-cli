from abxr.groups import GroupsService
from tests.conftest import make_response


def _service(mocker):
    svc = GroupsService("https://api.xrdm.app", "tok")
    svc.client = mocker.MagicMock()
    return svc


def test_get_all_groups(mocker):
    svc = _service(mocker)
    svc.client.get.return_value = make_response({"data": [{"id": "g1"}], "links": {}})

    result = svc.get_all_groups()

    assert result == [{"id": "g1"}]
    url = svc.client.get.call_args[0][0]
    assert url == "https://api.xrdm.app/api/v3/groups?per_page=20"


def test_create_group(mocker):
    svc = _service(mocker)
    svc.client.post.return_value = make_response({"id": "g1", "name": "new"})

    svc.create_group("new", parent_id="g0")

    args, kwargs = svc.client.post.call_args
    assert args[0] == "https://api.xrdm.app/api/v3/groups"
    assert kwargs["json"] == {"name": "new", "parentId": "g0"}


def test_get_group_details(mocker):
    svc = _service(mocker)
    svc.client.get.return_value = make_response({"id": "g1"})

    result = svc.get_group_details("g1")

    assert result == {"id": "g1"}
    svc.client.get.assert_called_once_with(
        "https://api.xrdm.app/api/v3/groups/g1",
        headers=svc.headers,
    )


def test_update_group(mocker):
    svc = _service(mocker)
    svc.client.put.return_value = make_response({"id": "g1", "name": "renamed"})

    svc.update_group("g1", "renamed")

    args, kwargs = svc.client.put.call_args
    assert args[0] == "https://api.xrdm.app/api/v3/groups/g1"
    assert kwargs["json"] == {"name": "renamed", "parentId": None}


def test_delete_group(mocker):
    svc = _service(mocker)
    svc.client.delete.return_value = make_response({}, content=b"")

    svc.delete_group("g1")

    svc.client.delete.assert_called_once_with(
        "https://api.xrdm.app/api/v3/groups/g1",
        headers=svc.headers,
    )

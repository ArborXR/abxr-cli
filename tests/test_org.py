from abxr.org import OrgService
from tests.conftest import make_response


def test_get_org_info_hits_v3(mocker):
    svc = OrgService("https://api.xrdm.app", "tok")
    svc.client = mocker.MagicMock()
    svc.client.get.return_value = make_response({"id": "org-1", "name": "Test Org"})

    result = svc.get_org_info()

    assert result == {"id": "org-1", "name": "Test Org"}
    svc.client.get.assert_called_once_with(
        "https://api.xrdm.app/api/v3/current-organization",
        headers=svc.headers,
    )

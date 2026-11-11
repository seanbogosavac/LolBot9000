import pytest

from api import RiotAPIError, RiotClient
from tests.conftest import PUUID_SEAN, RIOT_NAME_SEAN


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = {}

    def json(self):
        return self._payload


class FakeSession:
    """Records the calls RiotClient makes and replays queued responses."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def request(self, method, url, params=None, timeout=None):
        self.calls.append((method, url, params))
        return self.responses.pop(0)

    def close(self):
        pass


def client_with(*responses) -> RiotClient:
    return RiotClient(api_key="secret", session=FakeSession(*responses))


def test_get_riot_id_by_puuid_builds_the_account_endpoint_and_formats_the_name():
    client = client_with(FakeResponse(payload={"gameName": "SeanTheGoat", "tagLine": "EUW", "puuid": PUUID_SEAN}))
    assert client.get_riot_id_by_puuid(PUUID_SEAN) == RIOT_NAME_SEAN

    method, url, _ = client.session.calls[0]
    assert method == "GET"
    assert url == f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-puuid/{PUUID_SEAN}"


def test_get_riot_id_by_puuid_accepts_a_tagless_legacy_account():
    client = client_with(FakeResponse(payload={"gameName": "OldGuy", "tagLine": ""}))
    assert client.get_riot_id_by_puuid(PUUID_SEAN) == "OldGuy"


@pytest.mark.parametrize("payload", [{}, {"gameName": "", "tagLine": "EUW"}, "not a dict"])
def test_get_riot_id_by_puuid_rejects_an_answer_without_a_name(payload):
    client = client_with(FakeResponse(payload=payload))
    with pytest.raises(RiotAPIError, match="no game name"):
        client.get_riot_id_by_puuid(PUUID_SEAN)


def test_get_riot_id_by_puuid_reports_an_unknown_puuid():
    client = client_with(FakeResponse(status_code=404))
    with pytest.raises(RiotAPIError, match="not found"):
        client.get_riot_id_by_puuid(PUUID_SEAN)

import requests

from lolbot.api import ddragon
from lolbot.api.ddragon import champions_by_id, fetch_champions_data


def test_champion_data_comes_from_the_latest_ddragon_patch(monkeypatch):
    calls = []

    class Resp:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    def fake_get(url, timeout=None):
        calls.append((url, timeout))
        return Resp(["99.1.1", "13.14.1"] if url.endswith("versions.json") else {"data": {"Ahri": {"key": "103"}}})

    monkeypatch.setattr(ddragon.requests, "get", fake_get)
    assert fetch_champions_data() == {"data": {"Ahri": {"key": "103"}}}
    assert "/cdn/99.1.1/" in calls[1][0] and all(t for _, t in calls)


def test_champion_data_falls_back_to_empty_when_ddragon_is_down(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(ddragon.requests, "get", boom)
    assert fetch_champions_data() == {"data": {}}


def test_champions_are_mapped_by_numeric_id(monkeypatch):
    monkeypatch.setattr(ddragon, "fetch_champions_data", lambda: {"data": {"Ahri": {"key": "103", "name": "Ahri"}, "XinZhao": {"key": "5", "name": "Xin Zhao"}}})
    assert champions_by_id() == {103: "Ahri", 5: "Xin Zhao"}

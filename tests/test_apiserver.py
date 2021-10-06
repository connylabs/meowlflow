import json
import os
import urllib
import requests
import pytest

import meowlflow

from fastapi.testclient import TestClient
from meowlflow.main import app
from meowlflow.config import GCONFIG

DEFAULT_PREFIX = "http://localhost:5000"


class TestServer:
    @property
    def token(self):
        return "changeme"

    def headers(self):
        d = {"Content-Type": "application/json"}
        if self.token:
            d["token"] = self.token
        return d

    class Client(object):
        def __init__(self, client, headers=None):
            self.client = client
            self.headers = headers

        def _request(self, method, path, params, body):
            if params:
                path = path + "?" + urllib.urlencode(params)
            return getattr(self.client, method)(
                path, data=json.dumps(body), headers=self.headers
            )

        def get(self, path, params=None, body=None):
            return self._request("get", path, params, body)

        def delete(self, path, params=None, body=None):
            return self._request("delete", path, params, body)

        def post(self, path, params=None, body=None):
            return self._request("post", path, params, body)

    def json(self, res):
        return res.json()

    def content(self, res):
        return res.data

    def _url_for(self, path):
        return DEFAULT_PREFIX + self.api_prefix + path

    @property
    def api_prefix(self):
        return os.getenv("MEOWLFLOW_API_PREFIX", "")

    @pytest.fixture(autouse=True)
    def client(self):
        client = TestClient(app)
        return client

    def test_root(self, client):
        url = self._url_for("")
        res = self.Client(client, self.headers()).get(url)
        assert res.status_code == 200
        assert self.json(res) == {"version": meowlflow.__version__}

    def test_version(self, client):
        url = self._url_for("")
        res = self.Client(client, self.headers()).get(url)
        assert res.status_code == 200
        assert self.json(res) == {"version": meowlflow.__version__}

    def test_error(self, client):
        url = self._url_for("/error")
        res = self.Client(client, self.headers()).get(url)
        assert res.status_code == 403

    def test_404(self, client):
        url = self._url_for("/unknown")
        res = self.Client(client, self.headers()).get(url)
        assert res.status_code == 404

    def test_500(self, client):
        url = self._url_for("/error_uncatched")

        res = self.Client(client, self.headers()).get(url)
        assert res.status_code == 500

    def test_unauth_access(self, client):
        url = self._url_for("")
        headers = self.headers()
        headers["token"] = "badtoken"
        res = self.Client(client, headers).get(url)
        assert res.status_code == 401


BaseTestServer = TestServer


@pytest.mark.usefixtures("live_server")
class LiveTestServer(BaseTestServer):
    class Client(object):
        def __init__(self, client, headers):
            self.client = requests
            self.headers = headers

        def _request(self, method, path, params, body):
            return getattr(self.client, method)(
                path, params=params, data=json.dumps(body), headers=self.headers
            )

        def get(self, path, params=None, body=None):
            return self._request("get", path, params, body)

        def delete(self, path, params=None, body=None):
            return self._request("delete", path, params, body)

        def post(self, path, params=None, body=None):
            return self._request("post", path, params, body)

    def content(self, res):
        return res.content

    def _url_for(self, path):
        return request.url_root + self.api_prefix + path

    def json(self, res):
        return res.json()


def get_server_class():
    if os.getenv("MEOWLFLOW_TEST_LIVESERVER", "false") == "true":
        return LiveTestServer
    else:
        return BaseTestServer


ServerTest = get_server_class()

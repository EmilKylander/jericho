from jericho.plugin.async_http import AsyncHTTP
import pytest

TEST_URL = "https://google.com"


class AsyncMock:
    def __init__(self):
        self.headers = {"content-type": "text/html"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *error_info):
        return self

    async def read(self):
        return b"im alive!"

    async def headers(self):
        return {"header": "value"}


class AsyncMockImage:
    def __init__(self):
        self.headers = {"content-type": "image/gif"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *error_info):
        return self

    async def read(self):
        return b"im alive!"

    async def headers(self):
        return {"header": "value"}


class ClusterMock:
    def send_job_message(self, _):
        pass


@pytest.mark.asyncio
async def test__run_with_get(monkeypatch):
    def mock_client_get(self, params, ssl, allow_redirects, timeout, headers):
        mock_response = AsyncMock()
        mock_response.status = 200
        return mock_response

    cluster_mock = ClusterMock()

    async_http = AsyncHTTP(
        dns_cache={},
        max_requests=10,
        nameservers=["8.8.8.8"],
        rank=1,
        cluster=cluster_mock,
    )
    monkeypatch.setattr("aiohttp.ClientSession.get", mock_client_get)
    async for entry in async_http.get(
        [TEST_URL], settings={"status": 200, "timeout": 60}
    ):
        assert entry == (
            TEST_URL,
            "im alive!",
            {"content-type": "text/html"},
            "im alive!",
        )


@pytest.mark.asyncio
async def test__run_with_get_ignore_image(monkeypatch):
    def mock_client_get(self, params, ssl, allow_redirects, timeout, headers):
        mock_response = AsyncMockImage()
        mock_response.status = 200

        return mock_response

    responses = []

    cluster_mock = ClusterMock()

    async_http = AsyncHTTP(
        dns_cache={},
        max_requests=10,
        nameservers=["8.8.8.8"],
        rank=1,
        cluster=cluster_mock,
    )
    monkeypatch.setattr("aiohttp.ClientSession.get", mock_client_get)
    async for entry in async_http.get(
        [TEST_URL], settings={"status": 200, "timeout": 60, "ignore_multimedia": True}
    ):
        responses.append(entry)
    assert responses == []


def test__is_multi_media():
    cluster_mock = ClusterMock()

    a = AsyncHTTP(
        dns_cache={},
        max_requests=10,
        nameservers=["8.8.8.8"],
        rank=1,
        cluster=cluster_mock,
    )
    assert a._is_multi_media("image/png") is True


def test__is_multi_media_false_with_html():
    cluster_mock = ClusterMock()

    a = AsyncHTTP(
        dns_cache={},
        max_requests=10,
        nameservers=["8.8.8.8"],
        rank=1,
        cluster=cluster_mock,
    )
    assert a._is_multi_media("text/html") is False

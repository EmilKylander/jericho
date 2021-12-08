from jericho.plugin.async_http import AsyncHTTP, InvalidSetOfDomains
import pytest

TEST_URL = "https://google.com"

class AsyncMock:
    def __init__(self):
        self.headers = {"content-type": "text/html"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *error_info):
        return self

    async def text(self):
        return "im alive!"

    async def headers(self):
        return {"header": "value"}

class AsyncMockImage:
    def __init__(self):
        self.headers = {"content-type": "image/gif"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *error_info):
        return self

    async def text(self):
        return "im alive!"

    async def headers(self):
        return {"header": "value"}


@pytest.mark.asyncio
async def test__run_with_head(monkeypatch):
    def mock_client_get(self, params, ssl, allow_redirects, timeout, headers):
        mock_response = AsyncMock()
        mock_response.status = 200
        return mock_response

    async_http = AsyncHTTP()
    monkeypatch.setattr("aiohttp.ClientSession.head", mock_client_get)
    resp = await async_http.head(
        [TEST_URL],
        settings={
            "status": 200,
            "timeout": 5,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
            },
        },
    )
    assert resp == [(TEST_URL, "", "content-type: text/html")]


@pytest.mark.asyncio
async def test__run_with_get(monkeypatch):
    def mock_client_get(self, params, ssl, allow_redirects, timeout, headers):
        mock_response = AsyncMock()
        mock_response.status = 200
        return mock_response

    async_http = AsyncHTTP()
    monkeypatch.setattr("aiohttp.ClientSession.get", mock_client_get)
    resp = await async_http.get([TEST_URL], settings={"status": 200, "timeout": 60})
    assert resp == [(TEST_URL, "im alive!", "content-type: text/html")]


@pytest.mark.asyncio
async def test__run_with_get_ignore_image(monkeypatch):
    def mock_client_get(self, params, ssl, allow_redirects, timeout):
        mock_response = AsyncMockImage()
        mock_response.status = 200
        return mock_response

    async_http = AsyncHTTP()
    monkeypatch.setattr("aiohttp.ClientSession.get", mock_client_get)
    resp = await async_http.get(
        [TEST_URL], settings={"status": 200, "timeout": 5, "ignore_multimedia": True}
    )
    assert resp == []


@pytest.mark.asyncio
async def test_should_not_be_ok_with_non_str_lists(monkeypatch):
    def mock_client_get(self, params, ssl, allow_redirects, timeout):
        mock_response = AsyncMockImage()
        mock_response.status = 200
        return mock_response

    async_http = AsyncHTTP()
    monkeypatch.setattr("aiohttp.ClientSession.get", mock_client_get)
    with pytest.raises(InvalidSetOfDomains) as e_info:
        resp = await async_http.get(
            ["https://google.com", None, "https://example.com"],
            settings={"status": 200, "timeout": 5, "ignore_multimedia": True},
        )


@pytest.mark.asyncio
async def test_should_not_be_ok_with_non_str_lists_as_head(monkeypatch):
    def mock_client_get(self, params, ssl, allow_redirects, timeout):
        mock_response = AsyncMockImage()
        mock_response.status = 200
        return mock_response

    async_http = AsyncHTTP()
    monkeypatch.setattr("aiohttp.ClientSession.get", mock_client_get)
    with pytest.raises(InvalidSetOfDomains) as e_info:
        resp = await async_http.head(
            ["https://google.com", None, "https://example.com"],
            settings={"status": 200, "timeout": 5, "ignore_multimedia": True},
        )


def test__is_multi_media():
    a = AsyncHTTP()
    assert a._is_multi_media("image/png") is True


def test__is_multi_media_false_with_html():
    a = AsyncHTTP()
    assert a._is_multi_media("text/html") is False

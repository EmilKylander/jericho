from jericho.plugin.threaded_async_http import ThreadedAsyncHTTP
from jericho.enums.http_request_methods import HttpRequestMethods


class MockAsyncHTTP:
    async def head(self, domains, settings):
        return domains, settings

    async def get(self, domains, settings):
        return domains, settings


class MockAsyncHTTPArray:
    async def head(self, domains, settings):
        return ["https://google.com"]

    async def get(self, domains, settings):
        return ["https://google.com"]


async def test__run_with_head():
    async_http = MockAsyncHTTP()
    threaded_async_http = ThreadedAsyncHTTP(
        async_http,
        1,
        {
            "max_head_timeout": 5,
            "ignore_multimedia": True,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
            },
        },
    )
    resp = await threaded_async_http._send_head_request(["https://google.com"])
    assert resp == (
        ["https://google.com"],
        {
            "status": 200,
            "timeout": 5,
            "ignore_multimedia": True,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
            },
        },
    )
    threaded_async_http.close()


async def test__run_with_get():
    async_http = MockAsyncHTTP()
    threaded_async_http = ThreadedAsyncHTTP(
        async_http,
        1,
        {
            "max_get_timeout": 5,
            "ignore_multimedia": True,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
            },
        },
    )
    resp = await threaded_async_http._send_get_request(["https://google.com"])
    assert resp == (
        ["https://google.com"],
        {
            "status": 200,
            "timeout": 5,
            "ignore_multimedia": True,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
            },
        },
    )
    threaded_async_http.close()


def test_send():
    async_http = MockAsyncHTTPArray()
    threaded_async_http = ThreadedAsyncHTTP(
        async_http, 1, {"max_get_timeout": 5, "ignore_multimedia": True}
    )

    threaded_async_http.start_bulk(["https://google.com"], HttpRequestMethods.GET)
    assert threaded_async_http.get_response() == ["https://google.com"]
    threaded_async_http.close()


def test_send_head():
    async_http = MockAsyncHTTPArray()
    threaded_async_http = ThreadedAsyncHTTP(
        async_http,
        1,
        {
            "max_head_timeout": 5,
            "ignore_multimedia": True,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
            },
        },
    )

    threaded_async_http.start_bulk(["https://google.com"], HttpRequestMethods.HEAD)
    assert threaded_async_http.get_response() == ["https://google.com"]
    threaded_async_http.close()

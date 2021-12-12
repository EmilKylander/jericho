from jericho.plugin.threaded_async_http import ThreadedAsyncHTTP
from jericho.enums.http_request_methods import HttpRequestMethods


class MockAsyncHTTP:
    async def head(self, domains, settings):
        return domains, settings

    async def get(self, domains, settings):
        return domains, settings


class MockAsyncHTTPArray:
    async def head(self, domains, settings):
        return [("https://google.com", "testing", "test: header"), ("https://yahoo.com", "testing123", "test: header")]

    async def get(self, domains, settings):
        return [("https://google.com", "testing", "test: header"), ("https://yahoo.com", "testing123", "test: header")]

def test_send():
    async_http = MockAsyncHTTPArray()
    threaded_async_http = ThreadedAsyncHTTP(
        async_http, 1, {"max_get_timeout": 5, "ignore_multimedia": True}
    )

    threaded_async_http.start_bulk(["https://google.com", "https://yahoo.com"])
    for res in threaded_async_http.get_response():
        if res[0] == "https://google.com":
            assert res == ("https://google.com", "testing", "test: header")

        if res[0] == "https://yahoo.com":
            assert res == ("https://yahoo.com", "testing123", "test: header")
        
    threaded_async_http.close()

from threading import Thread
import queue
import multiprocessing
from jericho.plugin.threaded_async_http import ThreadedAsyncHTTP


class MockAsyncHTTPArray:
    async def get(self, domains, settings):
        return [(domain, f"test {domain}", {"header": "value"}) for domain in domains]


def test_send():
    async_http = MockAsyncHTTPArray()
    finish_queue = queue.Queue()
    threaded_async_http = ThreadedAsyncHTTP(
        async_http,
        1,
        {"max_get_timeout": 1, "ignore_multimedia": True},
        finish_queue,
        False,
        False,
        [{"endpoint": "/test.php"}],
    )

    threaded_async_http.start_bulk(["https://google.com", "https://yahoo.com"], 2)

    assert finish_queue.get() == {
        "status": "result",
        "url": "https://google.com/test.php",
        "html": "test https://google.com/test.php",
        "headers": {"header": "value"},
    }
    assert finish_queue.get() == {
        "status": "result",
        "url": "https://yahoo.com/test.php",
        "html": "test https://yahoo.com/test.php",
        "headers": {"header": "value"},
    }

    assert finish_queue.get() == {"status": "done"}


def test_send_ignore_endpoints():
    async_http = MockAsyncHTTPArray()
    finish_queue = queue.Queue()
    threaded_async_http = ThreadedAsyncHTTP(
        async_http,
        1,
        {"max_get_timeout": 1, "ignore_multimedia": True},
        finish_queue,
        False,
        True,
        [{"endpoint": "/test.php"}],
    )

    threaded_async_http.start_bulk(["https://google.com", "https://yahoo.com"], 2)

    assert finish_queue.get() == {
        "status": "result",
        "url": "https://google.com",
        "html": "test https://google.com",
        "headers": {"header": "value"},
    }
    assert finish_queue.get() == {
        "status": "result",
        "url": "https://yahoo.com",
        "html": "test https://yahoo.com",
        "headers": {"header": "value"},
    }

    assert finish_queue.get() == {"status": "done"}


def test_send_scan_both_schemes():
    async_http = MockAsyncHTTPArray()
    finish_queue = queue.Queue()
    threaded_async_http = ThreadedAsyncHTTP(
        async_http,
        1,
        {"max_get_timeout": 1, "ignore_multimedia": True},
        finish_queue,
        True,
        False,
        [{"endpoint": "/test.php"}],
    )

    threaded_async_http.start_bulk(["https://google.com", "https://yahoo.com"], 2)

    assert finish_queue.get() == {
        "status": "result",
        "url": "https://google.com/test.php",
        "html": "test https://google.com/test.php",
        "headers": {"header": "value"},
    }
    assert finish_queue.get() == {
        "status": "result",
        "url": "http://google.com/test.php",
        "html": "test http://google.com/test.php",
        "headers": {"header": "value"},
    }
    assert finish_queue.get() == {
        "status": "result",
        "url": "https://yahoo.com/test.php",
        "html": "test https://yahoo.com/test.php",
        "headers": {"header": "value"},
    }
    assert finish_queue.get() == {
        "status": "result",
        "url": "http://yahoo.com/test.php",
        "html": "test http://yahoo.com/test.php",
        "headers": {"header": "value"},
    }

    assert finish_queue.get() == {"status": "done"}


def test_send_scan_both_schemes_ignore_endpoints():
    async_http = MockAsyncHTTPArray()
    finish_queue = queue.Queue()
    threaded_async_http = ThreadedAsyncHTTP(
        async_http,
        1,
        {"max_get_timeout": 1, "ignore_multimedia": True},
        finish_queue,
        True,
        True,
        [{"endpoint": "/test.php"}],
    )

    threaded_async_http.start_bulk(["https://google.com", "https://yahoo.com"], 2)

    assert finish_queue.get() == {
        "status": "result",
        "url": "https://google.com",
        "html": "test https://google.com",
        "headers": {"header": "value"},
    }
    assert finish_queue.get() == {
        "status": "result",
        "url": "http://google.com",
        "html": "test http://google.com",
        "headers": {"header": "value"},
    }
    assert finish_queue.get() == {
        "status": "result",
        "url": "https://yahoo.com",
        "html": "test https://yahoo.com",
        "headers": {"header": "value"},
    }
    assert finish_queue.get() == {
        "status": "result",
        "url": "http://yahoo.com",
        "html": "test http://yahoo.com",
        "headers": {"header": "value"},
    }

    assert finish_queue.get() == {"status": "done"}

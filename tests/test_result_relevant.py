#!/bin/python3
from jericho.plugin.async_http import AsyncHTTP
from jericho.plugin.investigate import Investigate
from jericho.plugin.diff import Diff
from jericho.plugin.output_verifier import OutputVerifier
from jericho.plugin.result_is_relevant import ResultRelevant
from jericho.repositories.cache_lookup import CacheLookup
from jericho.repositories.result_lookup import ResultLookup
from jericho.repositories.endpoints_lookup import EndpointsLookup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jericho.models import *
from jericho.repositories.cache_lookup import CacheLookup
from sqlalchemy.ext.declarative import declarative_base


engine = create_engine("sqlite:///:memory:", echo=True)
Base.metadata.create_all(engine)


class MockNormalHeaders:
    def get(self, _):
        return "text/html"


class AsyncMock:
    def __init__(self):
        self.headers = MockNormalHeaders()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *error_info):
        return self

    async def text(self):
        return "im alive!"


Session = sessionmaker(bind=engine)
session = Session()

diff = Diff()
investigate = Investigate()
result_lookup = ResultLookup(session)
cache_lookup = CacheLookup(session)
async_http = AsyncHTTP()
output_verifier = OutputVerifier()

result_relevant = ResultRelevant(
    diff=diff,
    investigate=investigate,
    result_lookup=result_lookup,
    cache_lookup=cache_lookup,
    async_http=async_http,
    output_verifier=output_verifier,
    configuration={"max_result_and_404_percent_diff": 60},
)

result_relevant_with_cache = ResultRelevant(
    diff=diff,
    investigate=investigate,
    result_lookup=result_lookup,
    cache_lookup=cache_lookup,
    async_http=async_http,
    output_verifier=output_verifier,
    configuration={"max_result_and_404_percent_diff": 60},
)


cache_lookup.save_content("https://google.com", "not found sorry")


def test_is_relevant_based_on_string_pattern_with_cache():
    assert (
        result_relevant_with_cache.check(
            "https://google.com/phpinfo.php",
            "<title>phpinfo()</title>asdasda",
            [{"endpoint": "/phpinfo.php", "pattern": "phpinfo()"}],
        )
        is True
    )


def test_is_relevant_based_on_string_pattern_without_cache_data(monkeypatch):
    def mock_client_get(self, params, ssl, allow_redirects, timeout, headers):
        mock_response = AsyncMock()
        mock_response.status = 200
        return mock_response

    monkeypatch.setattr("aiohttp.ClientSession.get", mock_client_get)

    cache_lookup.delete("https://google.com")
    assert (
        result_relevant_with_cache.check(
            "https://google.com/phpinfo.php",
            "<title>phpinfo()</title>asdasda",
            [{"endpoint": "/phpinfo.php", "pattern": "phpinfo()"}],
        )
        is True
    )


def test_is_relevant_based_on_string_pattern_except_if_result_exist():
    result_lookup.delete_all()
    result_lookup.save("https://google.com/phpinfo.php", "aaaa")
    assert (
        result_relevant.check(
            "https://google.com/phpinfo.php",
            "<title>phpinfo()</title>asdasda",
            [{"endpoint": "/phpinfo.php", "pattern": "aaaa"}],
        )
        is False
    )


def test_is_relevant_based_on_string_same_content():
    cache_lookup.delete("https://google.com")
    cache_lookup.save_content("https://google.com", "found")
    assert (
        result_relevant.check(
            "https://google.com/phpinfo.php",
            "not found sorry",
            [{"endpoint": "/phpinfo.php", "pattern": "found"}],
        )
        is False
    )


def test_is_relevant_based_on_string_same_content_type():
    cache_lookup.delete("https://google.com")
    cache_lookup.save_content("https://google.com", "not found sorry")

    assert (
        result_relevant.check(
            "https://google.com/package.json",
            '{"test": "testing"}',
            [{"endpoint": "/package.json", "pattern": "JSON"}],
        )
        is True
    )


def test_get_json_pattern_from_url():
    for format in output_verifier.formats():
        assert (
            result_relevant._get_endpoint_from_url(
                "https://google.com/package.json",
                [{"endpoint": "/package.json", "pattern": format}],
            )
            is format
        )


def test_get_string_pattern_from_url():
    assert (
        result_relevant._get_endpoint_from_url(
            "https://google.com/package.json",
            [{"endpoint": "/package.json", "pattern": '{"test": "testing"}'}],
        )
        is '{"test": "testing"}'
    )

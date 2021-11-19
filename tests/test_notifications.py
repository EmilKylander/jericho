#!/bin/python3
from jericho.plugin.notifications import Notifications
from jericho.plugin.async_http import AsyncHTTP
import pytest
import asyncio
import yaml


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

    def text(self):
        return "im alive!"


sample_notification_config = yaml.safe_load(
    """
  slack:
    type: POST
    url: https://hooks.slack.com/services/sfuhfsiudfhisdu/oaisjdoiasjdoaisjd
    data:
      text: result *url*
    headers:
    Content-Type: application/json"""
)

sample_notification_config_get = yaml.safe_load(
    """
  slack:
    type: GET
    url: https://hooks.slack.com/services/sfuhfsiudfhisdu/oaisjdoiasjdoaisjd
    data:
      text: result *url*
    headers:
    Content-Type: application/json"""
)


def test_replace_post_data_with_url():
    notifications = Notifications(sample_notification_config)
    res = notifications._replace_data_var_with_url(
        sample_notification_config["slack"]["data"],
        "https://hooks.slack.com/services/sfuhfsiudfhisdu/oaisjdoiasjdoaisjd",
    )
    assert res == {
        "text": "result https://hooks.slack.com/services/sfuhfsiudfhisdu/oaisjdoiasjdoaisjd"
    }


def test__send_notification_get(monkeypatch):
    async def mock_client_get(self, params, ssl, allow_redirects, headers):
        mock_response = AsyncMock()
        mock_response.status = 200
        return mock_response

    monkeypatch.setattr("aiohttp.ClientSession.get", mock_client_get)

    notifications = Notifications(sample_notification_config)

    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(
        notifications._send_notification_get(
            sample_notification_config["slack"]["data"],
            "https://hooks.slack.com/services/sfuhfsiudfhisdu/oaisjdoiasjdoaisjd",
        )
    )

    assert res.text() == "im alive!"


def test__send_notification_post(monkeypatch):
    async def mock_client_post(self, params, ssl, allow_redirects, headers, data):
        mock_response = AsyncMock()
        mock_response.status = 200
        return mock_response

    monkeypatch.setattr("aiohttp.ClientSession.post", mock_client_post)

    notifications = Notifications(sample_notification_config)

    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(
        notifications._send_notification_post(
            sample_notification_config["slack"],
            "https://hooks.slack.com/services/sfuhfsiudfhisdu/oaisjdoiasjdoaisjd",
        )
    )

    assert res.text() == "im alive!"


def test_send_notification(monkeypatch):
    async def mock_client_post(self, params, ssl, allow_redirects, headers, data):
        mock_response = AsyncMock()
        mock_response.status = 200
        return mock_response

    monkeypatch.setattr("aiohttp.ClientSession.post", mock_client_post)

    notifications = Notifications(sample_notification_config)

    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(
        notifications._send_notification_post(
            sample_notification_config["slack"],
            "https://hooks.slack.com/services/sfuhfsiudfhisdu/oaisjdoiasjdoaisjd",
        )
    )

    assert res.text() == "im alive!"


def test_send_notification_get(monkeypatch):
    async def mock_client_post(self, params, ssl, allow_redirects, headers, data):
        mock_response = AsyncMock()
        mock_response.status = 200
        return mock_response

    monkeypatch.setattr("aiohttp.ClientSession.post", mock_client_post)

    notifications = Notifications(sample_notification_config_get)

    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(
        notifications._send_notification(
            sample_notification_config["slack"],
            "https://hooks.slack.com/services/sfuhfsiudfhisdu/oaisjdoiasjdoaisjd",
        )
    )

    assert res.text() == "im alive!"


def test_run_all(monkeypatch):
    async def mock_client_get(self, params, ssl, allow_redirects, headers):
        mock_response = AsyncMock()
        mock_response.status = 200
        return mock_response

    monkeypatch.setattr("aiohttp.ClientSession.get", mock_client_get)

    notifications = Notifications(sample_notification_config_get)

    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(
        notifications.run_all(
            "https://hooks.slack.com/services/sfuhfsiudfhisdu/oaisjdoiasjdoaisjd"
        )
    )

    assert res[0].text() == "im alive!"

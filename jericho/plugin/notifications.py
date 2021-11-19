#!/bin/python3
import logging
import typing
import json
from aiohttp import ClientSession, ClientResponse
from jericho.enums.http_request_methods import HttpRequestMethods


class Notifications:
    def __init__(self, notifications_configuration):
        """Initialize the notifications"""
        self.notifications_configuration = notifications_configuration
        self.url_replacement_string = "*url*"

    def _replace_data_var_with_url(self, data: dict, url: str):
        """We should replace the url variable from the data dictionary from the configuration"""
        new_dict = {}
        for key, value in data.items():
            new_dict[key] = value.replace("*url*", url)

        return new_dict

    async def _send_notification_get(
        self, notification_config: dict, url: str
    ) -> ClientResponse:
        """Send the notification through GET HTTP method"""
        async with ClientSession() as session:
            return await session.get(
                notification_config.get("url", "").replace(
                    self.url_replacement_string, url
                ),
                ssl=False,
                allow_redirects=False,
                headers=notification_config.get("headers", {}),
            )

    async def _send_notification_post(
        self, notification_config: dict, url: str
    ) -> ClientResponse:
        """Send the notification through POST HTTP method"""
        post_data = self._replace_data_var_with_url(
            notification_config.get("data", {}), url
        )

        notification_headers = notification_config.get("headers") or {}
        for key, value in notification_headers.items():
            if key.lower() == "content-type" and value.lower() == "application/json":
                post_data = json.dumps(post_data)

        async with ClientSession() as session:
            return await session.post(
                notification_config.get("url", "").replace(
                    self.url_replacement_string, url
                ),
                ssl=False,
                allow_redirects=False,
                headers=notification_config.get("headers", {}),
                data=post_data,
            )

    async def _send_notification(
        self, notification_config: dict, url: str
    ) -> ClientResponse:
        """Decide to run GET or POST methods based on the configuration"""
        if notification_config.get("type", "").lower() == HttpRequestMethods.GET.value:
            return await self._send_notification_get(notification_config, url)

        if notification_config.get("type", "").lower() == HttpRequestMethods.POST.value:
            return await self._send_notification_post(notification_config, url)

    async def run_all(self, url: str) -> typing.List:
        """Take a url and send it to all HTTP notifications url"""
        res = []
        for (
            notification_name,
            notification_config,
        ) in self.notifications_configuration.items():
            logging.info(
                "Sending a %s notification with url %s", notification_name, url
            )
            try:
                resp = await self._send_notification(notification_config, url)
                res.append(resp)
                logging.info("Sent the %s notification!", notification_name)
            except Exception as err:
                logging.error(
                    "Could not send the %s notification because of %s",
                    notification_name,
                    err,
                )
        return res

#!/bin/python3
import aiohttp
import socket
import logging
import typing
import aiodns
import asyncio
import random
import validators
from async_retrying import retry
from async_retrying import RetryError
from aiodnsresolver import Resolver, TYPES

from aiohttp.client_reqrep import ClientResponse
from aiohttp import ClientSession
from urllib.parse import urlparse

class EmptyDNSResolve(Exception):
    pass

class HTTPError(Exception):
    pass

async def get_nameservers(_, __):
    yield (0.5, ('8.8.8.8', 53))
    yield (0.5, ('1.1.1.1', 53))
    yield (1.0, ('8.8.8.8', 53))
    yield (1.0, ('1.1.1.1', 53))

async def fetch(self, url):
        resolver, clear_cache = Resolver(get_nameservers=get_nameservers)
        try:
            async with ClientSession(
                connector=aiohttp.TCPConnector(
                    ssl=False,
                    enable_cleanup_closed=True,
                    family=socket.AF_INET,
                    force_close=True,
                    resolver=resolver
                ),
                cookie_jar=aiohttp.DummyCookieJar(),
                timeout=aiohttp.ClientTimeout(total=10,sock_connect=10,sock_read=10)
            ) as session:
                headers = {
                    "User-Agent": self.settings['user_agent'],
                    "Connection": "close",
                }

                logging.debug("Sending a GET request to %s", url)
                async with session.get(
                    url,
                    ssl=False,
                    allow_redirects=False,
                    timeout=10,
                    headers=headers
                ) as response:
                    if str(response.status)[0] == "3":
                        redirect_url = response.headers.get("Location")
                        if redirect_url is None:
                            logging.error(
                                "A status %s gave no location header on domain %s",
                                response.status,
                                url,
                            )
                            return ""

                        # Sometimes the Location is a relative path
                        if redirect_url[0] == "/":
                            redirect_url = url + redirect_url

                        if urlparse(url).netloc.replace("www.", "") != urlparse(redirect_url).netloc.replace("www.", ""):
                            logging.exception("The URL %s and URL %s is not the same domain, skipping..", url, redirect_url)
                            return None

                        return await self.fetch(
                            redirect_url
                        )

                    #response_content = await self._process_response(
                    #    url, response
                    #)

                    logging.debug("Done with GET request %s", url)

                    #if response_content:
                    #    return {'url': response_content[0], 'content': response_content[1], 'headers': response_content[2]}

                    return None
        except Exception as err:
            logging.error("Error on %s. Error: %s", url, err)
            #raise err

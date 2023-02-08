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
from aiodnsresolver import Resolver, ResolverLoggerAdapter
from aiodnsresolver import (
    TYPES,
    Resolver,
    DnsError,
    DnsRecordDoesNotExist,
)
from aiohttp.client_reqrep import ClientResponse
from aiohttp import ClientSession
from urllib.parse import urlparse
from jericho.repositories.dns_cache_lookup import DnsCacheLookup
from jericho.helpers import chunks

class EmptyDNSResolve(Exception):
    pass

class HTTPError(Exception):
    pass

logging.getLogger("aiodnsresolver").setLevel(logging.CRITICAL)


class AioHttpDnsResolver(aiohttp.abc.AbstractResolver):
    def __init__(self, nameservers):
        super().__init__()
        self.resolver, self.clear_cache = Resolver(get_nameservers=self.get_nameservers)
        self.nameservers = nameservers

    async def get_nameservers(self, _, __):
        domain_list_chunk = chunks(self.nameservers, 10)
        for nameserver_chunk_raw in domain_list_chunk:
            nameserver_list = [0.5]
            for nameserver in nameserver_chunk_raw:
                nameserver_list.append((nameserver, 53))

            nameserver_chunk = tuple(nameserver_list)
            yield nameserver_chunk

    async def resolve(self, host, port=0, family=socket.AF_INET):
        # Use ipv4 unless requested otherwise
        # This is consistent with the default aiohttp + aiodns AsyncResolver
        record_type = \
            TYPES.AAAA if family == socket.AF_INET6 else \
            TYPES.A

        try:
            ip_addresses = await self.resolver(host, record_type)
        except DnsRecordDoesNotExist as does_not_exist:
            raise OSError(0, '{} does not exist'.format(host)) from does_not_exist
        except DnsError as dns_error:
            raise OSError(0, '{} failed to resolve'.format(host)) from dns_error

        return [{
            'hostname': host,
            'host': str(ip_address),
            'port': port,
            'family': family,
            'proto': socket.IPPROTO_TCP,
            'flags': socket.AI_NUMERICHOST,
        } for ip_address in ip_addresses]

    async def close(self):
        await self.clear_cache()

class AsyncFetch():
    def __init__(self, settings = {}):
        self.settings = settings
        self.multimedia_content_types: list = ["audio", "image", "video", "font"]
        self.lock: asyncio.Lock = asyncio.Lock()
        self.dns_cache_lookup = DnsCacheLookup()
        self.dns_requests: int = 0
        self.dns_responses: int = 0
        self.nameserver = ''

        if 'user_agent' not in settings:
            self.settings['user_agent'] = 'Jericho'

        if 'status' not in settings:
            self.settings['status'] = -1

        if 'ignore_multimedia' not in settings:
            self.settings['ignore_multimedia'] = True

        if 'max_content_size' not in settings:
            self.settings['max_content_size'] = 1000000

        if 'nameservers' not in settings:
            self.settings['nameservers'] = ['8.8.8.8', '8.8.4.4']

        if 'dns_cache' not in settings:
            self.settings['dns_cache'] = {}

    async def init(self):
        await self.dns_cache_lookup.connect_db()

    async def close(self):
        await self.dns_cache_lookup.close()

    def _remove_port(self, host):
        if ":" in host:
            return host.split(":")[0]

        return host

    def _is_multi_media(self, content_type: str) -> bool:
        """Check if content is a multi media"""
        for bad_content_type in self.multimedia_content_types:
            if bad_content_type in content_type:
                return True
            
        return False

    async def _process_response(
        self,
        url: str,
        response: ClientResponse,
    ) -> typing.Optional[tuple]:
        """
        Analyzes a responses content type and status code and figures out if it should ignore it
        """
        logging.debug("Got status %s for url %s", response.status, url)


        if self.settings["status"] != -1 and response.status != self.settings["status"]:
            return None

        headers = dict(response.headers)
        logging.debug("Getting the html")
        content_bytes: bytes = await response.read()
        content: str = content_bytes.decode("utf-8", "ignore")
        logging.debug("Done getting the html")

        # Ignore media content
        if self.settings["ignore_multimedia"] is True:
            content_type = response.headers.get("content-type", "")

            if self._is_multi_media(content_type):
                logging.info(
                    "Not gonna return the response from %s because it contains bad content type",
                    url,
                )
                return None
        # Huge content types are problematic, it consumes memory,
        # especially if we're trying to guess its content and put it in parsers
        # This is why we're gonna return None if it exceeds a certain configurable amount
        if len(content) >= self.settings['max_content_size']:
            logging.debug(
                "Skipping analyzing %s because it exceeds max content size of %s",
                url,
                self.settings['max_content_size'],
            )
            return None

        return url, content, headers

    #@retry(attempts = 3)
    async def fetch(self, url):
        try:
            async with ClientSession(
                connector=aiohttp.TCPConnector(
                    ssl=False,
                    enable_cleanup_closed=True,
                    family=socket.AF_INET,
                    force_close=True,
                    use_dns_cache=False,
                    resolver=AioHttpDnsResolver(self.settings['nameservers'])
                    
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

                        if urlparse(url).netloc.replace("www.", "").encode('idna').decode() != urlparse(redirect_url).netloc.replace("www.", ""):
                            logging.debug("The URL %s and URL %s is not the same domain, skipping..", url, redirect_url)
                            return None

                        return await self.fetch(
                            redirect_url
                        )

                    response_content = await self._process_response(
                        url, response
                    )

                    logging.debug("Done with GET request %s", url)

                    if response_content:
                        return {'url': response_content[0], 'content': response_content[1], 'headers': response_content[2]}

                    return None
        except Exception as err:
            logging.debug("Error on %s. Error: %s", url, err)
            #raise err

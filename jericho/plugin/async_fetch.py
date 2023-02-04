#!/bin/python3
import aiohttp
import socket
import logging
import typing
import aiodns
import asyncio
import random
from async_retrying import retry
from async_retrying import RetryError

from aiohttp.client_reqrep import ClientResponse
from aiohttp import ClientSession
from urllib.parse import urlparse
from jericho.repositories.dns_cache_lookup import DnsCacheLookup

class EmptyDNSResolve(Exception):
    pass

class HTTPError(Exception):
    pass

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

    async def _get_nameserver(self):
        """Use the asyncio lock to change the current nameserver index and return the nameserver"""
        async with self.lock:
            if len(self.settings['nameservers']) == 0:
                logging.critical("The nameserver list is empty")
                return ""

            nameserver = self.settings['nameservers'][random.randint(0, len(self.settings['nameservers']) - 1)]

            logging.debug("Called to get a nameserver: %s", nameserver)

            return nameserver


    async def _attempt_dns_lookup(self, domain: str):
        for attempt in range(0, 4):
            errno = 0
            try:
                nameserver = await self._get_nameserver()
                logging.debug(
                    "Sending a DNS request to domain %s with nameserver %s. Attempt: %s",
                    domain,
                    nameserver,
                    attempt,
                )
                resolver = aiodns.DNSResolver(
                    nameservers=[nameserver], loop=asyncio.get_event_loop()
                )
                async with self.lock:
                    self.dns_requests = self.dns_requests + 1
                get_ip_address = await resolver.query(domain, "A")
                async with self.lock:
                    self.dns_responses = self.dns_responses + 1

                if len(get_ip_address) == 0:
                    raise EmptyDNSResolve(Exception)

                ip_address = get_ip_address[0].host

                logging.debug(
                    "Resolved domain %s into IP %s with nameserver %s",
                    domain,
                    ip_address,
                    nameserver,
                )
                return ip_address
            except aiodns.error.DNSError as dnserr:
                errno = int(str(dnserr).split(",")[0].replace("(", ""))

                # 11 = "Could not contact DNS servers"
                # If this error happens we suspect we have a list with bad DNS servers
                # Could also be rate limiting

                if errno == 11:
                    logging.debug(
                        "The DNS server %s is unresponsive (Try %s)",
                        nameserver,
                        attempt
                    )

                    logging.debug("Done removing DNS server %s", nameserver)
            except ValueError as err:
                logging.exception(
                    "Could not parse domain %s with nameserver %s. Error: %s", domain, nameserver, err
                )
            except EmptyDNSResolve as err:
                logging.exception("Empty dns resolve. Domain: %s Error: %s", domain, err)
                return None
            except Exception as err:
                logging.exception(
                    "Got an error when parsing domain %s with nameserver %s: Error: %s",
                    domain,
                    nameserver,
                    err,
                )


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


    async def _transform_domain_url_to_ip_url(self, url):
        """Convert a domain url to an ip url, such a https://google.com/a to https://1.2.3.4/a"""
        logging.debug("Getting domain from url  %s", url)
        domain = urlparse(url).netloc

        # The domain could have a port, e.g test.com:8080
        domain = self._remove_port(domain)

        logging.debug("Got domain %s from url %s", domain, url)

        # If we get a potential relevant result we are going to send a page to a 404 page,
        # here we re-use the previous dns lookup
        if domain in self.settings['dns_cache']:
            logging.debug(
                "Using dns cache for domain %s with ip %s",
                domain,
                self.settings['dns_cache'][domain],
            )
            ip_address = self.settings['dns_cache'][domain]
            return url.replace(domain, ip_address), domain



        ip_from_database = await self.dns_cache_lookup.find_ip(domain)
        if ip_from_database:
            logging.debug(
                "Using dns cache for domain %s with ip %s",
                domain,
                ip_from_database,
            )
            return url.replace(domain, ip_from_database), domain


        ip_address = await self._attempt_dns_lookup(domain)
        if not ip_address:
            return None, None

        # Save the ip address in the cache
        await self.dns_cache_lookup.save(domain, ip_address)

        # Replace the domain in the url with the ip address
        return url.replace(domain, ip_address), domain


    @retry(attempts = 3)
    async def fetch(self, url):
        try:
            async with ClientSession(
                connector=aiohttp.TCPConnector(
                    ssl=False,
                    enable_cleanup_closed=True,
                    family=socket.AF_INET,
                    force_close=True,
                ),
                cookie_jar=aiohttp.DummyCookieJar(),
                timeout=aiohttp.ClientTimeout(total=10,sock_connect=10,sock_read=10)
            ) as session:
                transformed_url, domain = await self._transform_domain_url_to_ip_url(url)
                if not transformed_url:
                    return None

                headers = {
                    "User-Agent": self.settings['user_agent'],
                    "Host": domain,
                    "Connection": "close",
                }

                logging.debug("Sending a GET request to %s", transformed_url)
                async with session.get(
                    transformed_url,
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

                    response_content = await self._process_response(
                        url, response
                    )

                    logging.debug("Done with GET request %s", url)

                    if response_content:
                        return {'url': response_content[0], 'content': response_content[1], 'headers': response_content[2]}

                    return None
        except Exception as err:
            raise err

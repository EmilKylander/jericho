import asyncio
import logging
import typing
import aiodns
import json
import random
import socket
from aiohttp import ClientSession
import aiohttp.client_exceptions
from aiohttp.client_reqrep import ClientResponse
from urllib.parse import urlparse

from jericho.helpers import add_missing_schemes_to_domain, split_array_by
from jericho.plugin.cluster import Cluster
from jericho.enums.cluster_response_type import ClusterResponseType

class EmptyDNSResolve(Exception):
    pass


class AsyncHTTP:
    def __init__(
        self,
        nameservers: list,
        dns_cache: dict,
        max_requests: int,
        cluster: Cluster,
        rank: int,
    ):
        """Initialize default values"""
        self.multimedia_content_types: list = ["audio", "image", "video", "font"]
        self.max_content_length: int = 1000000  # 1Mb
        self.max_retries: int = 1
        self.responses: dict = {}
        self.requests: int = 0
        self.lock: asyncio.Lock = asyncio.Lock()
        self.nameservers: list = [
            nameserver for nameserver in nameservers if nameserver != ""
        ]
        self.dns_cache: dict = dns_cache
        self.max_requests: int = max_requests
        self.user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
        self.cluster: Cluster = cluster
        self.rank: int = rank
        self.domain_list_size: int = 0
        self.finished_requests: int = 0
        self.http_requests: int = 0
        self.dns_requests: int = 0
        self.dns_responses: int = 0
        self.timeouts: int = 0

    def _is_multi_media(self, content_type: str) -> bool:
        """Check if content is a multi media"""
        for bad_content_type in self.multimedia_content_types:
            if bad_content_type in content_type:
                return True
        return False

    def _parse_settings(self, settings: dict) -> dict:
        """Parse the settings given to async_http"""
        if not settings.get("ignore_multimedia"):
            settings["ignore_multimedia"] = False

        if not settings.get("status"):
            settings["status"] = -1

        if not settings.get("max_content_size"):
            settings["max_content_size"] = self.max_content_length

        return settings

    async def _get_not_found_html(self, session: ClientSession, url: str, domain: str, redirected: bool = False):
        not_found_html_bytes = b""
        async with self.lock:
            self.http_requests = self.http_requests + 1

        if not redirected:
            headers = {
                "User-Agent": self.user_agent,
                "Host": domain,
                "Connection": "close",
            }
        else:
            headers = {
                "User-Agent": self.user_agent,
                "Connection": "close",
            }

        async with session.get(
            url,
            ssl=False,
            allow_redirects=False,
            timeout=10,
            headers=headers,
        ) as not_found_response:
            if str(not_found_response.status)[0] == "3":
                redirect_url = not_found_response.headers.get("Location")
                if redirect_url is None:
                    logging.error("A status %s gave no location header on domain %s", not_found_response.status, url)
                    return ""

                # Sometimes the Location is a relative path
                if redirect_url[0] == "/":
                    redirect_url = url + redirect_url

                return (await self._get_not_found_html(session, redirect_url, domain, True))

            not_found_html_bytes = await not_found_response.read()

        return not_found_html_bytes.decode("utf-8", "ignore")

    def _remove_port(self, host):
        if ":" in host:
            return host.split(":")[0]

        return host

    async def _process_response(
        self,
        url: str,
        settings: dict,
        response: ClientResponse,
        session: ClientSession,
        domain: str,
        original_url: str,
    ) -> typing.Optional[tuple]:
        """
        Analyzes a responses content type and status code and figures out if it should ignore it
        """
        logging.debug("Got status %s for url %s", response.status, url)

        if settings["status"] != -1 and response.status != settings["status"]:
            return None

        headers = dict(response.headers)

        logging.debug("Getting the html")
        content_bytes: bytes = await response.read()
        content: str = content_bytes.decode("utf-8", "ignore")
        logging.debug("Done getting the html")

        # Ignore media content
        if settings["ignore_multimedia"] is True:
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
        if len(content) >= self.max_content_length:
            logging.debug(
                "Skipping analyzing %s because it exceeds max content size of %s",
                original_url,
                self.max_content_length,
            )
            return None

        url_parts = urlparse(url)
        ip_address = self._remove_port(url_parts.netloc)

        transformed_url = f"{url_parts.scheme}://{ip_address}/not_found_page.html"

        logging.debug(
            "Sending a request to not-found page %s with domain %s from dns cache",
            transformed_url,
            domain,
        )

        not_found_html: str = await self._get_not_found_html(
            session, transformed_url, domain
        )

        return original_url, content, headers, not_found_html

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
                #
                if errno == 11:
                    logging.warning(
                        "The DNS server %s is unresponsive",
                        nameserver,
                    )

                    logging.debug("Done removing DNS server %s", nameserver)
            except ValueError as err:
                logging.exception(
                    "Could not parse domain %s with nameserver %s", domain, nameserver
                )
            except EmptyDNSResolve as err:
                return None
            except Exception as err:
                logging.exception(
                    "Got an error when parsing domain %s with nameserver %s: Error: %s",
                    domain,
                    nameserver,
                    err,
                )

    async def _fetch(
        self,
        url: str,
        settings: dict,
        session: ClientSession,
        original_url: str,
        domain: str,
        redirected: bool = False
    ) -> typing.Optional[tuple]:
        """Calls different http methods based on which method was passed to async_http"""

        if not redirected:
            async with self.lock:
                self.http_requests = self.http_requests + 1

            headers = {
                "Host": domain,
                "User-Agent": self.user_agent
            }
        else:
            headers = {
                "User-Agent": self.user_agent
            }

        async with session.get(
            url,
            ssl=False,
            allow_redirects=False,
            timeout=10,
            headers=headers,
        ) as response:
            if str(response.status)[0] == "3":
                redirect_url = response.headers.get("Location")
                logging.debug("Sending a request to redirect url %s", redirect_url)

                if redirect_url is None:
                    logging.error("A status %s gave no location header on domain %s", response.status, url)
                    return ()

                # Sometimes the Location is a relative path
                if redirect_url[0] == "/":
                    redirect_url = url + redirect_url

                return (await self._fetch(redirect_url, settings, session, original_url, domain, True))

            response_content = await self._process_response(
                url, settings, response, session, domain, original_url
            )
            if response_content:
                async with self.lock:
                    self.responses[original_url] = response_content
                    logging.debug("Got a response from %s", original_url)

    async def _transform_domain_url_to_ip_url(self, url):
        """Convert a domain url to an ip url, such a https://google.com/a to https://1.2.3.4/a"""
        logging.debug("Getting domain from url  %s", url)
        domain = urlparse(url).netloc

        # The domain could have a port, e.g test.com:8080
        domain = self._remove_port(domain)

        logging.debug("Got domain %s from url %s", domain, url)

        # If we get a potential relevant result we are going to send a page to a 404 page,
        # here we re-use the previous dns lookup
        if domain in self.dns_cache:
            logging.debug(
                "Using dns cache for domain %s with ip %s",
                domain,
                self.dns_cache[domain],
            )
            ip_address = self.dns_cache[domain]
            return url.replace(domain, ip_address), domain

        ip_address = await self._attempt_dns_lookup(domain)
        if not ip_address:
            return None, None

        # Save the ip address in the cache
        self.dns_cache[domain] = ip_address

        # Replace the domain in the url with the ip address
        return url.replace(domain, ip_address), domain

    async def _bound_fetch(self, url: str, settings: dict, session: ClientSession):
        """Sends the HTTP request, handle some different types of exceptions"""

        logging.debug("In bound fetch on %s", url)

        try:
            logging.debug(
                "Transforming url to use IP and domain in Host header for url %s", url
            )
            transformed_url, domain = await self._transform_domain_url_to_ip_url(url)

            if not transformed_url:
                return None

            logging.debug(
                "Sending a request to %s with host header %s", transformed_url, domain
            )

            if transformed_url:
                await self._fetch(transformed_url, settings, session, url, domain)
                logging.debug("Got a response from %s", url)
            logging.debug("Done with fetch on %s", url)
        except aiohttp.ClientConnectorError as err:
            logging.info("Got a client timeout from url %s, error: %s", url, err)

        except asyncio.TimeoutError as err:

            logging.info("Got a timeout from url %s, error: %s", url, err)
            async with self.lock:
                self.timeouts = self.timeouts + 1

        except aiohttp.ClientConnectorSSLError:
            logging.info("Got a SSL connection error on url %s", url)

        except aiohttp.ClientOSError as err:
            logging.info(
                "Got client OS error on %s - most likely client reset by peer: %s",
                url,
                err,
            )

        except aiohttp.ClientResponseError as err:
            # This is related to when the peer closes the connection, this is retryable
            # We mitigate this by setting HTTP header Connection: close
            # Source: https://github.com/aio-libs/aiohttp/issues/850#issuecomment-471663047
            logging.warning(
                "Got a client response error on url %s - Error: %s", url, err
            )

        except aiohttp.ServerDisconnectedError:
            logging.info("The server disconnected us when connecting to %s", url)

        except aiohttp.ClientPayloadError:
            logging.info(
                "Got the error that the response payload is not completed on url %s",
                url,
            )

        except Exception as err:
            logging.exception("Got error %s when connecting to %s", err, url)

    async def _handle_responses(self) -> typing.AsyncGenerator[None, tuple]:
        """Use the asyncio lock to get the response list"""
        async with self.lock:
            for url in list(self.responses):
                if self.responses[url][0] is not None:
                    yield self.responses[url]
                del self.responses[url]

    async def _get_nameserver(self):
        """Use the asyncio lock to change the current nameserver index and return the nameserver"""
        async with self.lock:
            if len(self.nameservers) == 0:
                logging.critical("The nameserver list is empty")
                return ""

            nameserver = self.nameservers[random.randint(0, len(self.nameservers)-1)]

            logging.debug("Called to get a nameserver: %s", nameserver)

            return nameserver

    async def _start_statistics(self):
        logging.debug("Statistics coroutine started")

        while True:
            async with self.lock:
                http_requests = self.http_requests
                finished_requests = self.finished_requests
                dns_requests = self.dns_requests
                dns_responses = self.dns_responses
                timeouts = self.timeouts

            req_per_sec = int(http_requests / 60)
            if self.rank > 0:
                self.cluster.send_job_message(
                    json.dumps(
                        {
                            "type": ClusterResponseType.STATISTICS.value,
                            "rps": int(http_requests / 60),
                            "domain_list_size": self.domain_list_size,
                            "rank": self.rank,
                            "finished_requests": finished_requests,
                        }
                    )
                )
            else:
                logging.info(
                    "Statistics: Request per second: %s - Domain list size: %s - HTTP Requests: %s - DNS Requests: %s - DNS Responses: %s - DNS server list: %s - DNS Cache: %s - Timeouts: %s",
                    req_per_sec,
                    self.domain_list_size,
                    finished_requests,
                    dns_requests,
                    dns_responses,
                    len(self.nameservers),
                    len(self.dns_cache),
                    timeouts,
                )

            async with self.lock:
                self.http_requests = 0

            await asyncio.sleep(60)

    async def _bound_fetch_loop(self, domains: typing.List[str], settings: dict, session: ClientSession):
        for link in domains:
            link = add_missing_schemes_to_domain(link)
            try:
                await self._bound_fetch(link, settings, session)
            except:
                pass
            async with self.lock:
                self.finished_requests = self.finished_requests + 1


    async def _start_event_loop(
        self, session: ClientSession, links: typing.List[str], settings: dict
    ) -> typing.AsyncGenerator[None, typing.Tuple[str, str, dict, str]]:
        """Starts an async generator which starts async http requests and yields back results"""
        loop = asyncio.get_event_loop()

        loop.create_task(self._start_statistics())

        self.domain_list_size = len(links)

        domain_parts = split_array_by(links, self.max_requests)
        for domain_part in domain_parts:
            loop.create_task(self._bound_fetch_loop(domain_part, settings, session))

        while True:
            async for resp in self._handle_responses():
                yield resp
            async with self.lock:
                if self.finished_requests == self.domain_list_size:
                    break
                else:
                    logging.debug("Finished requests: %s - Total %s", self.finished_requests, self.domain_list_size)
            await asyncio.sleep(1)

    async def get(
        self, links: typing.List[str], settings: dict
    ) -> typing.AsyncGenerator[None, typing.Tuple[str, str, dict, str]]:
        """Sends a GET HTTP request"""

        settings = self._parse_settings(settings)

        # If we have a domain list with 100 domains as input then those 100 domains
        # can be saved in a way that related domains are near eachother.
        # Example: First 30 domains are taobao.com subdomains, all of them resolve to 1.2.3.4
        # This causes 30 GET requests to the same server in a short time, which could cause a DoS
        # or the server closing the connection. To mitigate this we shuffle the domain list before
        # continuing.
        random.shuffle(links)

        session = ClientSession(
            connector=aiohttp.TCPConnector(
                ssl=False,
                enable_cleanup_closed=True,
                family=socket.AF_INET,
                force_close=True,
                limit=self.max_requests,
            ),
            cookie_jar=aiohttp.DummyCookieJar(),
        )
        async for result in self._start_event_loop(session, links, settings):
            logging.debug("Saving domain %s", result[0])
            yield result

        await session.close()

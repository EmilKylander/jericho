import asyncio
import logging
import typing
from aiohttp import ClientSession
import aiohttp.client_exceptions
from aiohttp.client_reqrep import ClientResponse
from async_timeout import timeout
from jericho.enums.http_request_methods import HttpRequestMethods


class InvalidSetOfDomains(Exception):
    pass


class AsyncHTTP:
    def __init__(self):
        """Initialize default values"""
        self.multimedia_content_types = ["audio", "image", "video", "font"]
        self.max_content_length = 1000000  # 1Mb
        self.max_retries = 1
        self.sema = asyncio.Semaphore(1)

    def _is_multi_media(self, content_type: str) -> bool:
        """Check if content is a multi media"""
        for bad_content_type in self.multimedia_content_types:
            if bad_content_type in content_type:
                return True
        return False

    async def process_response(
        self, url: str, settings: dict, response: ClientResponse
    ) -> tuple:
        """
        Analyzes a responses content type and status code and figures out if it should ignore it
        """
        logging.debug("Got status %s for url %s", response.status, url)

        headers = response.headers

        content = ""
        if settings.get("method") != HttpRequestMethods.HEAD.value:
            content = await response.read()
            content = content.decode("utf-8", "ignore")

        # Ignore media content
        if settings["ignore_multimedia"] is True:
            content_type = response.headers.get("content-type", "")

            if self._is_multi_media(content_type):
                logging.info(
                    "Not gonna return the response from %s because it contains bad content type",
                    url,
                )
                return None, None, None

        # Huge content types are problematic, it consumes memory - especially if we're trying to guess its content and put it in parsers
        # This is why we're gonna return None if it exceeds a certain configurable amount
        content_length = len(content)
        if content_length >= self.max_content_length:
            return None, None, None

        if settings["status"] != -1:
            if response.status == settings["status"]:
                logging.debug("Got status %s for url %s", response.status, url)
                return url, content, headers
        else:
            return url, content, headers

        return None, None, None

    async def fetch(self, url: str, settings: dict, session: ClientSession) -> tuple:
        """Calls different http methods based on which method was passed to async_http"""

        if url is None:
            logging.critical(
                "We got a None entry in fetch(), sanitize the list before supplying."
            )
            return None, None, None

        logging.debug("Sending a request to %s with method %s", url, settings["method"])
        if settings["method"] == HttpRequestMethods.HEAD.value:
            async with session.head(
                url,
                ssl=False,
                allow_redirects=True,
                timeout=settings["timeout"],
                headers=settings["headers"],
            ) as response:
                return await self.process_response(url, settings, response)

        elif settings["method"] == HttpRequestMethods.GET.value:
            async with session.get(
                url,
                ssl=False,
                allow_redirects=True,
                timeout=settings["timeout"],
                headers=settings.get("headers", {}),
            ) as response:
                return await self.process_response(url, settings, response)

        return None, None, None

    async def bound_fetch(
        self, url: str, settings: dict, session: ClientSession
    ) -> tuple:
        """Sends the HTTP request, handle some different types of exceptions"""
        try:
            return await self.fetch(url, settings, session)
        except aiohttp.ClientConnectorError:
            logging.debug("Got a client timeout from url %s", url)
        except asyncio.TimeoutError:
            logging.debug("Got a timeout from url %s", url)
        except aiohttp.ClientConnectorSSLError:
            logging.debug("Got a SSL connection error on url %s", url)
        except aiohttp.ClientOSError as err:
            logging.debug(
                "Got client OS error on %s - most likely client reset by peer: %s",
                url,
                err,
            )
        except aiohttp.ClientResponseError as err:
            logging.warning(
                "Got a client response error on url %s - Eror: %s", url, err
            )
        except aiohttp.ServerDisconnectedError:
            logging.debug("The server disconnected us when connecting to %s", url)
        except aiohttp.ClientPayloadError:
            logging.debug(
                "Got the error that the response payload is not completed on url %s",
                url,
            )
        except Exception as err:
            logging.error("Got error for url %s - Error: %s", url, err)

        return None, None, None

    def _parse_settings(self, settings: dict) -> dict:
        """Parse the settings given to async_http"""
        if not settings.get("ignore_multimedia"):
            settings["ignore_multimedia"] = False

        if not settings.get("status"):
            settings["status"] = -1

        if not settings.get("max_content_size"):
            settings["max_content_size"] = self.max_content_length

        return settings

    def _validate_links(self, links: list) -> bool:
        for link in links:
            if not isinstance(link, str):
                return False

        return True

    async def head(self, links: typing.List[str], settings: dict) -> list:
        """Sends a HEAD HTTP request"""
        if not self._validate_links(links):
            logging.critical("We received an incorrect list of links")
            raise InvalidSetOfDomains

        tasks = []
        settings = self._parse_settings(settings)
        settings["method"] = HttpRequestMethods.HEAD.value
        async with self.sema, ClientSession(
            connector=aiohttp.TCPConnector(
                ssl=False, enable_cleanup_closed=True, force_close=True
            ),
            cookie_jar=aiohttp.DummyCookieJar(),
        ) as session:
            for link in links:
                tasks.append(self.bound_fetch(link, settings, session))

            responses = asyncio.gather(*tasks)
            results = await responses
            return [result for result in results if result[0] is not None]

    async def get(self, links: typing.List[str], settings: dict) -> list:
        """Sends a GET HTTP request"""
        if not self._validate_links(links):
            logging.critical("We received an incorrect list of links")
            raise InvalidSetOfDomains

        tasks = []
        settings = self._parse_settings(settings)
        settings["method"] = HttpRequestMethods.GET.value
        async with self.sema, ClientSession(
            connector=aiohttp.TCPConnector(
                ssl=False, enable_cleanup_closed=True, force_close=True
            ),
            cookie_jar=aiohttp.DummyCookieJar(),
        ) as session:
            for link in links:
                tasks.append(self.bound_fetch(link, settings, session))

            responses = asyncio.gather(*tasks)
            results = await responses
            return [result for result in results if result[0] is not None]

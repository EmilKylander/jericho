#!/bin/python3
import queue
import asyncio
import typing
import concurrent.futures
from jericho.enums.http_codes import HttpStatusCode
from jericho.enums.thread_response import ThreadResponse
from jericho.plugin.async_http import AsyncHTTP
from jericho.helpers import (
    split_array_by,
    add_missing_schemes_to_domain_list,
    chunks,
    merge_array_to_iterator,
)


class InvalidHTTPRequestMethod(Exception):
    pass


class ThreadedAsyncHTTP:
    def __init__(
        self,
        async_http: AsyncHTTP,
        num_threads: int,
        configuration: dict,
        finish_queue: queue.Queue,
        should_scan_both_schemes: bool,
        ignore_endpoints: bool,
        endpoints: typing.List[str],
    ):
        self.configuration: dict = configuration
        self.async_http: AsyncHTTP = async_http
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
        self.num_threads = num_threads
        self.should_scan_both_schemes = should_scan_both_schemes
        self.ignore_endpoints = ignore_endpoints
        self.endpoints = endpoints

        self.finish_queue: queue.Queue = finish_queue

    async def _send(
        self, send_domains: typing.List[str], batch_size: int
    ) -> typing.Any:
        """
        A method which is ran through a thread, purpose is to
        launch async method to send HTTP requests
        """
        # Here we get the full domain list / amount of threads
        # If we have a list of 100,000 domains and 5 threads
        # we don't want to send 20,000 requests at the same time per thread
        # so we split it again
        if self.ignore_endpoints:
            url_chunks = chunks(send_domains, batch_size)
        else:
            url_chunks = merge_array_to_iterator(
                self.endpoints, send_domains, domains_batch_size=batch_size
            )

        for url_chunk in url_chunks:
            url_chunk = add_missing_schemes_to_domain_list(
                url_chunk, self.should_scan_both_schemes
            )

            res = await self.async_http.get(
                url_chunk,
                settings={
                    "status": HttpStatusCode.OK.value,
                    "timeout": self.configuration.get("max_get_timeout"),
                    "ignore_multimedia": self.configuration.get("ignore_multimedia"),
                    "headers": {"User-Agent": self.user_agent},
                }
            )

            for url, html, headers in res:
                self.finish_queue.put(
                    {
                        "status": ThreadResponse.RESULT.value,
                        "url": url,
                        "html": html,
                        "headers": dict(headers),
                    }
                )

    def _async_send(
        self, send_domains: typing.List[str], batch_size: int
    ) -> typing.Any:
        """Start the coroutine from a non-async method"""
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._send(send_domains, batch_size))

    async def _run(self, domains: typing.List[str], batch_size: int):
        """Supply domains list to all the threads"""
        domain_chunks = split_array_by(domains, self.num_threads)
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.num_threads
        ) as pool:
            loop = asyncio.get_running_loop()
            futures = [
                loop.run_in_executor(pool, self._async_send, domain_chunk, batch_size)
                for domain_chunk in domain_chunks
            ]
            await asyncio.gather(*futures, return_exceptions=True)

        return True

    def start_bulk(self, domains: typing.List[str], batch_size: int) -> typing.Any:
        """Supply domains list to all the threads"""
        asyncio.run(self._run(domains, batch_size))
        self.finish_queue.put({"status": ThreadResponse.DONE.value})

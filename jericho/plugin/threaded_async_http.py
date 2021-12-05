#!/bin/python3
import queue
import threading
import asyncio
import logging
import typing
from jericho.enums.http_codes import HttpStatusCode
from jericho.plugin.async_http import AsyncHTTP
from jericho.enums.http_request_methods import HttpRequestMethods
from jericho.helpers import split_array_by


class InvalidHTTPRequestMethod(Exception):
    pass


class ThreadedAsyncHTTP:
    def __init__(self, async_http: AsyncHTTP, num_threads: int, configuration: dict):
        self.queues: typing.List[queue.Queue] = []
        self.threads: typing.List[threading.Thread] = []
        self.configuration: dict = configuration
        self.parts: typing.List[typing.List[str]] = []
        self.async_http: AsyncHTTP = async_http
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"

        self.finish_queue: queue.Queue = queue.Queue()

        for worker_id in range(num_threads):
            thread_queue: queue.Queue = queue.Queue()
            self.queues.append(thread_queue)
            thread = threading.Thread(
                target=self._send,
                name=f"worker-{worker_id}",
                args=(thread_queue, self.finish_queue),
            )
            self.threads.append(thread)

        [t.start() for t in self.threads]

    async def _send_head_request(
        self, domains: typing.List[str]
    ) -> typing.List[typing.Tuple]:
        """Send a HEAD requests to a list of domains"""
        return await self.async_http.head(
            domains,
            settings={
                "status": HttpStatusCode.OK.value,
                "timeout": self.configuration.get("max_head_timeout"),
                "ignore_multimedia": self.configuration.get("ignore_multimedia"),
                "headers": {"User-Agent": self.user_agent},
            },
        )

    async def _send_get_request(
        self, domains: typing.List[str]
    ) -> typing.List[typing.Tuple]:
        """Send a GET requests to a list of domains"""
        return await self.async_http.get(
            domains,
            settings={
                "status": HttpStatusCode.OK.value,
                "timeout": self.configuration.get("max_get_timeout"),
                "ignore_multimedia": self.configuration.get("ignore_multimedia"),
                "headers": {"User-Agent": self.user_agent},
            },
        )

    def _send(self, single_queue: queue.Queue, finish_queue: queue.Queue) -> typing.Any:
        """
        A method which is ran through a thread, purpose is to
        launch async method to send HTTP requests
        """
        while True:
            payload = single_queue.get()
            if isinstance(payload, str):
                if payload == f"CLOSE-{threading.current_thread().name}":
                    logging.debug("Got a close signal, exiting thread..")
                    return True
            else:
                method, domains = payload
                if method == HttpRequestMethods.HEAD:
                    res = asyncio.run(self._send_head_request(domains))

                elif method == HttpRequestMethods.GET:
                    res = asyncio.run(self._send_get_request(domains))
                else:
                    self.close()
                    raise InvalidHTTPRequestMethod

                finish_queue.put(res)

    def get_response(self) -> typing.List[typing.Tuple]:
        """Loop through all of the work queues and combine the data"""

        output: typing.List[typing.Tuple] = []
        for _ in self.parts:
            res = self.finish_queue.get()
            output = output + res
        return output

    def start_bulk(
        self, domains: typing.List[str], method: HttpRequestMethods
    ) -> typing.Any:
        """Supply domains list to all the threads"""

        self.parts = split_array_by(domains, len(self.threads))

        for key, single_queue in enumerate(self.queues):
            if key < len(self.parts):  # The data might not be enough for 10 threads
                single_queue.put((method, self.parts[key]))

    def close(self) -> typing.Any:
        """Send a kill message to all worker threads and join the threads"""

        for key, single_queue in enumerate(self.queues):
            single_queue.put(f"CLOSE-worker-{key}")

        logging.debug("Joining threads..")
        [t.join() for t in self.threads]

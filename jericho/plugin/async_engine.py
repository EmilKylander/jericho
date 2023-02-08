#!/bin/python3
import asyncio
import aiohttp
import socket
import logging
import typing
import aiodns
import random
import sys
from enum import Enum
from aiohttp import ClientSession
from aiohttp.client_reqrep import ClientResponse
from urllib.parse import urlparse
from jericho.helpers import merge_domains_with_endpoints
from jericho.plugin.async_fetch import AsyncFetch

class WorkerStatus(Enum):
    WORKING  = 'working'
    IDLE     = 'idle'

class WorkerMessage(Enum):
    DIE  = 'DIE'
    DEAD = 'DEAD'

class AsyncEngine():
    def __init__(self,
        nameservers: list,
        settings: dict
        ):
        self.workers = 100
        self.response_queue: asyncio.Queue = asyncio.Queue()

        self.max_content_length: int = 1000000  # 1Mb
        self.max_retries: int = 1
        self.responses: dict = {}
        self.requests: int = 0
        self.nameservers: list = [
            nameserver for nameserver in nameservers if nameserver != ""
        ]
        self.user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
        self.domain_list_size: int = 0
        self.finished_requests: int = 0
        self.http_requests: int = 0
        self.dns_requests: int = 0
        self.dns_responses: int = 0
        self.timeouts: int = 0
        self.workers_status: dict = {}
        self.settings = self._parse_settings(settings)
        self.async_fetch = AsyncFetch(self.settings)
        self.lock: asyncio.Lock = asyncio.Lock()
        self.queues = []
        self.finish_queues = []
        self.finished_requests = 0


    def _parse_settings(self, settings: dict) -> dict:
        """Parse the settings given to async_http"""
        if not settings.get("ignore_multimedia"):
            settings["ignore_multimedia"] = False

        if not settings.get("status"):
            settings["status"] = -1

        if not settings.get("max_content_size"):
            settings["max_content_size"] = self.max_content_length

        if not settings.get("nameservers"):
            settings["nameservers"] = self.nameservers

        return settings

    async def run(self, links: typing.List[str], endpoints: list = None):
        loop = asyncio.get_running_loop()

        await self.async_fetch.init()

        asd = []
        for workerID in range(0, self.workers-1):
            q: asyncio.Queue = asyncio.Queue()
            finish_queue: asyncio.Queue = asyncio.Queue()

            logging.info("Saving Starting worker %s", workerID)
            asd.append(loop.create_task(self.worker(q, finish_queue, workerID)))
            self.workers_status[workerID] = WorkerStatus.IDLE
            self.queues.append(q)
            self.finish_queues.append(finish_queue)

        if endpoints:
            links = merge_domains_with_endpoints(endpoints, links)

        while True:
            async with self.lock:
                logging.info("Finished requests: %s", self.finished_requests)
            active_workers = 0
            for worker_id in range(0, self.workers-1):
                if self.workers_status[worker_id] == WorkerStatus.WORKING:
                    active_workers = active_workers + 1

            if len(links) == 0 and active_workers == 0 and self.response_queue.qsize() == 0:
                for worker_id in range(0, self.workers-1):
                    await self.queues[worker_id].put(WorkerMessage.DIE)

                for worker_id in range(0, self.workers-1):
                    await self.finish_queues[worker_id].get()

                await self.async_fetch.close()
                break

            for workerID in range(0, self.workers-1):
                batch:list = []

                if self.queues[workerID].qsize() > 0:
                    continue

                for _ in range(0,2):
                    if len(links) == 0:
                        continue

                    batch.append(links.pop())

                if len(batch) > 0:
                    logging.debug("Queue Sending batch with %s of size", len(batch))
                    await self.queues[workerID].put(batch)

            if self.response_queue.qsize() > 0:
                for _ in range(0, self.response_queue.qsize()):
                    if self.response_queue.qsize() != 0:
                        job_response = await self.response_queue.get()

                        if endpoints:
                            response = job_response.get("result")
                            pattern = job_response.get("pattern")

                            if response:
                                yield response['url'], response['content'], response['headers'], pattern
                        else:
                            if job_response:
                                yield job_response['url'], job_response['content'], job_response['headers']

            await asyncio.sleep(0.1)

    async def worker(self, q, finish_queue,  workerID):
        while True:
            urls = await q.get()

            if urls == WorkerMessage.DIE:
                await finish_queue.put(WorkerMessage.DEAD)
                return False

            for url in urls:
                async with self.lock:
                    self.workers_status[workerID] = WorkerStatus.WORKING
                try:
                    fetch_result = await self.async_fetch.fetch(url.get("endpoint"))

                    if not fetch_result:
                        continue
                
                    # This is for checking if the final redirected url contains the desired endpoint that we look for.
                    # E.g /security.txt exists in test.com/security.txt. But /security.txt does not exist in test.com/?redirect=security.txt
                    if url.get("raw_endpoint") not in fetch_result.get("url"):
                        logging.debug("Endpoint %s does not exist in %s", url.get("raw_endpoint"), fetch_result.get("endpoint"))

                    await self.response_queue.put({"result": fetch_result, "pattern": url.get("pattern")})

                except Exception as e:
                    logging.error("Fetch caused an error: %s", e)
                self.workers_status[workerID] = WorkerStatus.IDLE

            async with self.lock:
                self.finished_requests = self.finished_requests + len(urls)
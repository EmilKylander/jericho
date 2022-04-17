#!/bin/python3
import typing
import logging
import asyncio
import os
import json
import uuid
import zmq
import threading
import queue
import base64
from jericho.helpers import split_array_by
from jericho.enums.cluster_response_type import ClusterResponseType
from jericho.repositories.converter_lookup import ConverterLookup


class Cluster:
    def __init__(self, servers):
        self.servers = servers
        self.socket = None
        self.job_socket = None
        self.topic = "jericho_event"
        self.finished = 0
        self.status = ""
        self.rank = 1

    def start_zmq_server(self):
        logging.debug("Starting result server")
        context = zmq.Context()
        self.socket = context.socket(zmq.PUB)
        self.socket.bind("tcp://*:1337")

    def start_zmq_subscribe_server(self):
        logging.debug("Starting subscribe server")
        context = zmq.Context()
        self.job_socket = context.socket(zmq.PULL)
        self.job_socket.bind("tcp://*:1338")

    def send_zmq_message(self, message):
        logging.info("Sending message %s", message)
        self.socket.send_string(f"{self.topic} {message}")

    def get_message_from_replica(self, server, q):
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect(f"tcp://{server}:1337")
        socket.setsockopt_string(zmq.SUBSCRIBE, self.topic)

        # We should get statistics statuses every minute, if a recv has not gotten any responses in two minutes then something is wrong
        socket.RCVTIMEO = 120000

        while True:
            try:
                messagedata = (
                    socket.recv().decode("utf-8", "ignore").replace(self.topic, "")
                ).strip()
            except:
                logging.warning(
                    "Got a timeout on server %s, closing the socket and re-connecting..",
                    server,
                )
                socket.close()
                self.get_message_from_replica(server, q)

            logging.debug("Received %s", messagedata)
            if messagedata == ClusterResponseType.FINISHED.value:
                logging.info("Got the finish signal")
                q.put(ClusterResponseType.FINISHED.value)
                return False

            q.put(messagedata)

    def receive_zmq_message(self):
        q = queue.Queue()

        for server in self.servers:
            threading.Thread(
                target=self.get_message_from_replica,
                args=(
                    server,
                    q,
                ),
            ).start()

        while True:
            messagedata = q.get()

            logging.debug("Received %s", messagedata)
            if messagedata == ClusterResponseType.FINISHED.value:
                logging.info("Got the finish signal")
                self.finished = self.finished + 1
                if self.finished == len(self.servers):
                    logging.info(
                        "Finish signals are the same amount of servers, finishing.."
                    )
                    break
                else:
                    continue

            messagedata = json.loads(messagedata)
            yield messagedata

    def listen_for_jobs(self, callback, converter_lookup: ConverterLookup):
        logging.debug("Listening for jobs")
        while True:
            messagedata = (
                self.job_socket.recv()
                .decode("utf-8", "ignore")
                .replace(self.topic, "")
                .strip()
            )
            logging.info("Received message %s", messagedata)

            if messagedata == "RESTART":
                if self.status == "":
                    continue

                logging.info("Got a reboot message!")
                os.system(
                    "echo 'pkill -9 python3 && nohup jericho --listen &' > /tmp/restart.sh && chmod +x /tmp/restart.sh && bash -c /tmp/restart.sh"
                )
                return False

            if messagedata == "UPGRADE":
                logging.info("Got a upgrade message!")
                os.system("jericho --upgrade")
                os.system(
                    "echo 'pkill -9 python3 && nohup jericho --listen &' > /tmp/restart.sh && chmod +x /tmp/restart.sh && bash -c /tmp/restart.sh"
                )
                return False

            if "SEND_FINISHED_JOBS" in messagedata:
                workload_uuid = messagedata.replace("SEND_FINISHED_JOBS ", "")
                finished_jobs = converter_lookup.get_workload(workload_uuid)

                for job in finished_jobs:
                    with open(job.get("location"), "rb") as f:
                        encoded_string = base64.b64encode(f.read()).decode()

                    self.send_zmq_message(
                        json.dumps(
                            {
                                "rank": self.rank,
                                "type": ClusterResponseType.WEBPAGE_CONTENT.value,
                                "workload_uuid": workload_uuid,
                                "uuid": job.get("location").replace("/tmp/", ""),
                                "zip": encoded_string,
                            }
                        )
                    )
                continue

            try:
                messagedata = json.loads(messagedata)
            except:
                logging.error("Could not parse message %s", messagedata)
                continue

            logging.info("Got job %s")
            self.status = f"Working on {messagedata.get('workload_uuid')}"
            self.rank = messagedata.get("rank")
            callback(
                messagedata.get("domains"),
                messagedata.get("workload_uuid"),
                messagedata.get("nameservers"),
                messagedata.get("configuration"),
                messagedata.get("rank"),
                messagedata.get("endpoints"),
                messagedata.get("dns_cache"),
                messagedata.get("converter"),
            )
            self.status = ""

    async def _restart_server(self, server):
        logging.info("Sending a restart message to %s", server)
        context = zmq.Context()
        socket = context.socket(zmq.PUSH)
        socket.connect(f"tcp://{server}:1338")
        socket.send_string(f"{self.topic} RESTART")
        socket.close()

    async def start_jericho_on_replica(
        self,
        workload_uuid: str,
        internal_data: dict,
        rank: int,
        server: str,
        dns_cache: typing.List,
        converter: typing.Optional[str],
    ):
        await self._restart_server(server)

        logging.debug("Sending message to Jericho on server %s", server)

        job = json.dumps(
            {
                "type": ClusterResponseType.JOB.value,
                "workload_uuid": workload_uuid,
                "domains": internal_data.get("domains"),
                "endpoints": internal_data.get("endpoints"),
                "configuration": internal_data.get("configuration"),
                "nameservers": internal_data.get("nameservers"),
                "rank": rank,
                "dns_cache": dns_cache,
                "converter": converter,
            }
        )

        context = zmq.Context()
        socket = context.socket(zmq.PUSH)
        socket.connect(f"tcp://{server}:1338")
        socket.send_string(f"{self.topic} {job}")
        socket.close()

    def request_finished_jobs(self, workload_uuid: uuid.uuid4):
        for server in self.servers:
            context = zmq.Context()
            socket = context.socket(zmq.PUSH)
            socket.connect(f"tcp://{server}:1338")
            socket.send_string(f"{self.topic} SEND_FINISHED_JOBS {workload_uuid}")
            socket.close()

    async def scatter(
        self,
        workload_uuid: uuid.uuid4,
        configuration: dict,
        endpoints: typing.List[str],
        domains_loaded: typing.List[str],
        nameservers: typing.List[str],
        dns_cache: typing.List,
        converter: typing.Optional[str],
    ):
        splitted_list = split_array_by(domains_loaded, len(self.servers))
        logging.info(
            "Split the domain list with %s servers into %s parts",
            len(self.servers),
            len(splitted_list),
        )
        rank = 1  # A replica always start with the rank 1 because rank 0 is main
        index = 0
        for split_list in splitted_list:
            internal_data = {
                "domains": split_list,
                "endpoints": endpoints,
                "configuration": configuration,
                "nameservers": nameservers,
                "converter": converter,
            }

            asyncio.ensure_future(
                self.start_jericho_on_replica(
                    workload_uuid,
                    internal_data,
                    rank,
                    self.servers[index],
                    dns_cache,
                    converter,
                )
            )
            rank = rank + 1
            index = index + 1

    def _send_upgrade_message(self, server):
        logging.info("Sending a upgrade message to %s", server)
        context = zmq.Context()
        socket = context.socket(zmq.PUSH)
        socket.connect(f"tcp://{server}:1338")
        socket.send_string(f"{self.topic} UPGRADE")
        socket.close()

    def upgrade_servers(self, servers):
        """Send a upgrade message to all servers"""
        for server in servers:
            self._send_upgrade_message(server)

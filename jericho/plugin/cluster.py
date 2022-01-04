#!/bin/python3
import typing
import logging
import asyncio
import json
import uuid
import zmq
from jericho.helpers import split_array_by
from jericho.enums.cluster_response_type import ClusterResponseType


class Cluster:
    def __init__(self, servers):
        self.servers = servers
        self.socket = None
        self.job_socket = None
        self.topic = "jericho_event"
        self.finished = 0

    def start_zmq_server(self):
        logging.debug("Starting result server")
        context = zmq.Context()
        self.socket = context.socket(zmq.PUB)
        self.socket.bind("tcp://*:1337")

    def start_zmq_subscribe_server(self):
        logging.debug("Starting subscribe server")
        context = zmq.Context()
        self.job_socket = context.socket(zmq.REP)
        self.job_socket.bind("tcp://*:1338")

    def send_zmq_message(self, message):
        logging.info("Sending message %s", message)
        self.socket.send_string(f"{self.topic} {message}")

    def receive_zmq_message(self):
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        for server in self.servers:
            socket.connect(f"tcp://{server}:1337")
            socket.setsockopt_string(zmq.SUBSCRIBE, self.topic)

        while True:
            messagedata = (
                socket.recv().decode("utf-8", "ignore").replace(self.topic, "")
            ).strip()
            logging.debug("Received %s", messagedata)
            if messagedata == ClusterResponseType.FINISHED.value:
                logging.info("Got the finish signal")
                self.finished = self.finished + 1
                if self.finished == len(self.servers):
                    logging.info(
                        "Finish signals are the same amount of servers, finishing.."
                    )
                    socket.close()
                    break
                else:
                    continue

            messagedata = json.loads(messagedata)
            yield messagedata

    def listen_for_jobs(self, callback):
        logging.debug("Listening for jobs")
        while True:
            messagedata = (
                self.job_socket.recv().decode("utf-8", "ignore").replace(self.topic, "")
            )
            messagedata = json.loads(messagedata)
            logging.info("Got job %s", messagedata)
            self.job_socket.send_string("ok")
            callback(
                messagedata.get("domains"),
                messagedata.get("workload_uuid"),
                messagedata.get("nameservers"),
                messagedata.get("configuration"),
                messagedata.get("rank"),
                messagedata.get("endpoints"),
                messagedata.get("dns_cache"),
                messagedata.get("converter")
            )

    async def start_jericho_on_replica(
        self,
        workload_uuid: str,
        internal_data: dict,
        rank: int,
        server: str,
        dns_cache: typing.List,
        converter: typing.Optional[str]
    ):
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
                "converter": converter
            }
        )

        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(f"tcp://{server}:1338")
        socket.send_string(f"{self.topic} {job}")
        socket.close()

    async def scatter(
        self,
        workload_uuid: uuid.uuid4,
        configuration: dict,
        endpoints: typing.List[str],
        domains_loaded: typing.List[str],
        nameservers: typing.List[str],
        dns_cache: typing.List,
        converter: typing.Optional[str]
    ):
        splitted_list = split_array_by(domains_loaded, len(self.servers))
        logging.info(
            "Split the domain list with %s servers into %s parts",
            len(self.servers),
            len(splitted_list),
        )
        rank = 0
        index = 0
        for split_list in splitted_list:
            internal_data = {
                "domains": split_list,
                "endpoints": endpoints,
                "configuration": configuration,
                "nameservers": nameservers,
                "converter": converter
            }

            asyncio.ensure_future(
                self.start_jericho_on_replica(
                    workload_uuid, internal_data, rank, self.servers[index], dns_cache, converter
                )
            )
            rank = rank + 1
            index = index + 1

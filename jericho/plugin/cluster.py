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
from multiprocessing import Process
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
        self.job_socket = context.socket(zmq.PULL)
        self.job_socket.bind("tcp://*:1338")

    def send_zmq_message(self, message):
        logging.info("Sending message %s", message)
        self.socket.send_string(f"{self.topic} {message}")

    def get_message_from_replica(self, server, q):
        """The replicas send back messages to main. E.g FINISHED and RESULT"""
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

    def listen_for_jobs(self, callback, result_lookup):
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

            if messagedata == "SEND_FINISHED_JOBS":
                workload_uuid = messagedata.replace("SEND_FINISHED_JOBS ", "")
                logging.info("Got a request to send back results on %s", workload_uuid)

                
                self.send_zmq_message(
                    json.dumps(
                        {
                            "type": ClusterResponseType.RESULT.value,
                            "workload_uuid": workload_uuid,
                            "result": result_lookup.get(workload_uuid)
                        }
                    )
                )

            try:
                messagedata = json.loads(messagedata)
            except:
                logging.error("Could not parse message %s", messagedata)
                continue

            logging.info("Got job %s")

            proc = Process(target=callback(
                messagedata.get("domains"),
                messagedata.get("workload_uuid"),
                messagedata.get("nameservers"),
                messagedata.get("configuration"),
                messagedata.get("endpoints"),
                messagedata.get("dns_cache")
            ))
            proc.start()
            
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
        server: str,
        dns_cache: typing.List
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
                "dns_cache": dns_cache,
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
        dns_cache: typing.List
    ):
        splitted_list = split_array_by(domains_loaded, len(self.servers))
        logging.info(
            "Split the domain list with %s servers into %s parts",
            len(self.servers),
            len(splitted_list),
        )
        index = 0
        for split_list in splitted_list:
            internal_data = {
                "domains": split_list,
                "endpoints": endpoints,
                "configuration": configuration,
                "nameservers": nameservers
            }

            asyncio.ensure_future(
                self.start_jericho_on_replica(
                    workload_uuid,
                    internal_data,
                    self.servers[index],
                    dns_cache
                )
            )
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

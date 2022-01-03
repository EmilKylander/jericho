#!/bin/python3
import json
import uuid
import logging
import sys
from aiohttp import ClientSession


CONTENT_TYPE_APPLICATION_JSON = "application/json"
LINODE_INSTANCES_API = "https://api.linode.com/v4/linode/instances"


class Linode:
    def __init__(self, configuration):
        self.configuration = configuration
        self.prefix = "jericho"
        self.instances = []

    async def _analyze_for_errors(self, resp: dict) -> bool:
        """A response at any time can return an error because of an expired token, this private method handles such responses"""
        if "errors" not in resp:
            return False

        if resp["errors"][0]["reason"] == "Invalid Token":
            logging.error(
                "Your Linode token has expired, please create a new one and save it in your configuration file"
            )
            return True

        return False

    async def create(self):
        """Creates an instance on Linode"""
        password = str(
            uuid.uuid4()
        )  # This is only used temporarily before we exchange the public keys
        name_uuid = str(uuid.uuid4())

        async with ClientSession() as session:
            async with session.post(
                LINODE_INSTANCES_API,
                ssl=False,
                allow_redirects=True,
                timeout=10,
                headers={
                    "Authorization": f"Bearer {self.configuration['token']}",
                    "Content-Type": CONTENT_TYPE_APPLICATION_JSON,
                },
                data=json.dumps(
                    {
                        "backups_enabled": False,
                        "swap_size": 512,
                        "image": "linode/debian11",
                        "root_pass": password,
                        "interfaces": [],
                        "booted": True,
                        "label": self.prefix + "_" + name_uuid,
                        "type": "g6-nanode-1",
                        "region": "us-east",
                        "group": "Linode-Group",
                    }
                ),
            ) as response:
                resp = await response.read()
                resp = json.loads(resp.decode("utf-8"))
                has_errors = await self._analyze_for_errors(resp)
                if has_errors:
                    sys.exit(0)

                self.instances.append(name_uuid)
                return {"password": password, "resp": resp}

    async def get_instances(self, show_all=False):
        """Get all of the VPSes that are related to Jericho"""
        found = []
        async with ClientSession() as session:
            async with session.get(
                LINODE_INSTANCES_API,
                ssl=False,
                allow_redirects=True,
                timeout=10,
                headers={
                    "Authorization": f"Bearer {self.configuration['token']}",
                    "Content-Type": CONTENT_TYPE_APPLICATION_JSON,
                },
            ) as response:
                resp = await response.read()
                obj = json.loads(resp.decode("utf-8"))
                has_errors = await self._analyze_for_errors(obj)
                if has_errors:
                    sys.exit(0)

                for row in obj["data"]:
                    if show_all and self.prefix in row["label"]:
                        found.append(row["label"])
                        continue

                    if (
                        self.prefix in row["label"]
                        and row["label"].replace("jericho_", "") in self.instances
                    ):
                        found.append(row["label"])
        return found

    async def get_ready(self):
        """Get all Jericho VPSes that are running"""
        found = 0
        async with ClientSession() as session:
            async with session.get(
                LINODE_INSTANCES_API,
                ssl=False,
                allow_redirects=True,
                timeout=10,
                headers={
                    "Authorization": f"Bearer {self.configuration['token']}",
                    "Content-Type": CONTENT_TYPE_APPLICATION_JSON,
                },
            ) as response:
                resp = await response.read()
                obj = json.loads(resp.decode("utf-8"))
                has_errors = await self._analyze_for_errors(obj)
                if has_errors:
                    sys.exit(0)

                for row in obj["data"]:
                    if (
                        self.prefix in row["label"]
                        and row["label"].replace("jericho_", "") in self.instances
                        and row["status"] == "running"
                    ):
                        found = found + 1
        return found

    async def delete_instances(self):
        """Delete are VPSes that are related to Jerico"""

        deleted = 0
        async with ClientSession() as session:
            async with session.get(
                LINODE_INSTANCES_API,
                ssl=False,
                allow_redirects=True,
                timeout=10,
                headers={
                    "Authorization": f"Bearer {self.configuration['token']}",
                    "Content-Type": CONTENT_TYPE_APPLICATION_JSON,
                },
            ) as response:
                resp = await response.read()
                obj = json.loads(resp.decode("utf-8"))
                has_errors = await self._analyze_for_errors(obj)
                if has_errors:
                    sys.exit(0)

                for row in obj["data"]:
                    if self.prefix in row["label"]:
                        instance_id = row["id"]
                        logging.info("Deleting %s", row["label"])

                        async with session.delete(
                            f"https://api.linode.com/v4/linode/instances/{instance_id}",
                            ssl=False,
                            allow_redirects=True,
                            timeout=10,
                            headers={
                                "Authorization": f"Bearer {self.configuration['token']}",
                                "Content-Type": CONTENT_TYPE_APPLICATION_JSON,
                            },
                        ) as response:
                            logging.info(
                                "Deleting instance %s (%s)", row["label"], instance_id
                            )

                            deleted = deleted + 1
        return deleted

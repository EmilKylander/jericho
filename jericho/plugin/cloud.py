#!/bin/python3
import logging
import asyncio
import asyncssh
import os
from jericho.helpers import get_username, chunks


class Cloud:
    def __init__(self, provider):
        self.provider = provider
        self.instances = []

    async def run_client(self, instance):
        """Run the installation synchronously"""
        try:
            logging.info("Logging into server %s", instance["resp"]["ipv4"][0])
        except:
            logging.error("Could not find IPV4 on instance: %s", instance)
            return False
        while True:
            username = "root"
            if "username" in instance["resp"]:
                username = instance["resp"]["username"]

            if username == "root":
                home_directory = "/root"
            else:
                home_directory = f"/home/{username}"
            try:
                async with asyncssh.connect(
                    instance["resp"]["ipv4"][0],
                    username=username,
                    password=instance.get("password"),
                    known_hosts=None,
                    public_key_auth=False
                ) as conn:
                    async with conn.start_sftp_client() as sftp:
                        await conn.run("mkdir /tmp/jericho")
                        await sftp.put(
                            f"/home/{get_username()}/.ssh/jericho_key.pub",
                            "/tmp/jericho/jericho_key",
                        )
                        await conn.run(
                            f"cat /tmp/jericho/jericho_key >> /{home_directory}/.ssh/authorized_keys"
                        )
                        await conn.run("apt update -y")
                        await conn.run("apt install git python3 python3-pip -y")
                        await conn.run(
                            "cd /tmp/jericho && git clone https://github.com/EmilKylander/jericho"
                        )
                        await conn.run("cd /tmp/jericho/jericho && pip3 install .")
                        await conn.run("rm -rf /tmp/jericho/jericho")
                        await conn.run(
                            f"echo {username}             soft    nofile          50000 >> /etc/security/limits.conf"
                        )
                        await conn.run("ulimit -n 50000")
                        await conn.run(
                            f"nohup jericho --listen > /{username}/jericho.log 2>&1 &"
                        )
                        self.instances.append(instance["resp"]["ipv4"][0])
                        return True
            except Exception as err:
                logging.error(
                    "Could not connect to %s because of error %s, retrying..",
                    instance["resp"]["ipv4"][0],
                    err,
                )

    async def block_until_ready(self, instances):
        """Block until the Jericho VPSes are at a running state"""
        while True:
            ready = await self.provider.get_ready()
            logging.info("Instances running: %s", ready)
            if instances == ready:
                return True

            await asyncio.sleep(1)

    async def delete_instances(self):
        """Delete the VPSes from the cloud provider which are related to Jericho"""
        return await self.provider.delete_instances()

    async def get_instances(self, show_all=False):
        """Send a message to the cloud provider and ask which of our VPSes of Jericho are available"""
        return await self.provider.get_instances(show_all)

    async def setup(self, num_instances: int) -> list:
        """Setup the cloud instances asynchronously through SSH"""
        if not os.path.isfile(f"/home/{get_username()}/.ssh/jericho_key.pub"):
            logging.info("Creating the public key..")
            os.system(
                f'cd /home/{get_username()}/.ssh/ && ssh-keygen -f jericho_key -N ""'
            )

        logging.info("Creating %s instances..", num_instances)

        # Should not create them all at once on Linode, will cause problems
        instances_created = []
        l = [0] * num_instances
        for iteration in chunks(l, 5):
            logging.info("Asking Linode to create %s instances", len(iteration))
            instances = [self.provider.create() for _ in range(0, len(iteration))]
            res = await asyncio.gather(*instances)
            instances_created = instances_created + res

        print("Waiting for all instances to be come ready")
        await self.block_until_ready(num_instances)

        # Wait an additional 60 seconds as it might take a while it to be reachable after it's ready
        print("Waiting for all instances to connection ready")
        await asyncio.sleep(60)

        logging.info("Installing Jericho on %s instances..", num_instances)
        setup_clouds = [self.run_client(instance) for instance in instances_created]
        await asyncio.gather(*setup_clouds)

        return self.instances

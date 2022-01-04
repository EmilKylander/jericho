#!/bin/python3
import logging
import asyncio
import asyncssh
import os
from jericho.helpers import get_username


class Cloud:
    def __init__(self, provider):
        self.provider = provider
        self.instances = []

    async def run_client(self, instance):
        """Run the installation synchronously"""
        logging.info("Logging into server %s", instance["resp"]["ipv4"][0])
        while True:
            try:
                async with asyncssh.connect(
                    instance["resp"]["ipv4"][0],
                    username="root",
                    password=instance.get("password"),
                    known_hosts=None,
                ) as conn:
                    async with conn.start_sftp_client() as sftp:
                        await sftp.put(
                            f"/home/{get_username()}/.ssh/jericho_key.pub",
                            "/root/jericho_key",
                        )
                        await conn.run(
                            "cat /root/jericho_key >> /root/.ssh/authorized_keys"
                        )
                        await conn.run("apt update -y")
                        await conn.run("apt install git python3 python3-pip -y")
                        await conn.run(
                            "git clone https://github.com/EmilKylander/jericho"
                        )
                        await conn.run("cd jericho")
                        await conn.run("cd jericho && pip3 install .")
                        await conn.run("rm -rf jericho")
                        await conn.run(
                            "echo root             soft    nofile          50000 >> /etc/security/limits.conf"
                        )
                        await conn.run("ulimit -n 50000")
                        await conn.run("nohup jericho --listen > /root/jericho.log 2>&1 &")
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
        instances = [self.provider.create() for _ in range(0, num_instances)]
        instances_created = await asyncio.gather(*instances)

        logging.info("Installing Jericho on %s instances..", num_instances)
        setup_clouds = [self.run_client(instance) for instance in instances_created]
        await asyncio.gather(*setup_clouds)

        await self.block_until_ready(num_instances)

        return self.instances

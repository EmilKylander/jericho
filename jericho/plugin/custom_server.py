#!/bin/python3

class CustomServer:
    def __init__(self, ip: str, username: str, password: str):
        self.ip = ip
        self.username = username
        self.password = password
        self.instances = []


    async def create(self):
        """Just return the data a gain"""

        self.instances.append(self.ip)
        return {"password": self.password, "resp": {'ipv4': [self.ip], 'username': self.username}}

    async def get_instances(self, show_all=False):
        """Return the IP in an array"""
        return [self.ip]

    async def get_ready(self):
        """Get all Jericho VPSes that are running"""
        return 1

    async def delete_instances(self):
        """Delete are VPSes that are related to Jerico"""

        return len(self.instances)
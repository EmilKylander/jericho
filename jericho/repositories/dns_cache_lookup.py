#!/bin/python3
import logging
import typing
import aiosqlite
from click import option
from sqlalchemy import delete
from jericho.models import Base
from jericho.models import JerichoDnsCacheLookup
from pathlib import Path


class DnsCacheLookup:
    def __init__(self, session):
        self.session = session
        self.db = None

    async def connect_db(self):
        "connect to the database"
        self.db = await aiosqlite.connect(f"{str(Path.home())}/jericho/jericho.db")

    async def find_ip(self, domain: str) -> typing.Optional[str]:
        """Check if a domain exist and if so get the content"""
        attempt = 0
        while True:
            try:
                async with self.db.execute("SELECT * FROM jericho_dns_cache_lookup WHERE domain=?", (domain, )) as cursor:
                    rows = await cursor.fetchall()
                    if len(rows) == 0:
                        return None

                    return rows[0][1]
            except Exception as error:
                logging.error("Could not find ip because of error %s - attempt %s", error, attempt)
                attempt = attempt + 1

    async def save(self, domain: str, ip_address: str) -> bool:
        """Save the ip address of a domain"""
        try:
            # Using aiosqlite for inserts because we are in an event loop right now and should therefore optimize the speed
            await self.db.execute("INSERT OR IGNORE INTO jericho_dns_cache_lookup(domain, ip_address) VALUES(?, ?)", (domain, ip_address, ))
            await self.db.commit()
            return True
        except Exception as error:
            logging.error("Could not save ip address of domain %s because of error %s", domain, error)
            await self.db.rollback()
            return False

    async def close(self):
        await self.db.close()
#!/bin/python3
import logging
from sqlalchemy import delete
from jericho.models import JerichoDnsServers


class DnsServerLookup:
    def __init__(self, session):
        self.session = session

    def get_all(self) -> list:
        """Check if a domain exist and if so get the content"""
        servers = self.session.query(JerichoDnsServers).all()

        return [server.server for server in servers]

    def delete_all(self) -> bool:
        """Delete all result"""
        try:
            self.session.execute(delete(JerichoDnsServers))
            self.session.commit()
            return True
        except Exception as err:
            logging.warning("Could not delete all records because of error %s", err)
            return False

    def save(self, server: str) -> bool:
        """Save a result"""

        try:
            result = JerichoDnsServers(server=server)
            self.session.add(result)
            self.session.commit()
            logging.debug("Added dns server %s", server)
            return True
        except Exception as err:
            logging.warning(
                "Could not save dns server %s because of error %s", server, err
            )
            self.session.rollback()
            return False

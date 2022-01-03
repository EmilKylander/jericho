#!/bin/python3
import logging
from sqlalchemy import delete
from jericho.models import JerichoServers


class ServerLookup:
    def __init__(self, session):
        self.session = session

    def save(self, server: str) -> bool:
        """Save a server"""

        try:
            result = JerichoServers(server=server.strip())
            self.session.add(result)
            self.session.commit()
            return True
        except Exception as err:
            logging.warning("Could not save server %s because of error %s", server, err)
            self.session.rollback()
            return False

    def get(self) -> list:
        """Get all servers"""
        records = self.session.query(JerichoServers).all()

        return [(record.server) for record in records]

    def delete(self, server: str) -> bool:
        """Delete a server from our database"""
        try:
            self.session.execute(
                delete(JerichoServers).where(JerichoServers.server == server)
            )
            self.session.commit()
            return True
        except Exception as err:
            logging.warning(
                "Could not delete the server entry %s because of error %s", server, err
            )
            self.session.rollback()
            return False

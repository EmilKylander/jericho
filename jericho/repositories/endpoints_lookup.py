#!/bin/python3
import logging
from jericho.models import JerichoEndpoints
from sqlalchemy import delete


class EndpointsLookup:
    def __init__(self, session):
        self.session = session

    def get(self) -> list:
        """Get all the endpoints and patterns"""
        content = self.session.query(JerichoEndpoints).all()

        return [
            {"endpoint": raw_object.endpoint, "pattern": raw_object.pattern}
            for raw_object in content
        ]

    def delete_all(self) -> bool:
        """Delete all endpoints"""
        try:
            self.session.execute(delete(JerichoEndpoints))
            self.session.commit()
            return True
        except Exception as err:
            logging.warning(
                "Could not delete all endpoints records because of error %s", err
            )
            return False

    def save_all(self, rows: list) -> None:
        """Save a list of endpoints"""
        for row in rows:
            entry = JerichoEndpoints(
                endpoint=row["endpoint"], pattern=row["pattern"], is_checked=0
            )
            self.session.add(entry)
            self.session.commit()

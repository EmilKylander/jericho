#!/bin/python3
import typing
import logging
from jericho.models import JerichoWorkload


class WorkloadLookup:
    def __init__(self, session):
        self.session = session

    def get(self) -> typing.Generator:
        """Check if a domain exist and if so get the content"""
        res: list = (
            self.session.query(JerichoWorkload)
            .all()
        )
        return [record.workload_uuid for record in res]

    def save(self, workload_uuid: str) -> bool:
        """Save a server"""

        try:
            result = JerichoWorkload(workload_uuid=workload_uuid.strip())
            self.session.add(result)
            self.session.commit()
            return True
        except Exception as err:
            logging.warning("Could not save server %s because of error %s", workload_uuid, err)
            self.session.rollback()
            return False

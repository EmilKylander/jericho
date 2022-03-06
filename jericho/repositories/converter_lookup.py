#!/bin/python3
import logging
from sqlalchemy import delete
from jericho.models import JerichoConverter


class ConverterLookup:
    def __init__(self, session):
        self.session = session

    def save(self, workload_uuid: str, location: str) -> bool:
        """Save a converter result"""

        try:
            result = JerichoConverter(workload_uuid=workload_uuid, location=location)
            self.session.add(result)
            self.session.commit()
            return True
        except Exception as err:
            logging.warning("Could not save converter result %s because of error %s", location, err)
            self.session.rollback()
            return False

    def get(self) -> list:
        """Get all servers"""

        return [
            {"workload_uuid": raw_object.workload_uuid, "location": raw_object.location}
            for raw_object in self.session.query(JerichoConverter).all()
        ]

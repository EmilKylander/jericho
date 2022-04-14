#!/bin/python3
import logging
import uuid
from pkg_resources import WorkingSet
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

    def get_workload(self, workload_uuid: uuid.uuid4) -> list:
        """Get all servers"""

        return [
            {"workload_uuid": raw_object.workload_uuid, "location": raw_object.location}
            for raw_object in self.session.query(JerichoConverter).filter(JerichoConverter.workload_uuid == workload_uuid).all()
        ]


    def delete_workload(self) -> bool:
        """Delete a workload from our converter database"""
        try:
            self.session.execute(
                delete(JerichoConverter)
            )
            self.session.commit()

            return True
        except Exception as err:
            logging.warning(
                "Could not delete the workload uuid of converters because of error %s", err
            )
            self.session.rollback()
            return False

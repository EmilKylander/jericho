#!/bin/python3
import logging
import uuid
from jericho.models import JerichoResult
from sqlalchemy import delete


class ResultLookup:
    def __init__(self, session):
        self.session = session

    def find(self, workload_uuid: uuid.uuid4, endpoint: str) -> bool:
        """Find result by endpoint"""
        try:
            found_rows = bool(
                self.session.query(JerichoResult)
                .filter(
                    JerichoResult.endpoint == endpoint,
                    JerichoResult.workload_uuid == workload_uuid,
                )
                .first()
            )
        except Exception as err:
            logging.warning(
                "Could not search for %s because of error %s", endpoint, err
            )
            return False

        return found_rows

    def get(self, workload_uuid: uuid.uuid4 = None) -> list:
        """Get all results"""
        if workload_uuid is not None:
            logging.debug("Getting records with workload uuid %s", workload_uuid)
            records = (
                self.session.query(JerichoResult)
                .filter(JerichoResult.workload_uuid == workload_uuid)
                .all()
            )
        else:
            logging.debug("Getting all records")
            records = self.session.query(JerichoResult).all()

        return [(record.endpoint, record.content) for record in records]

    def save(self, workload_uuid: uuid.uuid4, endpoint: str, content: str) -> bool:
        """Save a result"""
        if workload_uuid is not None and self.find(workload_uuid, endpoint):
            return False

        try:
            result = JerichoResult(
                workload_uuid=workload_uuid, endpoint=endpoint, content=content.strip()
            )
            self.session.add(result)
            self.session.commit()
            return True
        except Exception as err:
            logging.warning(
                "Could not save endpoint %s because of error %s", endpoint, err
            )
            self.session.rollback()
            return False

    def delete_all(self) -> bool:
        """Delete all result"""
        try:
            self.session.execute(delete(JerichoResult))
            self.session.commit()
            return True
        except Exception as err:
            logging.warning("Could not delete all records because of error %s", err)
            return False

    def delete_workload(self, workload_uuid: uuid.uuid4) -> bool:
        """Delete all result"""
        try:
            self.session.query(JerichoResult).filter(
                JerichoResult.workload_uuid == workload_uuid
            ).delete()
            self.session.commit()
            return True
        except Exception as err:
            logging.warning(
                "Could not delete workload uuid %s records because of error %s",
                workload_uuid,
                err,
            )
            return False

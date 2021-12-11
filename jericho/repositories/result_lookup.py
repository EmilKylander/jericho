#!/bin/python3
import logging
from jericho.models import JerichoResult
from sqlalchemy import delete


class ResultLookup:
    def __init__(self, session):
        self.session = session

    def find(self, endpoint: str) -> bool:
        """Find result by endpoint"""
        try:
            content = (
                self.session.query(JerichoResult)
                .filter(JerichoResult.endpoint == endpoint)
                .all()
            )
        except Exception as err:
            logging.warning(f"Could not search for {endpoint} because of error {err}")
            return True

        return len(content) > 0

    def get(self) -> list:
        """Get all results"""
        records = self.session.query(JerichoResult).all()
        return [record.endpoint for record in records]

    def save(self, endpoint, content) -> bool:
        """Save a result"""
        try:
            result = JerichoResult(endpoint=endpoint, content=content.strip())
            self.session.add(result)
            self.session.commit()
            return True
        except Exception as err:
            logging.warning(
                "Could not save endpoint %s because of error %s", endpoint, err
            )
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

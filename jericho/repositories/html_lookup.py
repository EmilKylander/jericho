#!/bin/python3
import typing
import logging
from sqlalchemy import delete
from jericho.models import JerichoHtml


class HtmlLookup:
    def __init__(self, session):
        self.session = session

    def get_all(self, workload_uuid: str) -> typing.Generator:
        """Check if a domain exist and if so get the content"""
        offset = 0
        while True:
            res: list = (
                self.session.query(JerichoHtml)
                .filter(JerichoHtml.workload_uuid == workload_uuid)
                .offset(offset)
                .limit(10)
                .all()
            )

            offset = offset + 10

            if len(res) == 0:
                break

            yield res

    def delete_workload(self, workload_uuid: str):
        """Delete a workload from our database"""
        try:
            self.session.execute(
                delete(JerichoHtml).where(JerichoHtml.workload_uuid == workload_uuid)
            )
            return True
        except Exception as err:
            logging.warning(
                "Could not delete the jericho html workload uuid %s because of error %s",
                workload_uuid,
                err,
            )
            self.session.rollback()
            return False

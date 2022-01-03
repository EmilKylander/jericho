#!/bin/python3
import typing
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

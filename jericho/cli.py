import os
import typing
import json
import logging
from aiohttp import ClientSession

from jericho.models import JerichoEndpoints
from jericho.repositories.endpoints_lookup import EndpointsLookup
from jericho.repositories.result_lookup import ResultLookup
from jericho.version import version


def import_endpoints(session, filepath: str) -> None:
    """This should be ran on the source server. It\'s to import endpoints to the local db"""
    imported = 0
    with open(filepath, encoding="utf-8") as file:
        for row in json.load(file):
            content = (
                session.query(JerichoEndpoints)
                .filter(JerichoEndpoints.endpoint == row["endpoint"])
                .all()
            )

            if len(content) == 0:
                entry = JerichoEndpoints(
                    endpoint=row["endpoint"], pattern=row["pattern"], is_checked=0
                )
                session.add(entry)
                session.commit()
                imported = imported + 1

    logging.info("Imported %s endpoints!", imported)


def get_records(result_lookup: ResultLookup) -> None:
    """This prints out all of the results we have in our database"""
    for domain in result_lookup.get():
        print(domain)


def delete_records(result_lookup: ResultLookup) -> None:
    """This deletes all of the results we have in our database"""
    if result_lookup.delete_all():
        print("OK")
    else:
        print("ERROR")


def delete_endpoints(endpoints_lookup: EndpointsLookup) -> None:
    """This deletes out all of the endpoints we have in our database"""
    if endpoints_lookup.delete_all():
        print("OK")
    else:
        print("ERROR")


def upgrade() -> None:
    """This function upgrades Jericho to the latest version"""
    print("Downloading source...")
    os.system("git clone https://github.com/EmilKylander/jericho /tmp/jericho")
    print("Installing")
    os.system("cd /tmp/jericho && pip3 install .")
    os.system("rm -rf /tmp/jericho")
    print("done")


def get_version() -> typing.Any:
    print(version)


def get_endpoints(endpoints_lookup: EndpointsLookup) -> typing.Any:
    """This prints out all of the results we have in our database"""
    for endpoint in endpoints_lookup.get():
        print(f"{endpoint['endpoint']}\t{endpoint['pattern']}")

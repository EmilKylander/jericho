import os
import typing
import json
import logging
import aiohttp
from datetime import datetime
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
        print(domain[0])


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

async def pull_dns_servers(servers: list) -> typing.Optional[list]:
    async with ClientSession(
        connector=aiohttp.TCPConnector(
            ssl=False,
            enable_cleanup_closed=True,
            force_close=True,
        ),
        cookie_jar=aiohttp.DummyCookieJar(),
    ) as session:
        async with session.get(
            "https://api.github.com/repos/cxosmo/dns-resolvers",
            ssl=False,
            allow_redirects=True,
            timeout=10,
        ) as response:
            list_bytes = await response.read()
            github_api_response = json.loads(list_bytes.decode("utf-8", "ignore"))
            last_updated = datetime.strptime(
                github_api_response.get("updated_at"), "%Y-%m-%dT%H:%M:%SZ"
            )

        days = (datetime.now() - last_updated).days
        if days == 0 and not len(servers) == 0:
            return None

        async with session.get(
            "https://raw.githubusercontent.com/cxosmo/dns-resolvers/main/resolvers.txt",
            ssl=False,
            allow_redirects=True,
            timeout=10,
        ) as response:
            list_bytes = await response.read()
            list_str = list_bytes.decode("utf-8", "ignore")
            return [server for server in list_str.split("\n") if not server == ""]

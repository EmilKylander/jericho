"""Leaked files identifier for web servers

This script allows you to pull domains from a database table
and specify endpoints in a yaml file. This will later compile a list
of your endpoints and your web servers and tries to access them using aiohttp.

In order to prevent specific web servers being overrun with requests we iterate by
the endpoints first, this means we take the first endpoint in the list and try it against
all of the web servers. Once this is done we go to the next endpoint.

To prevent false positives you are able to specify what the endpoint is (YML, XML, JSON, NOT_HTML).
There is also a configuration which makes the script cache 404 pages for domains that
has found endpoints.
This will later evaluate if the 404 page and the found endpoint has the same md5.

To get your output you need to specify your Notification() class.
These are located in the notifications directory.

This file is suppose to be run from the command line.
"""

#!/bin/python3
import typing
import sys
import logging
import asyncio
from pathlib import Path
from os import path
import os
import argparse
import sqlalchemy
from mpi4py import MPI
from sqlalchemy.orm import sessionmaker
from typing import Final

from jericho.enums.http_request_methods import HttpRequestMethods

from jericho.plugin.async_http import AsyncHTTP
from jericho.plugin.investigate import Investigate
from jericho.plugin.diff import Diff
from jericho.plugin.result_is_relevant import ResultRelevant
from jericho.plugin.notifications import Notifications
from jericho.plugin.threaded_async_http import ThreadedAsyncHTTP
from jericho.repositories.cache_lookup import CacheLookup
from jericho.repositories.result_lookup import ResultLookup
from jericho.repositories.endpoints_lookup import EndpointsLookup

from jericho.models import Base

from jericho.cli import (
    import_endpoints,
    get_records,
    get_version,
    delete_records,
    delete_endpoints,
    upgrade
)

from jericho.enums.cluster_roles import ClusterRole

from jericho.helpers import (
    load_yaml_file,
    logger_convert,
    add_missing_schemes_to_domain_list,
    merge_array_to_iterator,
    parse_cluster_settings,
    split_array_by,
)

# Instantiate the parser
parser = argparse.ArgumentParser(description="Optional app description")

parser.add_argument(
    "--import-endpoints",
    type=str,
    help="Specify a json file of endpoints to import from",
)

parser.add_argument(
    "--get-records",
    action="store_true",
    help="Get every endpoint that was found after scan",
)

parser.add_argument(
    "--delete-records",
    action="store_true",
    help="Delete every result that is found",
)

parser.add_argument(
    "--delete-endpoints",
    action="store_true",
    help="Delete every endpoint that is found",
)

parser.add_argument(
    "--threads",
    type=int,
    help="Set the amount of threads. Default: 40",
)

parser.add_argument(
    "--input",
    type=str,
    help="The file with domains",
)

parser.add_argument(
    "--version",
    action="store_true",
    help="Get the Jericho version",
)

parser.add_argument(
    "--upgrade",
    action="store_true",
    help="Upgrades jericho to the latest version",
)

parser.add_argument(
    "--log-level",
    type=str,
    help="Set the Jericho log level. This overwrides the log level specified in configuration. Available modes: debug, info, warn, error, fatal, critical. Default: info",
)

parser.add_argument(
    "--batch-size",
    action="store_true",
    help="The size of the batch of domains that is sent simultaneously in an even loop per thread. Default 100",
)

HOME: Final = str(Path.home())

if not path.exists(f"{HOME}/jericho"):
    logging.info("Creating a jericho directory in %s", HOME)
    os.mkdir(f"{HOME}/jericho")
    default_configuration = f"""
jericho_database: sqlite:///{HOME}/jericho/jericho.db
log_level: info
max_result_and_404_percent_diff: 60
max_head_timeout: 5
max_get_timeout: 10
ignore_multimedia: true"""
    f = open(f"{HOME}/jericho/configuration.yml", "w")
    f.write(default_configuration)
    f.close()

comm = MPI.COMM_WORLD
mpi_size = comm.Get_size()
rank = comm.Get_rank()

# Suppress aiohttp ssl errors..
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

configuration = load_yaml_file(f"{HOME}/jericho/configuration.yml")

engine = sqlalchemy.create_engine(configuration["jericho_database"])
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

log_level = logger_convert(configuration.get("log_level", "info"))


class RankFilter(logging.Filter):
    """This class adds so we can have the cluster rank in the logging"""

    rank = rank

    def filter(self, record):
        record.rank = f"SERVER-RANK-{RankFilter.rank}"
        return True


class ClusterFilter(logging.Filter):
    """This class adds so we can have the cluster role in the logging"""

    cluster = parse_cluster_settings(rank, mpi_size)

    def filter(self, record):
        record.cluster = ClusterFilter.cluster
        return True

cluster_role = parse_cluster_settings(rank, mpi_size)

args = parser.parse_args()

root = logging.getLogger()
if args.log_level:
    print(f"Using log level '{args.log_level}' from CLI")
    root.setLevel(logger_convert(args.log_level))
else:
    root.setLevel(log_level)

handler = logging.StreamHandler(sys.stdout)
handler.addFilter(ClusterFilter())
handler.addFilter(RankFilter())

if cluster_role != ClusterRole.DISABLED:
    formatter = logging.Formatter(
        "%(asctime)s - %(cluster)s - %(rank)s - %(name)s - %(levelname)s - %(message)s"
    )
else:
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

handler.setFormatter(formatter)
root.addHandler(handler)

async_http = AsyncHTTP()
endpoints_lookup = EndpointsLookup(session)
investigate = Investigate(endpoints_lookup)
cache_lookup = CacheLookup(session)
result_lookup = ResultLookup(session)
diff = Diff()

result_relevant = ResultRelevant(
    investigate=investigate,
    result_lookup=result_lookup,
    cache_lookup=cache_lookup,
    async_http=async_http,
    diff=diff,
    configuration=configuration,
)

BATCH_SIZE: Final = 100 if args.batch_size is not None else args.batch_size
AMOUNT_OF_THREADS: Final = 40 if args.batch_size is not None else args.batch_size

if args.input:
    input = args.input

def save_result(url: str, output: str) -> None:
    """This is a callback with the purpose of saving a result"""
    logging.info("Got a callback to save url %s", url)

    if not result_lookup.find(url):
        logging.info("The url %s does not exist, saving..", url)
        result_lookup.save(url, output)


def execute(payload: tuple) -> list:
    """This is the main module which will handle all execution"""

    logging.info(f"Using {BATCH_SIZE} as batch size and {AMOUNT_OF_THREADS} amount of threads")

    notifications_configuration, endpoints, domains = payload
    total_results: typing.List = []
    threaded_async_http = ThreadedAsyncHTTP(
        async_http, AMOUNT_OF_THREADS, configuration
    )

    # The class is instantiated here because the payload contain the
    # relevant notifications settings
    if notifications_configuration:
        notifications = Notifications(notifications_configuration)

    if len(endpoints) == 0:
        logging.error("No endpoint patterns was supplied")
        return []

    total_sites = len(domains)
    logging.debug("Got %s amount of domains", total_sites)
    amount_scanned = 0

    logging.debug("Adding http and https schemes to the links..")
    domains = add_missing_schemes_to_domain_list(domains)
    total_sites_after_schemes = len(domains)

    urls = merge_array_to_iterator(endpoints, domains, domains_batch_size=BATCH_SIZE)
    for created_requests in urls:

        # Which endpoints respond with status 200 on HEAD requests?
        threaded_async_http.start_bulk(created_requests, HttpRequestMethods.HEAD)
        head_responsive = threaded_async_http.get_response()

        # Get the content of the endpoints with the OK http responses
        threaded_async_http.start_bulk(
            [head[0] for head in head_responsive], HttpRequestMethods.GET
        )
        endpoints_content_with_ok_status = threaded_async_http.get_response()

        # Which endpoints return data that is probably useful?
        relevant_results = [
            result
            for result in endpoints_content_with_ok_status
            if result_relevant.check(
                result[0], result[1]
            )  # Returned is a type (url, output)
        ]

        logging.debug("Sending the notifications..")
        # Send the relevant results to all of the HTTP callbacks (Slack, etc)
        if notifications_configuration:
            for url, _ in relevant_results:
                asyncio.run(notifications.run_all(url))

        logging.debug("Saving results..")
        # Just save the result in real time if its standalone
        if cluster_role == ClusterRole.DISABLED:
            for url, output in relevant_results:
                save_result(url, output)

        total_results = total_results + relevant_results
        amount_scanned = amount_scanned + len(created_requests)
        logging.info("Scanned %s/%s", amount_scanned, total_sites_after_schemes)

    threaded_async_http.close()
    return total_results


def run() -> None:
    """This initializes the business logic"""
    data = None
    if rank == 0:
        logging.info("Getting domains from --input...")
        if not os.path.exists(input):
            logging.error(f"The path {input} does not exist!")
            return False

        with open(input, encoding="utf-8") as file:
            lines = file.readlines()
            domains_loaded = [domain.strip() for domain in lines]

        logging.info("Scattering domains into %s chunks..", mpi_size)
        rows = split_array_by(domains_loaded, mpi_size)

        # Get the masters notifications settings so we can send it to the slaves
        master_configuration_notifications = configuration.get("notifications", {})

        endpoints_from_database = endpoints_lookup.get()
        data = [
            (master_configuration_notifications, endpoints_from_database, row)
            for row in rows
        ]

        logging.info("Done scattering domains (%s chunks)..", len(data))

    data = comm.scatter(data, root=0)

    data = execute(data)

    gathered_data = comm.gather(data, root=0)

    if cluster_role != ClusterRole.MASTER:
        return None

    for response in gathered_data:
        if not response:
            continue

        for url, output in response:
            save_result(url, output)


def main() -> typing.Any:
    """The main module"""

    if args.import_endpoints:
        import_endpoints(session, args.import_endpoints)

    if args.get_records:
        get_records(result_lookup)

    if args.delete_records:
        delete_records(result_lookup)

    if args.delete_endpoints:
        delete_endpoints(endpoints_lookup)

    if args.upgrade:
        upgrade()

    if args.version:
        get_version()

    if args.input is not None:
        run()

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
import asyncio
import queue
import typing
import sys
import logging
from pathlib import Path
from os import path
import os
import argparse
import sqlalchemy
import uuid
import asyncio
import json
from mpi4py import MPI
from sqlalchemy.orm import sessionmaker
from threading import Thread
from jericho.plugin.async_http import AsyncHTTP
from jericho.plugin.investigate import Investigate
from jericho.plugin.diff import Diff
from jericho.plugin.output_verifier import OutputVerifier
from jericho.plugin.result_is_relevant import ResultRelevant
from jericho.plugin.notifications import Notifications
from jericho.plugin.threaded_async_http import ThreadedAsyncHTTP
from jericho.plugin.data_bucket import DataBucket
from jericho.plugin.result import Result
from jericho.repositories.cache_lookup import CacheLookup
from jericho.repositories.result_lookup import ResultLookup
from jericho.repositories.endpoints_lookup import EndpointsLookup
from jericho.converters.identifier import Identifier
from jericho.plugin.result import Result

from jericho.models import Base

from jericho.enums.cluster_roles import ClusterRole
from jericho.enums.thread_response import ThreadResponse

from jericho.cli import (
    import_endpoints,
    get_records,
    get_version,
    delete_records,
    delete_endpoints,
    get_endpoints,
    upgrade,
)

from jericho.helpers import (
    load_yaml_file,
    logger_convert,
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
    help="Delete every endpoint",
)

parser.add_argument(
    "--get-endpoints",
    action="store_true",
    help="Get every endpoint",
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

parser.add_argument(
    "--scan-both-schemes",
    action="store_true",
    help="Scan both the http and the https for the supplies domains",
)

parser.add_argument(
    "--converter",
    type=str,
    help="You can also use Jericho as a form of web scraper, you need to specify a converter. Currently 'identifier' is available, read the documentation for more information. When this flag is set no endpoints will be appended or processed.",
)


HOME = str(Path.home())

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
investigate = Investigate()
cache_lookup = CacheLookup(session)
result_lookup = ResultLookup(session)
output_verifier = OutputVerifier()
diff = Diff()
data_bucket = DataBucket(max_size=100000)  # 100kB

BATCH_SIZE = 100 if args.batch_size is not None else args.batch_size
AMOUNT_OF_THREADS = 40
if args.threads:
    AMOUNT_OF_THREADS = args.threads

CONVERTERS = {"identifier": Identifier()}
if args.input:
    input = args.input


def execute(payload: tuple) -> list:
    """This is the main module which will handle all execution"""

    logging.info(
        f"Using {BATCH_SIZE} as batch size and {AMOUNT_OF_THREADS} amount of threads"
    )

    finish_queue: queue.Queue = queue.Queue()
    workload_uuid, configuration, endpoints, domains = payload
    notifications_configuration = configuration.get("notifications")
    converter_configuration = configuration.get("converter_notifications")

    # The class is instantiated here because the payload contain the
    # relevant notifications settings

    notifications = None
    if notifications_configuration:
        notifications = Notifications(notifications_configuration)

    converter_notifications = None
    if converter_configuration:
        converter_notifications = Notifications(converter_configuration)

    if len(endpoints) == 0:
        logging.error("No endpoint patterns was supplied")
        return []

    total_sites = len(domains)
    logging.info("Got %s amount of domains", total_sites)
    should_scan_both_schemes = args.scan_both_schemes

    total_endpoints = total_sites * len(endpoints)

    if should_scan_both_schemes:
        logging.info("Scanning both http and https")
        total_endpoints = total_endpoints * 2

    threaded_async_http = ThreadedAsyncHTTP(
        async_http,
        AMOUNT_OF_THREADS,
        configuration,
        finish_queue,
        should_scan_both_schemes=should_scan_both_schemes,
        ignore_endpoints=args.converter,
        endpoints=endpoints,
    )

    result_relevant = ResultRelevant(
        investigate=investigate,
        result_lookup=result_lookup,
        cache_lookup=cache_lookup,
        async_http=async_http,
        diff=diff,
        output_verifier=output_verifier,
        configuration=configuration,
        workload_uuid=workload_uuid,
    )

    result = Result(
        result_relevant,
        notifications_configuration,
        notifications,
        cluster_role,
        result_lookup,
        workload_uuid,
    )

    p = Thread(
        target=threaded_async_http.start_bulk,
        args=(
            domains,
            BATCH_SIZE,
        ),
    )
    p.start()

    while True:
        # We are using a queue to respond with the data so we're not blocking the threads when we parse the results
        queue_payload = finish_queue.get()
        if queue_payload.get("status") == ThreadResponse.DONE.value:
            logging.info("Finished")

            # When the scan is complete we need to pull the domains back from all replicas db.
            # However if we're running as ClusterRole.SOURCE or ClusterRole.DISABLED then
            # we already have it in our database.
            if cluster_role == ClusterRole.REPLICA:
                results = result_lookup.get(workload_uuid)
                result_lookup.delete_workload(workload_uuid)
                return results
            else:
                return []

        url = queue_payload.get("url")
        html = queue_payload.get("html")
        headers = queue_payload.get("headers")

        # We might want to get the actual data from the domains in a serialized form
        if args.converter:
            logging.debug("Running the converter on parsing %s", url)
            result = CONVERTERS.get(args.converter).run("", url, 200, headers, html)
            logging.info("Parsed %s - Title: %s", url, result["title"])
            data_bucket.save(result)

            if data_bucket.is_full():
                # Send the notifications for the converter
                logging.debug("Sending notifications")
                if converter_notifications:
                    asyncio.run(
                        converter_notifications.run_all(json.dumps(data_bucket.get()))
                    )
                data_bucket.empty()

            logging.debug("Sent all notifications")

            # The rest of the function analyzes endpoints, there's no point to keep it running
            continue

        logging.debug("Analyzing the responses")
        result.process(url, html, endpoints)


def run() -> None:
    """This initializes the business logic"""
    data = None
    if rank == 0:
        logging.debug("Getting domains from --input...")
        if not os.path.exists(input):
            logging.error("The path %s does not exist!", input)
            return None

        with open(input, encoding="utf-8") as file:
            lines = file.readlines()
            domains_loaded = [domain.strip() for domain in lines]

        logging.debug("Scattering domains into %s chunks..", mpi_size)
        rows = split_array_by(domains_loaded, mpi_size)

        # Get the sources notifications settings so we can send it to the replicas

        endpoints_from_database = endpoints_lookup.get()
        workload_uuid = str(uuid.uuid4())
        logging.info("Using workload uid %s", workload_uuid)
        data = [
            (workload_uuid, configuration, endpoints_from_database, row) for row in rows
        ]

        logging.debug("Done scattering domains (%s chunks)..", len(data))

    data = comm.scatter(data, root=0)

    logging.info(
        "Starting with %s threads and %s batch size", AMOUNT_OF_THREADS, BATCH_SIZE
    )

    data = execute(data)

    # Combine all of the replica results and save it to the ClusterRole.SOURCE database
    data = comm.gather(data, root=0)

    # Only the source should gather the data
    if cluster_role == ClusterRole.SOURCE:
        for response in data:
            for url, output in response:
                logging.info("Saving url %s to source database", url)
                result_lookup.save(workload_uuid, url, output)


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

    if args.get_endpoints:
        get_endpoints(endpoints_lookup)

    if args.upgrade:
        upgrade()

    if args.version:
        get_version()

    if args.input is not None:
        run()

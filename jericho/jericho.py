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
import aiosqlite
import uvloop
import base64
import shutil
import sys
from threading import Thread
from sqlalchemy.orm import sessionmaker
from jericho.plugin.async_http import AsyncHTTP
from jericho.plugin.investigate import Investigate
from jericho.plugin.diff import Diff
from jericho.plugin.output_verifier import OutputVerifier
from jericho.plugin.result_is_relevant import ResultRelevant
from jericho.plugin.notifications import Notifications
from jericho.plugin.data_bucket import DataBucket
from jericho.plugin.linode import Linode
from jericho.plugin.custom_server import CustomServer
from jericho.plugin.cloud import Cloud
from jericho.plugin.cluster import Cluster
from jericho.repositories.cache_lookup import CacheLookup
from jericho.repositories.result_lookup import ResultLookup
from jericho.repositories.endpoints_lookup import EndpointsLookup
from jericho.repositories.html_lookup import HtmlLookup
from jericho.repositories.dns_server_lookup import DnsServerLookup
from jericho.repositories.converter_lookup import ConverterLookup
from jericho.repositories.workload_lookup import WorkloadLookup
from jericho.repositories.dns_cache_lookup import DnsCacheLookup
from jericho.converters.identifier import Identifier

from jericho.models import Base

from jericho.enums.cluster_roles import ClusterRole
from jericho.enums.http_codes import HttpStatusCode
from jericho.enums.cluster_response_type import ClusterResponseType

from jericho.cli import (
    import_endpoints,
    get_records,
    get_version,
    delete_records,
    delete_endpoints,
    get_endpoints,
    upgrade,
    pull_dns_servers,
    get_converter_output,
)

from jericho.helpers import (
    load_yaml_file,
    logger_convert,
    merge_domains_with_endpoints,
    get_domain_from_endpoint,
)
from jericho.repositories.server_lookup import ServerLookup

if sys.platform == 'win32':
    # Set the policy to prevent "Event loop is closed" error on Windows - https://github.com/encode/httpx/issues/914
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


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
    "--input",
    type=str,
    help="The file with domains",
)

parser.add_argument(
    "--continue-workload",
    type=str,
    help="Continue on a workload if the client disconnected (This will re-download every job result)",
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
    "--upgrade-all",
    action="store_true",
    help="Upgrades jericho to the latest version on this computer and on all servers",
)

parser.add_argument(
    "--log-level",
    type=str,
    help="Set the Jericho log level. This overwrides the log level specified in configuration. Available modes: debug, info, warn, error, fatal, critical. Default: info",
)

parser.add_argument(
    "--converter",
    type=str,
    help="You can also use Jericho as a form of web scraper, you need to specify a converter. Currently 'identifier' is available, read the documentation for more information. When this flag is set no endpoints will be appended or processed.",
)

parser.add_argument(
    "--nameservers",
    type=str,
    help="Jericho uses a default list with the 14 most popular DNS servers, you can use your own dns server list instead through a file. Round robin is enabled regardless",
)

parser.add_argument(
    "--resolve-list",
    type=str,
    help="This is mostly good for benchmarking and testing, by giving a file with domain:ip format per line Jericho will inject this to the internal DNS cache and use it through out the program",
)

parser.add_argument(
    "--max-requests",
    type=int,
    help="The maximum requests per second that the program will send, default 10,000",
)

parser.add_argument(
    "--setup-linodes",
    type=int,
    help="Setup X amount of Linodes and automatically exchange public keys and install Jericho",
)

parser.add_argument(
    "--delete-linodes",
    action="store_true",
    help="Deletes all Linodes prefixed with 'jericho'",
)

parser.add_argument(
    "--ignore-cloud-duplicates",
    action="store_true",
    help="Add instances to cloud even though there's existing Jericho instances",
)

parser.add_argument(
    "--get-linodes",
    action="store_true",
    help="Show all of the Linodes that is used for Jericho",
)

parser.add_argument(
    "--add-server",
    type=str,
    help="Add a server to the server list, use like --add-server 1.2.3.4",
)

parser.add_argument(
    "--remove-server",
    type=str,
    help="Remove a server to the server list, use like --remove-server 1.2.3.4",
)

parser.add_argument(
    "--remove-servers",
    action="store_true",
    help="Remove all servers to the server list",
)

parser.add_argument(
    "--get-servers",
    action="store_true",
    help="Get the servers",
)

parser.add_argument(
    "--use-servers",
    action="store_true",
    help="Use the servers when scanning",
)


parser.add_argument(
    "--get-last-workload-uuid",
    action="store_true",
    help="Get the latest workload uuid",
)

parser.add_argument(
    "--include-master",
    action="store_true",
    help="This includes the source computer in the scanning",
)

parser.add_argument(
    "--listen",
    action="store_true",
    help="Start a Jericho replica that will listen for jobs",
)

parser.add_argument(
    "--get-converter-output",
    action="store_true",
    help="Get the locations of the compressed result from converter jobs",
)

parser.add_argument(
    "--delete-converter-result",
    action="store_true",
    help="Delete all of the result which come from the converter",
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

configuration = load_yaml_file(f"{HOME}/jericho/configuration.yml")

engine = sqlalchemy.create_engine(configuration["jericho_database"])
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


server_lookup = ServerLookup(session)
dns_cache_lookup = DnsCacheLookup(session)

args = parser.parse_args()

servers = []
if args.use_servers:
    servers = server_lookup.get()
    if len(servers) == 0:
        logging.error("No servers in the database, quitting..")
        sys.exit(1)

cluster = Cluster(servers=servers)

cluster_size = len(servers)

cluster_role = ClusterRole.DISABLED
if args.use_servers:
    cluster_role = ClusterRole.SOURCE
if args.listen:
    cluster_role = ClusterRole.REPLICA

log_level = logger_convert(configuration.get("log_level", "info"))


class ClusterFilter(logging.Filter):
    """This class adds so we can have the cluster role in the logging"""

    cluster = cluster_role

    def filter(self, record):
        record.cluster = ClusterFilter.cluster
        return True


args = parser.parse_args()

root = logging.getLogger()
if args.log_level:
    root.setLevel(logger_convert(args.log_level))
else:
    root.setLevel(log_level)

handler = logging.StreamHandler(sys.stdout)
handler.addFilter(ClusterFilter())

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

handler.setFormatter(formatter)
root.addHandler(handler)


NAMESERVERS = []
DNS_CACHE = {}
MAX_REQUESTS = 100

if args.max_requests:
    MAX_REQUESTS = args.max_requests

if args.nameservers:
    with open(args.nameservers, encoding="utf-8") as file:
        lines = file.readlines()
        NAMESERVERS = [nameserver.strip() for nameserver in lines]

if args.resolve_list:
    with open(args.resolve_list, encoding="utf-8") as file:
        lines = file.readlines()
        for entry in lines:
            domain, ip = entry.split(":")
            DNS_CACHE[domain.strip()] = ip.strip()
    logging.debug("Loaded %s domains into dns cache", DNS_CACHE)

if args.listen:
    cluster.start_zmq_server()
    cluster.start_zmq_subscribe_server()

endpoints_lookup = EndpointsLookup(session)
investigate = Investigate()
cache_lookup = CacheLookup(session)
result_lookup = ResultLookup(session)
html_lookup = HtmlLookup(session)
dns_server_lookup = DnsServerLookup(session)

output_verifier = OutputVerifier()
diff = Diff()
data_bucket = DataBucket(
    max_size=100000000
)  # 100Mb (Avoid hitting the max ram when zipping)

CONVERTERS = {"identifier": Identifier()}
if args.input:
    input = args.input


async def start_aiohttp_loop(
    send_domains: typing.List,
    endpoints: typing.List,
    settings: dict,
    nameservers: typing.List[str],
    rank: int,
    dns_cache: typing.List,
):
    async_http = AsyncHTTP(
        nameservers=nameservers,
        dns_cache=dns_cache,
        max_requests=MAX_REQUESTS,
        cluster=cluster,
        rank=rank,
        dns_cache_lookup=dns_cache_lookup
    )

    workload_uuid = settings.get("workload_uuid")
    logging.debug("Starting async loop")
    async for url, html, headers, not_found_html in async_http.get(
        send_domains,
        settings={
            "status": HttpStatusCode.OK.value,
            "timeout": configuration.get("max_get_timeout"),
            "ignore_multimedia": configuration.get("ignore_multimedia"),
            "endpoints": endpoints
        },
    ):
        if url is None:
            continue
        while True:
            try:
                logging.debug("Saving output for %s", url)

                logging.debug(
                    "Accessing database sqlite:///%s/jericho/jericho.db", HOME
                )
                db = await aiosqlite.connect(f"/{HOME}/jericho/jericho.db")

                # Using aiosqlite for inserts because we are in an event loop right now and should therefore optimize the speed
                cursor = await db.execute(
                    "INSERT OR IGNORE INTO jericho_html(workload_uuid, endpoint, content, headers) VALUES(?, ?, ?, ?)",
                    (workload_uuid, url, html, json.dumps(dict(headers))),
                )
                await db.commit()

                cursor = await db.execute(
                    "INSERT OR IGNORE  INTO jericho_404_caches(domain, content) VALUES(?, ?)",
                    (get_domain_from_endpoint(url), not_found_html),
                )
                await db.commit()

                await cursor.close()

                break
            except Exception as err:
                logging.exception(
                    "Could not save %s to database tables because of error: %s",
                    url,
                    err,
                )
                await db.rollback()
            finally:
                await db.close()


def receiver(cluster: Cluster):
    engine = sqlalchemy.create_engine(configuration["jericho_database"])
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    result_lookup = ResultLookup(session)
    converter_lookup = ConverterLookup(session)

    logging.info("Waiting for result messages..")
    for response in cluster.receive_zmq_message():
        if response.get("type") == ClusterResponseType.RESULT.value:
            logging.info("Saving url %s to source database", response.get("endpoint"))
            result_lookup.save(
                response.get("workload_uuid"),
                response.get("endpoint"),
                response.get("content"),
            )

        if response.get("type") == ClusterResponseType.STATISTICS.value:
            logging.info(
                "Statistics (Rank %s) | Finished Requests: %s",
                response.get("rank"),
                response.get("finished_requests"),
            )

        if response.get("type") == ClusterResponseType.WEBPAGE_CONTENT.value:
            logging.info(
                "Node %s sent back compressed data",
                response.get("rank"),
            )
            content = base64.b64decode(response.get("zip"))
            zip_output_file = open(
                f"/tmp/{response.get('uuid')}.zip", "w", encoding="utf-8"
            )
            zip_output_file.write(content.decode("UTF-8", "ignore"))
            zip_output_file.close()

            converter_lookup.save(
                response.get("workload_uuid"), f"/tmp/{response.get('uuid')}.zip"
            )


def execute(
    domains: typing.List[str],
    workload_uuid: uuid.uuid4,
    nameservers: typing.List[str],
    configuration: dict,
    rank: int,
    endpoints: typing.List,
    dns_cache: typing.List,
    converter: typing.Optional[str],
):
    """This is the main module which will handle all execution"""

    uvloop.install()

    notifications_configuration = configuration.get("notifications")
    converter_configuration = configuration.get("converter_notifications")

    result_relevant = ResultRelevant(
        investigate=investigate,
        result_lookup=result_lookup,
        cache_lookup=cache_lookup,
        diff=diff,
        output_verifier=output_verifier,
        configuration=configuration,
        workload_uuid=workload_uuid,
    )

    # The class is instantiated here because the payload contain the
    # relevant notifications settings

    notifications = None
    if notifications_configuration:
        notifications = Notifications(notifications_configuration)

    converter_notifications = None
    if converter_configuration:
        converter_notifications = Notifications(converter_configuration)

    total_sites = len(domains)
    logging.info("Got %s amount of domains", total_sites)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        start_aiohttp_loop(
            domains,
            endpoints,
            settings={
                "workload_uuid": workload_uuid,
                "converter_notifications": converter_notifications,
                "notifications": notifications,
            },
            nameservers=nameservers,
            rank=rank,
            dns_cache=dns_cache,
        )
    )

    if converter:
        converter_lookup = ConverterLookup(session)
        for record_chunk in html_lookup.get_all(workload_uuid):
            for record in record_chunk:
                logging.debug("Running the converter on %s", record.endpoint)
                result = CONVERTERS.get(converter).run(
                    "", record.endpoint, 200, json.loads(record.headers), record.content
                )

                logging.info("Parsed %s - Title: %s", record.endpoint, result["title"])

                data_bucket.save(
                    (
                        record.endpoint,
                        json.dumps({"content": record.content, "result": result}),
                    )
                )

                path = data_bucket.get()

                if data_bucket.is_full():
                    with open(path, "rb") as f:
                        encoded_string = base64.b64encode(f.read()).decode()

                    cluster.send_zmq_message(
                        json.dumps(
                            {
                                "rank": rank,
                                "type": ClusterResponseType.WEBPAGE_CONTENT.value,
                                "workload_uuid": workload_uuid,
                                "uuid": data_bucket.get_uuid(),
                                "zip": encoded_string,
                            }
                        )
                    )
                    data_bucket.empty()

                    # Save the result files in case of client crash
                    if rank >= 1:
                        new_location = f"/tmp/{uuid.uuid4()}"
                        shutil.copyfile(path, new_location)
                        converter_lookup.save(workload_uuid, new_location)

        html_lookup.delete_workload(workload_uuid)

        if not data_bucket.is_empty():
            path = data_bucket.get()
            with open(path, "rb") as f:
                encoded_string = base64.b64encode(f.read()).decode()

            cluster.send_zmq_message(
                json.dumps(
                    {
                        "rank": rank,
                        "type": ClusterResponseType.WEBPAGE_CONTENT.value,
                        "workload_uuid": workload_uuid,
                        "uuid": data_bucket.get_uuid(),
                        "zip": encoded_string,
                    }
                )
            )
            data_bucket.empty()

            # Save the result files in case of client crash
            if rank >= 1:
                new_location = f"/tmp/{uuid.uuid4()}"
                shutil.copyfile(path, new_location)
                converter_lookup.save(workload_uuid, new_location)

        html_lookup.delete_workload(workload_uuid)

        if cluster_role == ClusterRole.REPLICA:
            cluster.send_zmq_message(ClusterResponseType.FINISHED.value)

        return []

    for record_chunk in html_lookup.get_all(workload_uuid):
        for record in record_chunk:
            if not result_relevant.check(record.endpoint, record.content, endpoints):
                continue

            if notifications:
                logging.debug("Sending the notifications..")
                asyncio.run(notifications.run_all(record.url))

            logging.debug("Saving result..")
            if (
                cluster_role == ClusterRole.SOURCE and not args.use_servers
            ) or cluster_role == ClusterRole.DISABLED:
                result_lookup.save(workload_uuid, record.endpoint, record.content)

            if cluster_role == ClusterRole.REPLICA:
                logging.info("Sending endpoint %s to source", record.endpoint)
                cluster.send_zmq_message(
                    json.dumps(
                        {
                            "type": ClusterResponseType.RESULT.value,
                            "workload_uuid": workload_uuid,
                            "endpoint": record.endpoint,
                            "content": record.content,
                        }
                    )
                )

    if cluster_role == ClusterRole.REPLICA:
        cluster.send_zmq_message(ClusterResponseType.FINISHED.value)
        return True

    # When the scan is complete we need to pull the domains back from all replicas db.
    # However if we're running as ClusterRole.SOURCE or ClusterRole.DISABLED then
    # we already have it in our database.
    return result_lookup.get(workload_uuid)


def run() -> None:
    """This initializes the business logic"""
    global NAMESERVERS

    # TODO: This updates every time now..
    if not args.nameservers and not args.resolve_list:
        logging.info("Updating DNS servers if there is a new update")
        original_dns_servers = dns_server_lookup.get_all()
        dns_servers = asyncio.run(pull_dns_servers(original_dns_servers))
        if dns_servers:
            dns_server_lookup.delete_all()
            for server in dns_servers:
                dns_server_lookup.save(server)
        dns_server_lookup.commit()

        NAMESERVERS = dns_server_lookup.get_all()

        logging.info("Got %s dns servers", len(NAMESERVERS))

    logging.debug("Getting domains from --input...")
    if not os.path.exists(input):
        logging.error("The path %s does not exist!", input)
        return None

    with open(input, encoding="utf-8") as file:
        lines = file.readlines()
        domains_loaded = [domain.strip() for domain in lines]

    # Get the sources notifications settings so we can send it to the replicas
    endpoints_from_database = []
    if not args.converter:
        endpoints_from_database = endpoints_lookup.get()

    workload_uuid = str(uuid.uuid4())

    workload_lookup = WorkloadLookup(session)
    workload_lookup.save(workload_uuid)

    logging.info("Using workload uuid %s", workload_uuid)

    if args.use_servers:
        if len(servers) == 0:
            logging.error(
                "You can not run Jericho with servers if the server list is empty"
            )
            sys.exit(1)
        else:
            thread = Thread(target=receiver, args=(cluster,))
            thread.start()

            asyncio.run(
                cluster.scatter(
                    workload_uuid,
                    configuration,
                    endpoints_from_database,
                    domains_loaded,
                    NAMESERVERS,
                    DNS_CACHE,
                    args.converter,
                )
            )

    if not args.use_servers or (args.use_servers and args.include_master):
        logging.info("Scraping domains from the %s", cluster_role)
        endpoints = []
        if not args.converter:
            endpoints = endpoints_lookup.get()
            if len(endpoints) == 0:
                logging.error("No endpoint patterns was supplied")
                return []

        # Split list
        execute(
            domains_loaded,
            workload_uuid,
            NAMESERVERS,
            configuration,
            rank=0,
            endpoints=endpoints,
            dns_cache=DNS_CACHE,
            converter=args.converter,
        )

    # Combine all of the replica results and save it to the ClusterRole.SOURCE database
    if cluster_role == ClusterRole.SOURCE:
        thread.join()
    else:
        logging.debug(
            "Skipping waiting on result because of cluster role %s", cluster_role
        )

    logging.info("Done!")


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

    if args.get_converter_output:
        get_converter_output(ConverterLookup(session))

    if args.upgrade:
        upgrade()

    if args.upgrade_all:
        upgrade()
        cluster.upgrade_servers(server_lookup.get())

    if args.version:
        get_version()

    if args.input is not None:
        run()

    if args.listen:
        cluster.listen_for_jobs(
            callback=execute, converter_lookup=ConverterLookup(session)
        )

    if args.delete_converter_result:
        converter_lookup = ConverterLookup(session)
        converter_lookup.delete_workload()
        print("OK")

    if args.get_last_workload_uuid:
        workload_lookup = WorkloadLookup(session)
        results = workload_lookup.get()
        if len(results) > 0:
            print(results[-1])

    if args.add_server:
        username = ""
        password = ""
        server = args.add_server
        if "@" in args.add_server:
            username = args.add_server.split("@")[0]
            server = args.add_server.split("@")[1]
            logging.info("Adding username %s to server ", username)

        if ":" in args.add_server:
            password = server.split(":")[1]
            server = server.split(":")[0]
            logging.info("Adding password %s to server", password)

        if not server in server_lookup.get():
            logging.info("Adding server %s to Jericho", server)
            server_lookup.save(server)
        else:
            logging.info("Not adding server %s because of duplicate", args.add_server)
            return False

        if username != "" and password != "":
            logging.info("Installing Jericho on %s", server)
            cloud = Cloud(provider=CustomServer(server, username, password))
            asyncio.run(cloud.setup(1))

    if args.remove_server:
        server_lookup.delete(args.remove_server)

    if args.remove_servers:
        for server in server_lookup.get():
            server_lookup.delete(server)

    if args.get_servers:
        for server in server_lookup.get():
            print(server)

    if args.setup_linodes:
        if not configuration.get("linode_token"):
            logging.error("Please specify a linode_token in your configuration file")
            return False

        cloud = Cloud(provider=Linode({"token": configuration.get("linode_token")}))

        if (
            len(asyncio.run(cloud.get_instances())) > 0
            and not args.ignore_cloud_duplicates
        ):
            logging.error(
                "Jericho instances is already created. To delete them use jericho --delete-linodes or run jericho --ignore-cloud-duplicates"
            )
            return False

        servers = asyncio.run(cloud.setup(args.setup_linodes))
        for server in servers:
            server_lookup.save(server)

        print(
            f"We have created {args.setup_linodes} linodes and installed Jericho. To use them run jericho --use-servers --input yourdomainlist.txt"
        )

    if args.delete_linodes:
        logging.info("Deleting linodes...")
        cloud = Cloud(provider=Linode({"token": configuration.get("linode_token")}))
        asyncio.run(cloud.delete_instances())
        logging.info("Done")

    if args.get_linodes:
        if not configuration.get("linode_token"):
            logging.error("Please specify a linode_token in your configuration file")
            return False

        cloud = Cloud(provider=Linode({"token": configuration.get("linode_token")}))

        resp = asyncio.run(cloud.get_instances(show_all=True))
        for instance in resp:
            print(instance)

        logging.info("Found %s Jericho instances", len(resp))

    if args.continue_workload:
        logging.info("Requesting the finished jobs")
        cluster.request_finished_jobs(args.continue_workload)
        receiver(cluster)
        logging.info("Receiver is done, exiting..")

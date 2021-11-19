import logging
import typing
import yaml
import math
from jericho.enums.cluster_roles import ClusterRole


def load_yaml_file(path: str) -> dict:
    """This parses a yaml file to a dict"""
    try:
        with open(path, "r", encoding="utf8") as stream:
            res = yaml.safe_load(stream)
            if isinstance(res, str):
                return {}

            return res
    except FileNotFoundError:
        logging.warning("Could not read file %s", path)

    return {}


def logger_convert(level: str) -> int:
    """
    Convert the log levels from the configuration to log levels the logging module can understand
    """
    levels = {
        "debug": 10,
        "info": 20,
        "warn": 30,
        "error": 40,
        "fatal": 50,
        "critical": 50,
    }
    return levels[level]


def add_missing_schemes_to_domain_list(domains: list) -> list:
    """The file could exist on the http vhost instead of the https vhost, so we check them both"""
    new_domain_list = []
    for domain in domains:
        domain = domain.replace("http://", "").replace("https://", "")

        if f"https://{domain}" not in new_domain_list:
            new_domain_list.append(f"https://{domain}")

        if f"http://{domain}" not in new_domain_list:
            new_domain_list.append(f"http://{domain}")

    return new_domain_list


def get_domain_from_endpoint(url: str) -> str:
    """Get the domain from a url"""
    url_parts = url.split("/")
    return f"{url_parts[0]}//{url_parts[2]}"


def parse_cluster_settings(rank: int, mpi_size: int) -> ClusterRole:
    """Parse the MPI settings to figure out if we are in a cluster and what cluster role"""
    # This is ran from a single machine, not a cluster
    if mpi_size == 1:
        return ClusterRole.DISABLED

    if rank == 0:
        return ClusterRole.MASTER

    return ClusterRole.SLAVE


def _chunks(lst: list, size: int) -> typing.Iterable:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def merge_array_to_iterator(
    endpoints: list, domains: list, domains_batch_size: int
) -> typing.Iterable:
    """Take a list of domains and endpoints and convert it to one iterable"""

    if len(endpoints) > len(domains):
        for domain in domains:
            endpoint_batches = _chunks(endpoints, domains_batch_size)
            for endpoint_batch in endpoint_batches:
                yield [
                    f'{domain}/{endpoint.get("endpoint").lstrip("/").rstrip("/")}'
                    for endpoint in endpoint_batch
                ]
    else:
        for endpoint in endpoints:
            domains_batches = _chunks(domains, domains_batch_size)

            for domain_batch in domains_batches:
                yield [
                    f'{domain}/{endpoint.get("endpoint").lstrip("/").rstrip("/")}'
                    for domain in domain_batch
                ]


def split_array_by(
    list_content: typing.List[str], num: int
) -> typing.List[typing.List[str]]:
    """Split a list by the num amount of chunks"""
    return [
        chunk for chunk in _chunks(list_content, math.ceil(len(list_content) / num))
    ]

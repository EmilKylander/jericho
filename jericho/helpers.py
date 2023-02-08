import logging
import typing
import yaml
import math
import os
import pwd
from urllib.parse import urlparse


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


def add_missing_schemes_to_domain(domain: str) -> str:
    """The file could exist on the http vhost instead of the https vhost, so we check them both"""
    if not "http://" in domain and not "https://" in domain:
        return f"http://{domain}"

    return domain


def get_domain_from_endpoint(url: str) -> str:
    """Get the domain from a url"""
    url_parts = url.split("/")
    return f"{url_parts[0]}//{url_parts[2]}"


def chunks(lst: list, size: int) -> typing.Iterable:
    """Yield successive n-sized chunks from lst."""
    if size == 0:
        yield []
    else:
        for i in range(0, len(lst), size):
            yield lst[i : i + size]


def merge_domains_with_endpoints(endpoints: list, domains: list) -> typing.Iterable:
    responses = []
    """Take a list of domains and endpoints and convert it to one iterable"""
    if len(endpoints) > len(domains):
        for domain in domains:
            for endpoint in endpoints:
                responses.append(
                    {'endpoint': f'{domain}{endpoint.get("endpoint")}', 'pattern': endpoint.get("pattern"), 'raw_endpoint': endpoint.get("endpoint")}
                )
    else:
        for endpoint in endpoints:
            for domain in domains:
                responses.append(
                    {'endpoint': f'{domain}{endpoint.get("endpoint")}', 'pattern': endpoint.get("pattern"), "raw_endpoint": endpoint.get("endpoint")}
                )

    return responses


def split_array_by(
    list_content: typing.List[str], num: int
) -> typing.List[typing.List[str]]:
    """Split a list by the num amount of chunks"""
    return [chunk for chunk in chunks(list_content, math.ceil(len(list_content) / num))]


def get_username() -> str:
    """Get the logged in users username"""
    return pwd.getpwuid(os.getuid())[0]


def is_not_same_domain(domain1: str, domain2: str) -> bool:
    return urlparse(domain1).netloc.replace("www.", "") != urlparse(
        domain2
    ).netloc.replace("www.", "")


def get_endpoint(domain):
    return urlparse(domain).path

def permutate_url_paths(rows):
    result_domains = []

    for row in rows:
        url_analyzed = urlparse(row)
        paths = urlparse(row).path.split("/")
        permutated_result = "/nonexistant404" + paths[len(paths)-1]
        del paths[len(paths)-1]
        permutated_result = url_analyzed.scheme + "://" + url_analyzed.netloc + "/".join(paths) + permutated_result
        result_domains.append(permutated_result)

    return result_domains
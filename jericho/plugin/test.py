from async_http import AsyncHTTP
from threaded_async_http import ThreadedAsyncHTTP
import yaml
import logging


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


configuration = load_yaml_file(f"/home/aces/jericho/configuration.yml")


async_http = AsyncHTTP()
threaded_async_http = ThreadedAsyncHTTP(async_http, 1, configuration)

threaded_async_http.start_bulk(["https://google.com", "https://yahoo.com"])
for url, html, headers in threaded_async_http.get_response():
    print(url)
threaded_async_http.close()

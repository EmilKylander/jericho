import logging
import typing
import asyncio
from jericho.helpers import get_domain_from_endpoint
from jericho.plugin.investigate import Investigate
from jericho.plugin.async_http import AsyncHTTP
from jericho.plugin.diff import Diff
from jericho.plugin.output_verifier import OutputVerifier
from jericho.repositories.result_lookup import ResultLookup
from jericho.repositories.cache_lookup import CacheLookup


class ResultRelevant:
    def __init__(
        self,
        investigate: Investigate,
        result_lookup: ResultLookup,
        cache_lookup: CacheLookup,
        async_http: AsyncHTTP,
        diff: Diff,
        output_verifier: OutputVerifier,
        configuration: dict,
    ):
        """Get objects through dependency injection"""
        self.investigate = investigate
        self.result_lookup = result_lookup
        self.cache_lookup = cache_lookup
        self.output_verifier = output_verifier
        self.async_http = async_http
        self.diff = diff
        self.configuration = configuration

    def _get_endpoint_from_url(self, url, endpoints):
        matched_endpoints = []
        for row in endpoints:
            if row["endpoint"].rstrip("/") in url.rstrip("/"):
                matched_endpoints.append(row["endpoint"])

        endpoint_found = max(matched_endpoints, key=len)
        for endpoint in endpoints:
            if endpoint["endpoint"] == endpoint_found:
                return endpoint["pattern"]

    def check(self, url: str, output: str, endpoints: typing.List) -> bool:
        """
        Identify if a result is relevant based if the result has been found before,
        and if the 404 page and the result is too similar, if it is then disregard it
        """
        domain = get_domain_from_endpoint(url)
        logging.debug(f"Running investigation on {url}")
        pattern = self._get_endpoint_from_url(url, endpoints)
        content_analysis = self.investigate.run(url, output, pattern)

        if not content_analysis:
            return False

        # Check if this url has been scanned before
        logging.debug(f"Checking if {url} has been scanned before")
        result_already_exist = True if self.result_lookup.find(url) else False
        if result_already_exist:
            return False

        (
            domain_is_found_in_404_cache,
            cache_content,
        ) = self.cache_lookup.find_domain(domain)

        # Check if the 404 page exists in the cache, else make a real time request
        logging.debug(f"Checking if {url} exists in cache..")
        if not domain_is_found_in_404_cache:
            logging.debug(
                "Could not find %s in cache, sending a request..",
                f"{domain}/page_not_found.html",
            )
            loop = asyncio.get_event_loop()
            page_not_found_res = loop.run_until_complete(
                self.async_http.get(
                    [f"{domain}/page_not_found.html"],
                    settings={
                        "timeout": 60,
                        "headers": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
                        },
                    },
                ),
            )
            if len(page_not_found_res) == 0:
                logging.debug(
                    "Could not get a 404 page for %s", f"{domain}/page_not_found"
                )
                return False

            _, cache_content = page_not_found_res[0]

            self.cache_lookup.save_content(domain, cache_content)
        else:
            logging.debug(
                "Using 404 page %s from cache", f"{domain}/page_not_found.html"
            )

        # Check if the content type of the result is the same as the "not found" page
        not_found_page_content_analysis = self.output_verifier.find_content_type(
            cache_content
        )

        # Check how much the result content and the 404 content differ in percentage
        result_and_404_too_different = False
        if (
            not_found_page_content_analysis == pattern
            and pattern not in self.output_verifier.formats()
        ):
            logging.debug(f"Analyzing the text difference for url {url}")
            result_and_404_content_procent_diff = self.diff.check(output, cache_content)
            logging.debug(
                "We analyzed the text difference between endpoint %s and a 404 page. Difference: %s%%",
                url,
                result_and_404_content_procent_diff,
            )

            # Check if the percentage difference between the result
            # and the 404 page is larger than acceptable
            if result_and_404_content_procent_diff <= self.configuration.get(
                "max_result_and_404_percent_diff"
            ):
                logging.debug(
                    "Skipping analyzing content for %s because the difference in content is %s%%",
                    url,
                    result_and_404_content_procent_diff,
                )
                result_and_404_too_different = True
        else:
            logging.debug(
                f"The result content type was {pattern} for {url} and the 'not found' page content type was {not_found_page_content_analysis}, skipping comparing them"
            )

        if not result_and_404_too_different:
            logging.info(f"Found endpoint {url}")

        return not result_and_404_too_different

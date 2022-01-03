import logging
import typing
import uuid
from jericho.helpers import get_domain_from_endpoint
from jericho.plugin.investigate import Investigate
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
        diff: Diff,
        output_verifier: OutputVerifier,
        configuration: dict,
        workload_uuid: uuid.uuid4,
    ):
        """Get objects through dependency injection"""
        self.investigate = investigate
        self.result_lookup = result_lookup
        self.cache_lookup = cache_lookup
        self.output_verifier = output_verifier
        self.diff = diff
        self.configuration = configuration
        self.workload_uuid = workload_uuid

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
        logging.debug("Running investigation on %s", url)
        pattern = self._get_endpoint_from_url(url, endpoints)
        content_analysis = self.investigate.run(url, output, pattern)

        if not content_analysis:
            return False

        # Check if this url has been scanned before
        logging.debug("Checking if %s has been scanned before", url)

        if self.result_lookup.find(self.workload_uuid, url):
            return False

        # The 404 page is always saved when we save potential results
        _, cache_content = self.cache_lookup.find_domain(domain)

        # Check if the content type of the result is the same as the "not found" page
        not_found_page_content_analysis = self.output_verifier.find_content_type(
            cache_content
        )

        logging.debug("pattern: %s", pattern)
        logging.debug("404 content type: %s", not_found_page_content_analysis)

        # Check if the pattern type is the same on result and 404 page, but only if it's a content type and not a search string
        result_and_404_too_different = False
        if (
            not_found_page_content_analysis == pattern
            and pattern not in self.output_verifier.formats()
        ):
            logging.debug(
                "The result content type was %s for %s and the 'not found' page content type was %s, skipping comparing them",
                pattern,
                url,
                not_found_page_content_analysis,
            )
            return False

        logging.debug("Analyzing the text difference for url %s", url)
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

        if not result_and_404_too_different:
            logging.info("Found endpoint %s", url)

        return not result_and_404_too_different

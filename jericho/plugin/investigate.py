#!/bin/python3
import logging
from jericho.plugin.output_verifier import OutputVerifier


class Investigate:
    def __init__(self, endpoints_lookup):
        """Setup some default values"""
        self.endpoints_lookup = endpoints_lookup
        self.output_verifier = OutputVerifier()
        self.blacklisted_words = [
            "access denied",
            "not found",
            "unauthorized",
            "error 404",
            "error 403",
            "does not exist",
            "deny_pc",
            "the requested url was rejected",
        ]
        self.blacklisted_content = [
            "forbidden",
            "ok",
            "{}",
            "invalid request!",
            "400 bad request",
            "404",
            "",
        ]

    def run(self, url: str, content: str) -> bool:
        """
        Analyze if the content is relevant based on lack of blacklisted words and phrases.
        If we have content type patterns we should use it, otherwise check if the string exists
        """
        logging.debug("Lowercasing content for url {url}")
        content = content.lower().strip()

        # These responses are irrelevant and come from unexpected blocks, misconfigured 404s etc
        logging.debug("Checking for blacklisted content")
        for blacklisted_content in self.blacklisted_content:
            if blacklisted_content == content:
                logging.info("Found %s in %s, skipping..", blacklisted_content, url)
                return False

        # Check if it contains blacklisted words
        logging.debug("Checking for blacklisted words")
        for word in self.blacklisted_words:
            if word in content:
                return False

        logging.debug("Getting the patterns")
        endpoints_objects = self.endpoints_lookup.get()
        endpoints = {}
        matched_endpoints = []
        for row in endpoints_objects:
            endpoints[row["endpoint"]] = row["pattern"]
            if row["endpoint"] in url:
                matched_endpoints.append(row["endpoint"])

        endpoint = max(matched_endpoints, key=len)
        pattern = endpoints[endpoint]
        if pattern in self.output_verifier.formats():
            logging.debug(f"Checking for pattern {pattern} in {url} content")
            result = self.output_verifier.verify(content, pattern)
            logging.info(
                "Tested if url %s is %s - evaluated to %s", url, pattern, result
            )
            return result

        logging.info("Checking if pattern exist in content for url %s", url)
        return pattern in content

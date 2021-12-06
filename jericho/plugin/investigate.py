#!/bin/python3
import logging
import typing
from jericho.plugin.output_verifier import OutputVerifier


class Investigate:
    def __init__(self):
        """Setup some default values"""
        self.output_verifier = OutputVerifier()
        self.exclude_words = [
            "access denied",
            "not found",
            "unauthorized",
            "error 404",
            "error 403",
            "does not exist",
            "deny_pc",
            "the requested url was rejected",
        ]
        self.exclude_content = [
            "forbidden",
            "ok",
            "{}",
            "invalid request!",
            "400 bad request",
            "404",
            "",
        ]

    def run(self, url: str, content: str, pattern: str) -> bool:
        """
        Analyze if the content is relevant based on lack of excluded words and phrases.
        If we have content type patterns we should use it, otherwise check if the string exists
        """
        logging.debug(f"Lowercasing content for url {url}")
        content = content.lower().strip()

        # These responses are irrelevant and come from unexpected blocks, misconfigured 404s etc
        logging.debug("Checking for excluded content")
        for excluded_content in self.exclude_content:
            if excluded_content == content:
                logging.debug("Found %s in %s, skipping..", excluded_content, url)
                return False

        # Check if it contains excluded words
        logging.debug("Checking for excluded words")
        for word in self.exclude_words:
            if word in content:
                return False

        # Check for text string as pattern
        if pattern not in self.output_verifier.formats():
            return pattern in content

        # Check if it matches the pattern
        if pattern in self.output_verifier.formats():
            logging.debug(f"Checking for pattern {pattern} in {url} content")
            result = self.output_verifier.verify(content, pattern)
            logging.debug(
                "Tested if url %s is %s - evaluated to %s", url, pattern, result
            )
            return result

        logging.debug("Checking if pattern exist in content for url %s", url)
        return False

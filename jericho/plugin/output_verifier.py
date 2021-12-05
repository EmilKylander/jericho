"""Output Verifier

This script is suppose to be run as a module and its
purpose is to validate if a string is really the intended
format that we expect it to be.

"""
#!/bin/python3
import logging
import json
import yaml
from bs4 import BeautifulSoup
from jericho.enums.pattern_types import PatternTypes

standard_html_tags = [
    "a",
    "abbr",
    "address",
    "area",
    "article",
    "aside",
    "audio",
    "b",
    "base",
    "bdi",
    "bdo",
    "blockquote",
    "body",
    "br",
    "button",
    "canvas",
    "caption",
    "cite",
    "code",
    "col",
    "colgroup",
    "data",
    "datalist",
    "dd",
    "del",
    "details",
    "dfn",
    "dialog",
    "div",
    "dl",
    "dt",
    "em",
    "embed",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "head",
    "header",
    "hgroup",
    "hr",
    "html",
    "i",
    "iframe",
    "img",
    "input",
    "ins",
    "kbd",
    "label",
    "legend",
    "li",
    "link",
    "main",
    "map",
    "mark",
    "math",
    "menu",
    "menuitem",
    "meta",
    "meter",
    "nav",
    "noscript",
    "object",
    "ol",
    "optgroup",
    "option",
    "output",
    "p",
    "param",
    "picture",
    "pre",
    "progress",
    "q",
    "rb",
    "rp",
    "rt",
    "rtc",
    "ruby",
    "samp",
    "script",
    "section",
    "select",
    "slot",
    "small",
    "source",
    "span",
    "strong",
    "style",
    "sub",
    "summary",
    "sup",
    "svg",
    "table",
    "tbody",
    "td",
    "template",
    "textarea",
    "tfoot",
    "th",
    "thead",
    "time",
    "title",
    "tr",
    "track",
    "u",
    "ul",
    "var",
    "video",
    "wbr",
]


class OutputVerifier:
    """This class attempts to identify what type of document a string is"""

    def __init__(self):
        """Setup which HTML tags are standard"""
        self.standard_html_tags = standard_html_tags

    def _is_json(self, content: str) -> bool:
        """Private method to attempt a json parse"""
        print(content[0])
        if content[0] != "{":
            return False

        return True

    def _is_yaml(self, content: str) -> bool:
        """Private method to figure out if a string is yaml"""
        if self._is_html(content) or self._is_xml(content) or self._is_json(content):
            return False

        if not ":" in content:
            return False

        try:
            yaml.safe_load(content)
        except yaml.YAMLError:
            return False

        return True

    def _is_html(self, content: str) -> bool:
        """Private method to identify if a string is HTML"""
        content = content.lower()
        if "<html" in content or "<!doctype html" in content:
            return True

        if "<?xml" in content:
            return False

        soup = BeautifulSoup(content, "html.parser")
        found_tags = [tag.name for tag in soup.find_all()]
        for found_tag in found_tags:
            if found_tag in self.standard_html_tags:
                return True

        return False

    def _is_xml(self, content: str) -> bool:
        """Private method to identify if a string is XML"""
        content = content.lower()
        if "<html" in content or "<!doctype html" in content:
            return False

        if not "<?xml" in content:
            return False

        return True

    def _is_no_spaces(self, content: str) -> bool:
        """Private method to check if a string has no spaces (Good for e.g .env files)"""
        lines = content.split("\n")
        for line in lines:
            if "#" in line:
                continue
            if " " in line.strip():
                return False

        return True

    def _is_text(self, content: str) -> bool:
        if self._is_json(content):
            return False

        if self._is_yaml(content):
            return False

        if self._is_html(content):
            return False

        if self._is_xml(content):
            return False

        return True

    def formats(self):
        """Return type content types that we can match against"""
        return [e.value for e in PatternTypes]

    def find_content_type(self, content: str) -> str:
        logging.debug("Checking if content is JSON")
        if self._is_json(content):
            return PatternTypes.JSON.value

        logging.debug("Checking if content is YML")
        if self._is_yaml(content):
            return PatternTypes.YML.value

        logging.debug("Checking if content is XML")
        if self._is_xml(content):
            return PatternTypes.XML.value

        logging.debug("Checking if content is TEXT")
        if self._is_text(content):
            return PatternTypes.TEXT.value

        logging.debug("Checking if content is NO_SPACES")
        if self._is_no_spaces(content):
            return PatternTypes.NO_SPACES.value

        logging.debug("Checking if content is HTML")
        if self._is_html(content):
            return PatternTypes.HTML.value

        return ""

    def verify(self, content: str, pattern: str) -> bool:
        """Verify that if a string is relevant based on our pattern"""
        if pattern == PatternTypes.JSON.value:
            logging.debug("Checking if content is json")
            return self._is_json(content)

        if pattern == PatternTypes.YML.value:
            logging.debug("Checking if content is yml")
            return self._is_yaml(content)

        if pattern == PatternTypes.XML.value:
            logging.debug("Checking if content is xml")
            return self._is_xml(content)

        if pattern == PatternTypes.TEXT.value:
            logging.debug("Checking if <html> does not exist in content")
            return self._is_text(content)

        if pattern == PatternTypes.NO_SPACES.value:
            logging.debug("Checking if space does not exist in content")
            return self._is_no_spaces(content)

        if pattern == PatternTypes.HTML.value:
            logging.debug("Checking if space does not exist in content")
            return self._is_html(content)

        logging.error("We got a pattern that we did not expect: %s", pattern)
        return False

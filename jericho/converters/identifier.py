#!/bin/python3
import logging
import typing
import html2text
import re
import gc
import html
import validators
from bs4 import BeautifulSoup
from validate_email import validate_email
import urllib.parse
import cchardet
from Wappalyzer import Wappalyzer, WebPage
from jericho.enums.link_prefixes import LinkPrefixes

class Identifier:
    def _get_text(self, url: str, site_html: str) -> str:
        logging.debug("Getting the raw text")
        try:
            h = html2text.HTML2Text()
            h.ignore_links = True
            h.ignore_images = True
            return (
                h.handle(site_html)
                .replace("\n", " ")
                .replace("\r", "")
                .replace("*", "")
                .replace("#", "")
                .replace("_", "")
                .strip()
            )
        except Exception as err:
            logging.warning(f"Could not get text from {url} because of error {err}")
            return ""

    def _get_description(self, url: str, soup: BeautifulSoup) -> str:
        logging.debug("Getting the description")
        description = soup.find("meta", attrs={"name": "description"})

        if not description:
            return ""

        try:
            return html.unescape(
                description["content"].replace("\n", "").replace("\r", "")
            )
        except Exception as err:
            logging.warning(
                f"Could not get the meta description from {url} because of error {err}"
            )
            return ""

    def _get_contact_info(self, soup: BeautifulSoup) -> dict:
        logging.debug("Getting the contact info")

        links = soup.find_all("a")
        emails = []
        phones = []

        for link in links:
            current_link = link.get("href", "")

            if "?" in current_link:
                current_link = current_link.split("?")[0]

            if LinkPrefixes.PHONE.value in current_link:
                phones.append(current_link.replace(LinkPrefixes.PHONE.value, ""))
            elif LinkPrefixes.MAIL.value in current_link:
                parsed = validate_email(current_link.replace(LinkPrefixes.MAIL.value, ""))
                if parsed:
                    emails.append(current_link.replace(LinkPrefixes.MAIL.value, ""))

        return {"phones": list(set(phones)), "emails": list(set(emails))}

    def _get_title(self, site_html: str) -> str:
        logging.debug("Getting the title")
        title = ""
        pat = re.compile("<title>(.*?)<\\/title>")

        get_title = pat.search(site_html.replace("\n", "").replace("\r", "").lower())
        if get_title:
            title = html.unescape(get_title.group(1))

        return title

    def _get_google_tracking_code(self, html: str) -> str:
        logging.debug("Getting the google analytics code")
        tracking_code = re.findall(r"ga\('create', '(.*)', 'auto'\);", html)
        if tracking_code:
            return tracking_code[0]

        tracking_code_alt = re.findall(r"'_setAccount','(.*?)'", html)
        if tracking_code_alt:
            return tracking_code_alt[0]

        return ""

    def _get_domains(self, soup: BeautifulSoup) -> typing.List[str]:
        logging.debug("Getting the domains")
        links = [a.get("href") for a in soup.find_all("a", href=True)]
        domains = []
        for link in links:
            if not validators.url(link):
                continue

            parsed_uri = urllib.parse.urlsplit(link)
            if parsed_uri.scheme == "http" or parsed_uri.scheme == "https":
                domains.append(parsed_uri.scheme + "://" + parsed_uri.netloc)

        return list(set(domains))

    def _get_technologies(
        self, url: str, site_html: str, headers: dict, wappalyzer: Wappalyzer
    ) -> typing.List[dict]:
        techs = []
        webpage = WebPage(url, site_html, headers)
        for technology, info in wappalyzer.analyze_with_versions_and_categories(
            webpage
        ).items():
            version = ""
            if len(info.get("versions")) > 0:
                version = info.get("versions")[0]
            techs.append(
                {
                    "technology": technology,
                    "version": version,
                    "theme": "",
                    "plugins": "",
                }
            )

        return techs

    def run(
        self, ip: str, url: str, status: int, headers: dict, site_html: str
    ) -> dict:
        wappalyzer = Wappalyzer.latest()

        soup = BeautifulSoup(site_html, "lxml")
        contact_info = self._get_contact_info(soup)
        techs = self._get_technologies(url, site_html, headers, wappalyzer)
        headers = "\n".join([f"{key}: {val}" for key, val in headers.items()])

        soup.decompose()
        del wappalyzer
        gc.collect()

        return {
            "status": status,
            "headers": headers,
            "domain": url,
            "tech": techs,
            "domains_found": self._get_domains(soup),
            "title": self._get_title(site_html),
            "description": self._get_description(url, soup),
            "phones": contact_info.get("phones"),
            "emails": contact_info.get("emails"),
            "ip": ip,
            "google_tracking_code": self._get_google_tracking_code(site_html),
            "text_content": self._get_text(url, site_html),
            "bytes": len(site_html),
        }

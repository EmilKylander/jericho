#!/bin/python3
import logging
from sqlalchemy import delete
from jericho.models import Jericho404Cache


class CacheLookup:
    def __init__(self, session):
        self.session = session

    def find_url(self, url: str) -> tuple:
        """Check if a domain exist and if so get the content"""
        content = (
            self.session.query(Jericho404Cache)
            .filter(Jericho404Cache.url == url)
            .first()
        )

        if not content:
            return False, ""

        return True, content.content

    def save_content(self, domain: str, content: str) -> bool:
        """Save the content of a domain"""
        try:
            cache = Jericho404Cache(domain=domain, content=content)
            self.session.add(cache)
            self.session.commit()
            return True
        except Exception as err:
            logging.warning(
                "Could not save content for %s because of error %s", domain, err
            )
            self.session.rollback()
            return False

    def delete(self, url: str) -> bool:
        """Delete a domain from our database"""
        try:
            self.session.execute(
                delete(Jericho404Cache).where(Jericho404Cache.url == url)
            )
            return True
        except Exception as err:
            logging.warning(
                "Could not delete the cache entry %s because of error %s", url, err
            )
            self.session.rollback()
            return False

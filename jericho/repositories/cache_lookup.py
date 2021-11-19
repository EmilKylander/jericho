#!/bin/python3
import logging
from sqlalchemy import delete
from jericho.models import Jericho404Cache


class CacheLookup:
    def __init__(self, session):
        self.session = session

    def find_domain(self, domain: str) -> tuple:
        """Check if a domain exist and if so get the content"""
        content = (
            self.session.query(Jericho404Cache)
            .filter(Jericho404Cache.domain == domain)
            .all()
        )

        if len(content) == 0:
            return False, ""

        return True, content[0].content

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
            return False

    def delete(self, domain: str) -> bool:
        """Delete a domain from our database"""
        try:
            self.session.execute(
                delete(Jericho404Cache).where(Jericho404Cache.domain == domain)
            )
            return True
        except Exception as err:
            logging.warning(
                "Could not delete the cache entry %s because of error %s", domain, err
            )
            self.session.rollback()
            return False

import unittest
import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jericho.models import *
from jericho.repositories.dns_cache_lookup import DnsCacheLookup
from sqlalchemy.ext.declarative import declarative_base


engine = create_engine("sqlite:///:memory:", echo=True)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


async def test_save_result():
    dns_cache_lookup = DnsCacheLookup(session)
    await dns_cache_lookup.connect_db()

    save = await dns_cache_lookup.save("https://example.com", "1.2.3.4")
    assert save is True
    find = await dns_cache_lookup.find_ip("https://example.com") == '1.2.3.4'
    assert find == True
    await dns_cache_lookup.close()
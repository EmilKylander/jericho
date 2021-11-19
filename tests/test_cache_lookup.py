import unittest
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jericho.models import *
from jericho.repositories.cache_lookup import CacheLookup
from sqlalchemy.ext.declarative import declarative_base


engine = create_engine("sqlite:///:memory:", echo=True)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


def test_get_content_from_domain():
    cache_lookup = CacheLookup(session)
    cache_lookup.save_content("https://test.com", "testing content here")
    assert cache_lookup.find_domain("https://test.com") == (
        True,
        "testing content here",
    )


def test_save_big_content():
    cache_lookup = CacheLookup(session)
    one_mb_content = "A" * 1048576
    save = cache_lookup.save_content("https://test1.com", one_mb_content)
    assert save is True


def test_fail_gracefully_on_duplicate_domain():
    cache_lookup = CacheLookup(session)
    save = cache_lookup.save_content("https://test2.com", "hello")
    save = cache_lookup.save_content("https://test2.com", "there")
    assert save is False

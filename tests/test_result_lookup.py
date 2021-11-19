import unittest
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jericho.models import *
from jericho.repositories.result_lookup import ResultLookup
from sqlalchemy.ext.declarative import declarative_base


engine = create_engine("sqlite:///:memory:", echo=True)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


def test_save_result():
    result_lookup = ResultLookup(session)
    save = result_lookup.save("https://example.com", "contenthere")
    assert save is True
    assert result_lookup.find("https://example.com") is True


def test_save_result():
    result_lookup = ResultLookup(session)
    save = result_lookup.save("https://example.com", "contenthere")
    assert save is True
    assert result_lookup.find("https://example.com") is True


def test_delete_all_result():
    result_lookup = ResultLookup(session)
    result_lookup.save("https://example1.com", "contenthere")
    result_lookup.delete_all()
    assert result_lookup.find("https://example.com") is False

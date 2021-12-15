import unittest
import pytest
import uuid
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
    workload_uuid = str(uuid.uuid4())
    save = result_lookup.save(workload_uuid, "https://example.com", "contenthere")
    assert save is True
    assert result_lookup.find(workload_uuid, "https://example.com") is True


def test_save_result():
    result_lookup = ResultLookup(session)
    workload_uuid = str(uuid.uuid4())

    save = result_lookup.save(workload_uuid, "https://example.com", "contenthere")
    assert save is True
    assert result_lookup.find(workload_uuid, "https://example.com") is True


def test_delete_all_result():
    result_lookup = ResultLookup(session)
    workload_uuid = str(uuid.uuid4())

    result_lookup.save(workload_uuid, "https://example.com", "contenthere")
    result_lookup.delete_all()
    assert result_lookup.find(workload_uuid, "https://example.com") is False
    assert result_lookup.get(workload_uuid) == []

def test_delete_all_workload_uuid():
    result_lookup = ResultLookup(session)
    workload_uuid = str(uuid.uuid4())

    result_lookup.save(workload_uuid, "https://example.com", "contenthere")
    result_lookup.delete_workload(workload_uuid)
    assert result_lookup.find(workload_uuid, "https://example.com") is False
    assert result_lookup.get(workload_uuid) == []

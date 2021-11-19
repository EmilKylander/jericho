import unittest
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jericho.models import *
from jericho.repositories.endpoints_lookup import EndpointsLookup
from sqlalchemy.ext.declarative import declarative_base


engine = create_engine("sqlite:///:memory:", echo=True)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


def test_get_endpoints():
    endpoints_lookup = EndpointsLookup(session)
    endpoints_lookup.save_all([{"endpoint": "/phpinfo.php", "pattern": "phpinfo"}])
    assert endpoints_lookup.get() == [
        {"endpoint": "/phpinfo.php", "pattern": "phpinfo"}
    ]


def test_delete_endpoints():
    endpoints_lookup = EndpointsLookup(session)
    endpoints_lookup.save_all([{"endpoint": "/phpinfo.php", "pattern": "phpinfo"}])
    endpoints_lookup.delete_all()
    assert endpoints_lookup.get() == []

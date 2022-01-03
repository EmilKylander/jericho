import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jericho.models import *
from jericho.repositories.dns_server_lookup import DnsServerLookup
from sqlalchemy.ext.declarative import declarative_base


engine = create_engine("sqlite:///:memory:", echo=True)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


def test_get_all():
    dns_server_lookup = DnsServerLookup(session)

    dns_server_lookup.save("8.8.8.8")
    dns_server_lookup.save("8.8.4.4")

    assert dns_server_lookup.get_all() == ["8.8.8.8", "8.8.4.4"]


def test_delete_all():
    dns_server_lookup = DnsServerLookup(session)

    dns_server_lookup.save("8.8.8.8")
    dns_server_lookup.save("8.8.4.4")
    dns_server_lookup.delete_all()

    assert dns_server_lookup.get_all() == []

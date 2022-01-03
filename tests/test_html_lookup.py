import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jericho.models import *
from jericho.repositories.html_lookup import HtmlLookup
from sqlalchemy.ext.declarative import declarative_base


engine = create_engine("sqlite:///:memory:", echo=True)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


def test_get_all():
    html_lookup = HtmlLookup(session)
    session.execute(
        """INSERT INTO jericho_html(workload_uuid, endpoint, content, headers) VALUES('1234-1234-1234-1234', 'https://google.com', 'neat content', '{"test": "testing"}')"""
    )
    session.commit()

    for res in html_lookup.get_all(workload_uuid="1234-1234-1234-1234"):
        assert res[0].workload_uuid == "1234-1234-1234-1234"
        assert res[0].endpoint == "https://google.com"
        assert res[0].content == "neat content"
        assert res[0].headers == '{"test": "testing"}'

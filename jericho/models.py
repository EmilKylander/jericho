from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.sql import func

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class JerichoEndpoints(Base):
    __tablename__ = "jericho_endpoints"

    endpoint = Column(String(255))
    pattern = Column(Text)
    is_checked = Column(Integer)
    id = Column(Integer, autoincrement=True, primary_key=True)


class Jericho404Cache(Base):
    __tablename__ = "jericho_404_caches"
    __table_args__ = {"extend_existing": True}

    domain = Column(String(255), primary_key=True)
    content = Column(Text)


class JerichoProgress(Base):
    __tablename__ = "jericho_progress"

    key = Column(String(255), primary_key=True)
    value = Column(String(255))

class JerichoResult(Base):
    __tablename__ = "jericho_result"

    workload_uuid = Column(String(36), primary_key=True)
    endpoint = Column(String(255))
    content = Column(Text)
    time_created = Column(DateTime(timezone=True), server_default=func.now())

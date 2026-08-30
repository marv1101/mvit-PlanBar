import pytest
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeMeta, declarative_base, sessionmaker

from app.utils.pagination import paginate

Base: DeclarativeMeta = declarative_base()


class SampleItem(Base):
    __tablename__ = "sample_items"
    id = Column(Integer, primary_key=True)
    name = Column(String)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    for i in range(25):
        session.add(SampleItem(name=f"Item {i + 1}"))
    session.commit()
    yield session
    session.close()


def test_paginate_first_page(db_session):
    query = db_session.query(SampleItem).order_by(SampleItem.id)
    items, pagination = paginate(query, page=1, page_size=10)
    assert len(items) == 10
    assert pagination.total == 25
    assert pagination.page == 1
    assert pagination.page_size == 10
    assert pagination.total_pages == 3


def test_paginate_last_page(db_session):
    query = db_session.query(SampleItem).order_by(SampleItem.id)
    items, pagination = paginate(query, page=3, page_size=10)
    assert len(items) == 5
    assert pagination.page == 3


def test_paginate_page_out_of_range_clamps(db_session):
    query = db_session.query(SampleItem).order_by(SampleItem.id)
    items, pagination = paginate(query, page=99, page_size=10)
    assert len(items) == 5
    assert pagination.page == 3


def test_paginate_page_below_one_clamps(db_session):
    query = db_session.query(SampleItem).order_by(SampleItem.id)
    items, pagination = paginate(query, page=0, page_size=10)
    assert len(items) == 10
    assert pagination.page == 1


def test_paginate_empty_table():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    query = session.query(SampleItem).order_by(SampleItem.id)
    items, pagination = paginate(query)
    assert len(items) == 0
    assert pagination.total == 0
    assert pagination.page == 1
    assert pagination.total_pages == 1
    session.close()


def test_paginate_default_page_size(db_session):
    query = db_session.query(SampleItem).order_by(SampleItem.id)
    items, pagination = paginate(query)
    assert len(items) == 20
    assert pagination.page_size == 20

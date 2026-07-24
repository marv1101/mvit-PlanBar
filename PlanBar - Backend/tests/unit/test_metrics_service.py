import pytest
from app.db.base import Base
from app.db.models.schedule import Schedule
from app.services.metrics_service import get_aggregated_metrics, get_robustness_metrics
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()

    s1 = Schedule(
        name="S1",
        status="completed",
        metrics_json={"solveTimeSeconds": 10.5, "wishFulfillmentRate": 0.85},
    )
    s2 = Schedule(
        name="S2",
        status="completed",
        metrics_json={"solveTimeSeconds": 5.2, "wishFulfillmentRate": 0.92},
    )
    s3 = Schedule(name="S3", status="completed", metrics_json={"solveTimeSeconds": 8.0})
    s4 = Schedule(name="S4", status="failed")
    s5 = Schedule(name="S5", status="draft")
    session.add_all([s1, s2, s3, s4, s5])
    session.commit()
    yield session
    session.close()


def test_get_aggregated_metrics(db_session):
    metrics = get_aggregated_metrics(db_session)
    assert metrics["total_schedules"] == 3
    assert metrics["completed_schedules"] == 2
    assert metrics["average_solve_time"] == pytest.approx(7.9, rel=0.1)
    assert metrics["average_wish_fulfillment_rate"] == pytest.approx(0.885, rel=0.01)
    assert metrics["failed_schedules"] == 1
    assert metrics["draft_schedules"] == 1


def test_get_aggregated_metrics_all_draft():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    session.add(Schedule(name="Draft", status="draft"))
    session.commit()

    metrics = get_aggregated_metrics(session)
    assert metrics["total_schedules"] == 0
    assert metrics["completed_schedules"] == 0
    assert metrics["average_solve_time"] == 0.0
    assert metrics["average_wish_fulfillment_rate"] == 0.0
    session.close()


def test_get_robustness_metrics(db_session):
    metrics = get_robustness_metrics(db_session)
    assert metrics["total_completed"] == 3
    assert metrics["total_optimal"] == 0


def test_get_robustness_metrics_with_optimal():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    s1 = Schedule(name="Optimal", status="completed", diagnostics_json={"isOptimal": True})
    s2 = Schedule(name="NotOptimal", status="completed", diagnostics_json={"isOptimal": False})
    session.add_all([s1, s2])
    session.commit()

    metrics = get_robustness_metrics(session)
    assert metrics["total_completed"] == 2
    assert metrics["total_optimal"] == 1
    assert metrics["optimal_rate"] == 50.0
    session.close()


def test_get_robustness_metrics_no_completed():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    metrics = get_robustness_metrics(session)
    assert metrics["total_completed"] == 0
    assert metrics["total_optimal"] == 0
    assert metrics["optimal_rate"] == 0.0
    session.close()

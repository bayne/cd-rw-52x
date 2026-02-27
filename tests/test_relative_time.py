"""Unit tests for cdrw.relative_time."""

from datetime import datetime, timedelta

import pytest

from cdrw.relative_time import relative_time


def _ago(seconds: float) -> datetime:
    return datetime.now() - timedelta(seconds=seconds)


def test_just_now_zero():
    assert relative_time(_ago(0)) == "just now"


def test_just_now_under_minute():
    assert relative_time(_ago(45)) == "just now"


def test_minutes():
    assert relative_time(_ago(90)) == "1m ago"
    assert relative_time(_ago(3599)) == "59m ago"


def test_hours():
    assert relative_time(_ago(3600)) == "1h ago"
    assert relative_time(_ago(7200)) == "2h ago"
    assert relative_time(_ago(86399)) == "23h ago"


def test_days():
    assert relative_time(_ago(86400)) == "1d ago"
    assert relative_time(_ago(86400 * 10)) == "10d ago"


def test_months():
    assert relative_time(_ago(86400 * 35)) == "1mo ago"
    assert relative_time(_ago(86400 * 60)) == "2mo ago"


def test_years():
    assert relative_time(_ago(86400 * 400)) == "1y ago"
    assert relative_time(_ago(86400 * 730)) == "2y ago"


def test_future_returns_just_now():
    future = datetime.now() + timedelta(seconds=60)
    assert relative_time(future) == "just now"

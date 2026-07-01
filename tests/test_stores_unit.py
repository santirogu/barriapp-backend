"""Unit tests for store search-criteria building and query parsing (no DB)."""

import pytest
from beanie import PydanticObjectId

from app.core.errors import AppError
from app.stores.models import StoreStatus
from app.stores.repository import build_search_criteria
from app.stores.router import _parse_near, _parse_object_id


@pytest.mark.req("S-4")
def test_criteria_excludes_suspended_and_has_no_geo_by_default() -> None:
    criteria = build_search_criteria()
    assert criteria["status"] == {"$ne": StoreStatus.SUSPENDED.value}
    assert "location.geo" not in criteria


@pytest.mark.req("S-4")
def test_criteria_with_near_adds_geo_clause() -> None:
    criteria = build_search_criteria(near=(-74.0, 4.6), radius_meters=1500)
    near_clause = criteria["location.geo"]["$near"]
    assert near_clause["$geometry"] == {"type": "Point", "coordinates": [-74.0, 4.6]}
    assert near_clause["$maxDistance"] == 1500


@pytest.mark.req("S-6")
def test_criteria_with_category_and_query() -> None:
    cid = PydanticObjectId()
    criteria = build_search_criteria(category_id=cid, query="arroz")
    assert criteria["category_ids"] == cid
    assert criteria["name"] == {"$regex": "arroz", "$options": "i"}


@pytest.mark.req("S-4")
def test_parse_near_valid_and_none() -> None:
    assert _parse_near("-74.08,4.61") == (-74.08, 4.61)
    assert _parse_near(None) is None


@pytest.mark.req("S-4")
@pytest.mark.parametrize("bad", ["1.0", "a,b", "1,2,3", ""])
def test_parse_near_invalid_raises_422(bad: str) -> None:
    if bad == "":
        # empty string is treated as "not provided"
        assert _parse_near(bad) is None
        return
    with pytest.raises(AppError) as exc:
        _parse_near(bad)
    assert exc.value.status_code == 422


@pytest.mark.req("S-4")
def test_parse_object_id() -> None:
    oid = PydanticObjectId()
    assert _parse_object_id(str(oid), "category") == oid
    assert _parse_object_id(None, "category") is None
    with pytest.raises(AppError) as exc:
        _parse_object_id("not-an-object-id", "category")
    assert exc.value.status_code == 422

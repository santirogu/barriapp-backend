"""Unit tests for single-role registration: age gate and per-role schema shape."""

from datetime import date

import pytest
from pydantic import TypeAdapter, ValidationError

from app.auth.logic import calculate_age, is_adult
from app.auth.schemas import RegisterRequest
from app.users.models import Role

_adapter = TypeAdapter(RegisterRequest)


def _base(role: str) -> dict[str, object]:
    return {
        "role": role,
        "first_name": "Ana",
        "last_name": "Pérez",
        "document_type": "CC",
        "document_number": "123456",
        "phone": "+573001112233",
        "email": "ana@barriapp.co",
        "password": "supersecret",
        "accept_habeas_data": True,
    }


@pytest.mark.req("A-1")
def test_calculate_age_before_and_after_birthday() -> None:
    assert calculate_age(date(2000, 6, 15), date(2018, 6, 15)) == 18
    assert calculate_age(date(2000, 6, 15), date(2018, 6, 14)) == 17
    assert is_adult(date(2000, 1, 1), date(2018, 1, 1)) is True
    assert is_adult(date(2001, 12, 31), date(2018, 1, 1)) is False


@pytest.mark.req("A-1")
def test_seller_registration_omits_gender_and_birth_date() -> None:
    model = _adapter.validate_python(_base("seller"))
    assert model.role == Role.SELLER
    assert not hasattr(model, "birth_date")


@pytest.mark.req("A-1")
def test_client_requires_gender_and_birth_date() -> None:
    with pytest.raises(ValidationError):
        _adapter.validate_python(_base("client"))  # missing gender + birth_date


@pytest.mark.req("A-1")
def test_minor_collaborator_is_rejected() -> None:
    payload = _base("collaborator") | {"gender": "male", "birth_date": "2015-01-01"}
    with pytest.raises(ValidationError, match="at least 18"):
        _adapter.validate_python(payload)


@pytest.mark.req("A-1")
def test_adult_client_is_accepted() -> None:
    payload = _base("client") | {"gender": "female", "birth_date": "1990-01-01"}
    model = _adapter.validate_python(payload)
    assert model.role == Role.CLIENT
    assert model.birth_date == date(1990, 1, 1)


@pytest.mark.req("A-1")
def test_unknown_role_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _adapter.validate_python(_base("super_admin"))  # not a self-registerable role

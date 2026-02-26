"""Unit tests for utility helpers in the service layer."""

from __future__ import annotations

from while_i_slept_api.services.utils import iso_now, new_jti, new_user_id, utc_now


def test_utc_now_and_iso_now_are_utc() -> None:
    now = utc_now()
    now_iso = iso_now()

    assert now.tzinfo is not None
    assert now_iso.endswith("Z")


def test_generated_ids_have_expected_prefixes_and_are_unique() -> None:
    user_id_1 = new_user_id()
    user_id_2 = new_user_id()
    jti_1 = new_jti()
    jti_2 = new_jti()

    assert user_id_1.startswith("usr_")
    assert user_id_2.startswith("usr_")
    assert user_id_1 != user_id_2
    assert jti_1 != jti_2

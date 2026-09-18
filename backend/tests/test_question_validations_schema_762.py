"""tests/test_question_validations_schema_762.py

Per-school "this answer was checked" state (#762). Keyed by stable_question_id
(ADR-008 / migration 0067) because `q1` names a SLOT within a set, not a
question, and the same question appears in several sets.
"""

import pytest


@pytest.mark.asyncio
async def test_the_table_exists_with_the_expected_key(db_conn):
    cols = {
        r["column_name"]: r["data_type"]
        for r in await db_conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'question_validations'"
        )
    }
    assert set(cols) == {
        "school_id",
        "stable_question_id",
        "correct_text",
        "validated_by",
        "validated_at",
    }
    pk = [
        r["attname"]
        for r in await db_conn.fetch(
            "SELECT a.attname FROM pg_index i "
            "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = 'question_validations'::regclass AND i.indisprimary"
        )
    ]
    assert sorted(pk) == ["school_id", "stable_question_id"]


@pytest.mark.asyncio
async def test_row_level_security_is_forced(db_conn):
    row = await db_conn.fetchrow(
        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
        "WHERE relname = 'question_validations'"
    )
    assert row["relrowsecurity"] and row["relforcerowsecurity"]
    policies = [
        r["polname"]
        for r in await db_conn.fetch(
            "SELECT polname FROM pg_policy WHERE polrelid = 'question_validations'::regclass"
        )
    ]
    assert "tenant_isolation" in policies

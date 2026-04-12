"""
tests/test_phase_e_pipeline_billing.py

Phase E — Pipeline Billing tests.

Coverage:
  POST /api/v1/schools/{id}/curriculum/definitions/{def_id}/estimate  — cost estimate
  POST /api/v1/schools/{id}/curriculum/definitions/{def_id}/trigger   — pipeline trigger from definition

Key gates:
  - Definition must be approved
  - trigger requires confirm=True
  - Concurrency guard (one job per school+grade)
  - Within-allowance vs. exhausted-allowance path (Stripe mocked)
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

_PW = "SecureTestPwd1!"

_VALID_DEF = {
    "name": "Grade 9 STEM — Unit Test Build",
    "grade": 9,
    "languages": ["en"],
    "subjects": [
        {
            "subject_label": "Mathematics",
            "units": [{"title": "Algebra"}, {"title": "Geometry"}],
        },
        {
            "subject_label": "Science",
            "units": [{"title": "Physics Basics"}],
        },
    ],
}


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _register(client: AsyncClient, name: str, email: str) -> dict:
    r = await client.post(
        "/api/v1/schools/register",
        json={"school_name": name, "contact_email": email, "country": "CA", "password": _PW},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _submit_and_approve(
    client: AsyncClient, school_id: str, token: str
) -> str:
    """Submit a definition and immediately approve it. Returns definition_id."""
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions",
        json=_VALID_DEF,
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    definition_id = r.json()["definition_id"]

    r2 = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/approve",
        headers=_auth(token),
    )
    assert r2.status_code == 200, r2.text
    return definition_id


# ── Estimate tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_estimate_unauthenticated(client: AsyncClient, db_conn) -> None:
    """Estimate endpoint requires JWT."""
    r = await client.post(
        f"/api/v1/schools/{uuid.uuid4()}/curriculum/definitions/{uuid.uuid4()}/estimate",
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_estimate_pending_definition_returns_409(client: AsyncClient, db_conn) -> None:
    """Cannot estimate a definition that is still pending_approval."""
    school = await _register(client, "Est Pending School", "est-pending@example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions",
        json=_VALID_DEF,
        headers=_auth(token),
    )
    assert r.status_code == 201
    definition_id = r.json()["definition_id"]

    r2 = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/estimate",
        headers=_auth(token),
    )
    assert r2.status_code == 409
    assert r2.json()["error"] == "not_approved"


@pytest.mark.asyncio
async def test_estimate_approved_definition(client: AsyncClient, db_conn) -> None:
    """
    Estimate on an approved definition returns cost breakdown.
    Stripe is mocked so card_last4 lookup doesn't reach the network.
    """
    school = await _register(client, "Est School", "est-approved@example.com")
    school_id, token = school["school_id"], school["access_token"]

    definition_id = await _submit_and_approve(client, school_id, token)

    with patch(
        "src.school.pipeline_router._get_card_last4", new=AsyncMock(return_value="4242")
    ):
        r = await client.post(
            f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/estimate",
            headers=_auth(token),
        )

    assert r.status_code == 200
    data = r.json()

    # Shape checks
    assert data["definition_id"] == definition_id
    assert data["total_units"] == 3          # 2 + 1 units
    assert data["languages"] == ["en"]
    assert data["unit_runs"] == 3            # 3 units × 1 language
    assert data["estimated_input_tokens"] > 0
    assert data["estimated_output_tokens"] > 0

    # Cost must be a valid decimal string
    cost = Decimal(data["estimated_cost_usd"])
    assert cost > Decimal("0")

    # No subscription → no build allowance → within_allowance is False
    # (school was registered but no Stripe subscription seeded)
    assert isinstance(data["within_allowance"], bool)
    assert isinstance(data["builds_remaining"], int)


@pytest.mark.asyncio
async def test_estimate_multilanguage_scales_unit_runs(client: AsyncClient, db_conn) -> None:
    """unit_runs = total_units × language_count."""
    school = await _register(client, "Est ML School", "est-ml@example.com")
    school_id, token = school["school_id"], school["access_token"]

    defn_body = {
        **_VALID_DEF,
        "name": "Grade 9 Multilang",
        "languages": ["en", "fr"],
    }
    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions",
        json=defn_body,
        headers=_auth(token),
    )
    assert r.status_code == 201
    definition_id = r.json()["definition_id"]

    await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/approve",
        headers=_auth(token),
    )

    with patch("src.school.pipeline_router._get_card_last4", new=AsyncMock(return_value=None)):
        r2 = await client.post(
            f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/estimate",
            headers=_auth(token),
        )

    assert r2.status_code == 200
    data = r2.json()
    assert data["total_units"] == 3
    assert data["languages"] == ["en", "fr"]
    assert data["unit_runs"] == 6   # 3 units × 2 languages


# ── Trigger tests ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_requires_confirm(client: AsyncClient, db_conn) -> None:
    """trigger without confirm=True returns 400."""
    school = await _register(client, "Trigger Noconfirm", "trig-noconfirm@example.com")
    school_id, token = school["school_id"], school["access_token"]
    definition_id = await _submit_and_approve(client, school_id, token)

    with patch("src.school.pipeline_router._get_card_last4", new=AsyncMock(return_value=None)):
        r = await client.post(
            f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/trigger",
            json={"confirm": False, "langs": "en"},
            headers=_auth(token),
        )
    assert r.status_code == 400
    assert r.json()["error"] == "confirmation_required"


@pytest.mark.asyncio
async def test_trigger_pending_definition_returns_409(client: AsyncClient, db_conn) -> None:
    """trigger on a pending definition returns 409."""
    school = await _register(client, "Trigger Pending", "trig-pending@example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions",
        json=_VALID_DEF,
        headers=_auth(token),
    )
    definition_id = r.json()["definition_id"]

    r2 = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/trigger",
        json={"confirm": True, "langs": "en"},
        headers=_auth(token),
    )
    assert r2.status_code == 409
    assert r2.json()["error"] == "not_approved"


@pytest.mark.asyncio
async def test_trigger_dispatches_pipeline_job(client: AsyncClient, db_conn) -> None:
    """
    Successful trigger (within allowance) creates curricula rows and queues a job.

    Celery send_task and consume_build are mocked — we verify HTTP response
    shape and that the pipeline_jobs row was created.
    """
    school = await _register(client, "Trigger OK School", "trig-ok@example.com")
    school_id, token = school["school_id"], school["access_token"]
    definition_id = await _submit_and_approve(client, school_id, token)

    with (
        patch("src.school.pipeline_router.check_build_allowance", new=AsyncMock(
            return_value={
                "allowed": True,
                "builds_included": 3,
                "builds_used": 0,
                "builds_remaining": 3,
                "builds_period_end": None,
                "builds_credits_balance": 0,
            }
        )),
        patch("src.school.pipeline_router.consume_build", new=AsyncMock()),
        patch("src.core.celery_app.celery_app.send_task", MagicMock()),
    ):
        r = await client.post(
            f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/trigger",
            json={"confirm": True, "langs": "en"},
            headers=_auth(token),
        )

    assert r.status_code == 202, r.text
    data = r.json()
    assert "job_id" in data
    assert "curriculum_id" in data
    assert data["status"] == "queued"
    assert Decimal(data["estimated_cost_usd"]) >= Decimal("0")
    assert data["charged_amount_usd"] is None  # within allowance → no charge


@pytest.mark.asyncio
async def test_trigger_charges_stripe_when_allowance_exhausted(
    client: AsyncClient, db_conn
) -> None:
    """
    When build allowance is exhausted, a Stripe PaymentIntent is created.
    Stripe is mocked — we verify the charge amount in the response.
    """
    school = await _register(client, "Trigger Charge School", "trig-charge@example.com")
    school_id, token = school["school_id"], school["access_token"]
    definition_id = await _submit_and_approve(client, school_id, token)

    # Seed a subscription row with a stripe_customer_id so the billing path runs.
    # Must use the app's pool (committed connection) so the API endpoint can see it.
    pool = client._transport.app.state.pool
    async with pool.acquire() as _conn:
        await _conn.execute("SELECT set_config('app.current_school_id', 'bypass', false)")
        await _conn.execute(
            """
            INSERT INTO school_subscriptions
                (school_id, plan, status, stripe_customer_id, stripe_subscription_id,
                 current_period_end)
            VALUES ($1::uuid, 'starter', 'active', 'cus_test123', 'sub_test123', NOW() + INTERVAL '30 days')
            ON CONFLICT (school_id) DO UPDATE
                SET stripe_customer_id = EXCLUDED.stripe_customer_id
            """,
            school_id,
        )

    mock_pi = {"id": "pi_test", "status": "succeeded"}

    with (
        patch("src.school.pipeline_router.check_build_allowance", new=AsyncMock(
            return_value={
                "allowed": False,
                "builds_included": 1,
                "builds_used": 1,
                "builds_remaining": 0,
                "builds_period_end": None,
                "builds_credits_balance": 0,
            }
        )),
        patch("src.school.pipeline_router.consume_build", new=AsyncMock()),
        patch("src.school.pipeline_router.run_stripe", new=AsyncMock(return_value=mock_pi)),
    ):
        r = await client.post(
            f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/trigger",
            json={"confirm": True, "langs": "en"},
            headers=_auth(token),
        )

    assert r.status_code == 202, r.text
    data = r.json()
    assert data["charged_amount_usd"] == "15.00"


@pytest.mark.asyncio
async def test_trigger_payment_required_no_card(client: AsyncClient, db_conn) -> None:
    """
    When allowance is exhausted and no Stripe customer on file, returns 402.
    """
    school = await _register(client, "Trigger NoCard", "trig-nocard@example.com")
    school_id, token = school["school_id"], school["access_token"]
    definition_id = await _submit_and_approve(client, school_id, token)

    with patch("src.school.pipeline_router.check_build_allowance", new=AsyncMock(
        return_value={
            "allowed": False,
            "builds_included": 0,
            "builds_used": 0,
            "builds_remaining": 0,
            "builds_period_end": None,
            "builds_credits_balance": 0,
        }
    )):
        r = await client.post(
            f"/api/v1/schools/{school_id}/curriculum/definitions/{definition_id}/trigger",
            json={"confirm": True, "langs": "en"},
            headers=_auth(token),
        )

    assert r.status_code == 402
    assert r.json()["error"] == "payment_required"


@pytest.mark.asyncio
async def test_trigger_not_found(client: AsyncClient, db_conn) -> None:
    """Trigger on a non-existent definition returns 404."""
    school = await _register(client, "Trigger 404", "trig-404@example.com")
    school_id, token = school["school_id"], school["access_token"]

    r = await client.post(
        f"/api/v1/schools/{school_id}/curriculum/definitions/{uuid.uuid4()}/trigger",
        json={"confirm": True, "langs": "en"},
        headers=_auth(token),
    )
    assert r.status_code == 404

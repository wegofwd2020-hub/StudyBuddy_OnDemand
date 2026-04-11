"""
backend/src/pricing.py

Single source of truth for ALL platform pricing and cost parameters.

Three sections:
  1. SCHOOL_PLANS       — subscription tiers (prices, seat limits, build allowances)
  2. STORAGE_PACKAGES   — storage add-on options
  3. AI_GENERATION      — per-token and per-grade AI cost model

DESIGN INTENT
─────────────
This module is deliberately a flat, human-readable file with no env-var
overrides. It answers the question: "what does the platform charge and cost?"
without requiring any environment configuration.

Operational config (Stripe price IDs, API keys) lives in config.py.
That file references these constants for the default values it exposes.

When presenting to investors or architects, modify values in this file only —
no need to touch config.py, the router, or the frontend PLANS array.

See web/lib/pricing.ts for the TypeScript mirror used by the subscription page.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


# ─────────────────────────────────────────────────────────────────────────────
# 1. School subscription plans
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SchoolPlan:
    """
    One subscription tier available to schools.

    Attributes
    ----------
    id              Stripe metadata key and DB plan column value.
    name            Display name shown in the school portal.
    price_monthly   USD / month charged to the school. "0.00" = free tier.
                    "custom" = sales-negotiated (Enterprise).
    max_students    Hard seat cap. 9999 is the sentinel for "effectively unlimited".
    max_teachers    Hard seat cap. 9999 is the sentinel for "effectively unlimited".
    builds_per_year Annual grade-level pipeline build allowance.
                    -1 = unlimited (Enterprise).
    storage_base_gb Base storage included (GB). All plans include 5 GB; schools
                    can purchase additional storage in add-on packages.
    features        Bullet points shown in the plan comparison card.
    highlight       True = "Popular" badge in the UI.
    """

    id: str
    name: str
    price_monthly: str          # decimal string, e.g. "49.00". "0.00" = free. "custom" = sales
    max_students: int
    max_teachers: int
    builds_per_year: int        # -1 = unlimited
    storage_base_gb: int = 5    # 5 GB included in every plan
    features: tuple[str, ...] = field(default_factory=tuple)
    highlight: bool = False


SCHOOL_PLANS: dict[str, SchoolPlan] = {
    "starter": SchoolPlan(
        id="starter",
        name="Starter",
        price_monthly="49.00",
        max_students=30,
        max_teachers=3,
        builds_per_year=1,
        storage_base_gb=5,
        features=(
            "30 students · 3 teachers",
            "1 custom curriculum build / year",
            "5 GB storage included",
            "Default curriculum (Grades 5–12)",
            "English content",
        ),
        highlight=False,
    ),
    "professional": SchoolPlan(
        id="professional",
        name="Professional",
        price_monthly="149.00",
        max_students=150,
        max_teachers=10,
        builds_per_year=3,
        storage_base_gb=5,
        features=(
            "150 students · 10 teachers",
            "3 custom curriculum builds / year",
            "5 GB storage included",
            "EN + FR + ES content",
            "Custom curriculum upload",
            "Teacher reporting dashboard",
        ),
        highlight=True,
    ),
    "enterprise": SchoolPlan(
        id="enterprise",
        name="Enterprise",
        price_monthly="custom",
        max_students=9999,
        max_teachers=9999,
        builds_per_year=-1,     # unlimited
        storage_base_gb=5,      # base; typically negotiated higher
        features=(
            "Unlimited students & teachers",
            "Unlimited curriculum builds",
            "Custom storage quota",
            "All languages",
            "Dedicated support · SLA guarantee",
        ),
        highlight=False,
    ),
}

# ── Convenience accessors ─────────────────────────────────────────────────────

def get_plan(plan_id: str) -> SchoolPlan:
    """Return the SchoolPlan for plan_id, falling back to 'starter' if unknown."""
    return SCHOOL_PLANS.get(plan_id, SCHOOL_PLANS["starter"])


def plan_builds(plan_id: str) -> int:
    """Annual build allowance for plan_id. -1 = unlimited."""
    return get_plan(plan_id).builds_per_year


def plan_seats(plan_id: str) -> dict[str, int]:
    """Return {max_students, max_teachers} for plan_id."""
    plan = get_plan(plan_id)
    return {"max_students": plan.max_students, "max_teachers": plan.max_teachers}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Storage add-on packages
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StoragePackage:
    """
    A purchasable storage block. Bought as a one-time Stripe payment.

    Attributes
    ----------
    gb          Additional gigabytes added to the school's quota.
    price_usd   One-time charge in USD.
    """

    gb: int
    price_usd: str              # decimal string, e.g. "19.00"


STORAGE_PACKAGES: dict[int, StoragePackage] = {
    5:  StoragePackage(gb=5,  price_usd="19.00"),
    10: StoragePackage(gb=10, price_usd="35.00"),
    25: StoragePackage(gb=25, price_usd="79.00"),
}

VALID_STORAGE_GB: frozenset[int] = frozenset(STORAGE_PACKAGES.keys())  # {5, 10, 25}


# ─────────────────────────────────────────────────────────────────────────────
# 2b. Extra build add-ons  (#106 pay-per-build, #107 credit bundles)
# ─────────────────────────────────────────────────────────────────────────────

# One-time $15 charge for a single extra grade build beyond the plan allowance.
EXTRA_BUILD_PRICE_USD: str = "15.00"

@dataclass(frozen=True)
class BuildCreditBundle:
    """
    A purchasable block of curriculum build credits.

    Credits roll over — they never expire.  Consumed after the plan allowance
    is exhausted (builds_used >= builds_included).

    Attributes
    ----------
    credits     Number of grade-level builds in the bundle.
    price_usd   One-time charge in USD (decimal string).
    """

    credits: int
    price_usd: str              # decimal string, e.g. "39.00"


BUILD_CREDIT_BUNDLES: dict[int, BuildCreditBundle] = {
    3:  BuildCreditBundle(credits=3,  price_usd="39.00"),
    10: BuildCreditBundle(credits=10, price_usd="119.00"),
    25: BuildCreditBundle(credits=25, price_usd="269.00"),
}

VALID_CREDIT_BUNDLE_SIZES: frozenset[int] = frozenset(BUILD_CREDIT_BUNDLES.keys())  # {3, 10, 25}


# ─────────────────────────────────────────────────────────────────────────────
# 3. AI generation cost model  (pipeline / build_grade.py)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AICostModel:
    """
    Per-token cost rates for Claude Sonnet (USD).

    Used by the pipeline spend-cap check and for cost projections.
    These are Anthropic list prices as of the model pinned in pipeline/config.py.
    Update this block whenever the model is upgraded.

    Attributes
    ----------
    model               The Claude model ID these rates apply to.
    input_per_million   USD per 1 million input tokens.
    output_per_million  USD per 1 million output tokens.
    max_run_usd         Pipeline abort threshold — never exceed this per run.

    Derived estimates (based on profiling Grade 8 English):
      avg_input_tokens_per_unit   ≈ 1 800
      avg_output_tokens_per_unit  ≈ 3 200
      units_per_grade             ≈ 30
      ─────────────────────────────────────
      cost_per_grade_en   ≈ $11.55
      cost_per_grade_3x   ≈ $34.65  (EN + FR + ES)
    """

    model: str = "claude-sonnet-4-6"

    # API rates
    input_per_million: Decimal = Decimal("3.00")    # $3 / 1M input tokens
    output_per_million: Decimal = Decimal("15.00")  # $15 / 1M output tokens

    # Pipeline safety cap
    max_run_usd: Decimal = Decimal("50.00")

    # Derived cost estimates (informational — not enforced at runtime)
    avg_input_tokens_per_unit: int = 1_800
    avg_output_tokens_per_unit: int = 3_200
    avg_units_per_grade: int = 30

    @property
    def cost_per_unit_usd(self) -> Decimal:
        """Estimated Anthropic API cost per curriculum unit (one language)."""
        input_cost  = Decimal(self.avg_input_tokens_per_unit)  / Decimal("1_000_000") * self.input_per_million
        output_cost = Decimal(self.avg_output_tokens_per_unit) / Decimal("1_000_000") * self.output_per_million
        return (input_cost + output_cost).quantize(Decimal("0.0001"))

    @property
    def cost_per_grade_en_usd(self) -> Decimal:
        """Estimated cost to build one grade in English."""
        return (self.cost_per_unit_usd * self.avg_units_per_grade).quantize(Decimal("0.01"))

    @property
    def cost_per_grade_3lang_usd(self) -> Decimal:
        """Estimated cost to build one grade in EN + FR + ES."""
        return (self.cost_per_grade_en_usd * 3).quantize(Decimal("0.01"))

    # Convenience floats for pipeline/config.py compatibility
    @property
    def input_per_token_usd(self) -> float:
        """Per-token input cost as float (pipeline config format)."""
        return float(self.input_per_million / Decimal("1_000_000"))

    @property
    def output_per_token_usd(self) -> float:
        """Per-token output cost as float (pipeline config format)."""
        return float(self.output_per_million / Decimal("1_000_000"))


AI_COST = AICostModel()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Independent teacher plans  (future — teacher tier rebuild, #57)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TeacherPlan:
    """
    Flat-fee independent teacher subscription tier (#57).

    Teachers pay a flat monthly fee and keep 100% of any student-side revenue
    they collect (Option A).  Option B (Stripe Connect revenue share) and
    Option C (seat-tiered flat) are tracked in GitHub #104 and #105 respectively.

    Attributes
    ----------
    id              Stripe metadata key and DB plan column value.
    name            Display name shown in the teacher portal.
    price_monthly   USD / month (decimal string, e.g. "29.00").
    max_students    Hard seat cap on independently-enrolled students.
    features        Bullet points shown in the plan comparison card.
    highlight       True = "Popular" badge in the UI.
    """

    id: str
    name: str
    price_monthly: str          # decimal string
    max_students: int
    features: tuple[str, ...] = field(default_factory=tuple)
    highlight: bool = False


TEACHER_PLANS: dict[str, TeacherPlan] = {
    "solo": TeacherPlan(
        id="solo",
        name="Solo",
        price_monthly="29.00",
        max_students=25,
        features=(
            "Up to 25 students",
            "Default curriculum (Grades 5–12)",
            "English content",
            "Progress dashboard",
        ),
        highlight=False,
    ),
    "growth": TeacherPlan(
        id="growth",
        name="Growth",
        price_monthly="59.00",
        max_students=75,
        features=(
            "Up to 75 students",
            "EN + FR + ES content",
            "Teacher reporting dashboard",
            "Weekly digest emails",
        ),
        highlight=True,
    ),
    "pro": TeacherPlan(
        id="pro",
        name="Pro",
        price_monthly="99.00",
        max_students=200,
        features=(
            "Up to 200 students",
            "All languages",
            "Full reporting suite",
            "Priority support",
        ),
        highlight=False,
    ),
}

VALID_TEACHER_PLAN_IDS: frozenset[str] = frozenset(TEACHER_PLANS.keys())


def get_teacher_plan(plan_id: str) -> TeacherPlan:
    """Return TeacherPlan for plan_id. Raises KeyError for unknown IDs."""
    if plan_id not in TEACHER_PLANS:
        raise KeyError(f"Unknown teacher plan: {plan_id!r}. Valid: {sorted(VALID_TEACHER_PLAN_IDS)}")
    return TEACHER_PLANS[plan_id]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Option B — Revenue-share billing constants  (#104)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RevenueShare:
    """
    Platform revenue-share parameters for Option B teacher billing (#104).

    Under this model the teacher earns teacher_pct % of each student's monthly
    payment.  The platform keeps platform_pct % as a Stripe application fee.
    Stripe's application_fee_percent accepts an integer so both values are ints
    that must sum to 100.

    student_price_monthly is the platform's listed per-student price the
    student sees at checkout.
    """

    teacher_pct: int = 70          # % forwarded to teacher's Connect account
    platform_pct: int = 30         # % kept by platform as application fee
    student_price_monthly: str = "9.99"  # USD, decimal string


REVENUE_SHARE = RevenueShare()

# Passed directly to Stripe's application_fee_percent on Subscription.create.
CONNECT_APPLICATION_FEE_PCT: int = REVENUE_SHARE.platform_pct

/**
 * web/lib/pricing.ts
 *
 * TypeScript mirror of backend/src/pricing.py
 *
 * Single source of truth for ALL platform pricing displayed in the web UI.
 * When modifying plan prices, seat limits, or add-on costs — edit both files.
 *
 * This file has no imports and no runtime dependencies — safe to import
 * anywhere in the Next.js app (server components, client components, tests).
 */

// ─────────────────────────────────────────────────────────────────────────────
// 1. School subscription plans
// ─────────────────────────────────────────────────────────────────────────────

export interface SchoolPlan {
  /** Stripe metadata key and DB plan column value */
  id: string;
  /** Display name */
  name: string;
  /**
   * Monthly price string shown in the UI.
   * "free" → shown as "Free"
   * "custom" → shown as "Custom"
   * otherwise → shown as "$X / month"
   */
  priceMonthly: string;
  /** Hard student seat cap. null = effectively unlimited (Enterprise) */
  maxStudents: number | null;
  /** Hard teacher seat cap. null = effectively unlimited (Enterprise) */
  maxTeachers: number | null;
  /**
   * Annual grade-level pipeline build allowance.
   * -1 = unlimited (Enterprise)
   * null = not applicable (no subscription)
   */
  buildsPerYear: number | null;
  /** Base storage included in gigabytes */
  storageBaseGb: number;
  /** Feature bullet points for the plan comparison card */
  features: readonly string[];
  /** Show "Popular" badge in the UI */
  highlight: boolean;
}

export const SCHOOL_PLANS: Record<string, SchoolPlan> = {
  starter: {
    id: "starter",
    name: "Starter",
    priceMonthly: "49.00",
    maxStudents: 30,
    maxTeachers: 3,
    buildsPerYear: 1,
    storageBaseGb: 5,
    features: [
      "30 students · 3 teachers",
      "1 custom curriculum build / year",
      "5 GB storage included",
      "Default curriculum (Grades 5–12)",
      "English content",
    ],
    highlight: false,
  },

  professional: {
    id: "professional",
    name: "Professional",
    priceMonthly: "149.00",
    maxStudents: 150,
    maxTeachers: 10,
    buildsPerYear: 3,
    storageBaseGb: 5,
    features: [
      "150 students · 10 teachers",
      "3 custom curriculum builds / year",
      "5 GB storage included",
      "EN + FR + ES content",
      "Custom curriculum upload",
      "Teacher reporting dashboard",
    ],
    highlight: true,
  },

  enterprise: {
    id: "enterprise",
    name: "Enterprise",
    priceMonthly: "custom",
    maxStudents: null,
    maxTeachers: null,
    buildsPerYear: -1,          // unlimited
    storageBaseGb: 5,           // base; typically negotiated higher
    features: [
      "Unlimited students & teachers",
      "Unlimited curriculum builds",
      "Custom storage quota",
      "All languages",
      "Dedicated support · SLA guarantee",
    ],
    highlight: false,
  },
} as const;

/** Ordered array for rendering the plan comparison grid */
export const SCHOOL_PLANS_LIST: SchoolPlan[] = [
  SCHOOL_PLANS.starter,
  SCHOOL_PLANS.professional,
  SCHOOL_PLANS.enterprise,
];

/** Format priceMonthly for display in the UI */
export function formatPlanPrice(plan: SchoolPlan): string {
  if (plan.priceMonthly === "custom") return "Custom";
  if (plan.priceMonthly === "0.00" || plan.priceMonthly === "free") return "Free";
  return `$${parseFloat(plan.priceMonthly).toFixed(0)} / month`;
}


// ─────────────────────────────────────────────────────────────────────────────
// 2. Storage add-on packages
// ─────────────────────────────────────────────────────────────────────────────

export interface StoragePackage {
  /** Gigabytes added to the school's quota */
  gb: number;
  /** One-time USD price as a decimal string */
  priceUsd: string;
  /** Human-readable label */
  label: string;
}

export const STORAGE_PACKAGES: StoragePackage[] = [
  { gb: 5,  priceUsd: "19.00", label: "+5 GB — $19" },
  { gb: 10, priceUsd: "35.00", label: "+10 GB — $35" },
  { gb: 25, priceUsd: "79.00", label: "+25 GB — $79" },
];

export const VALID_STORAGE_GB = new Set([5, 10, 25] as const);


// ─────────────────────────────────────────────────────────────────────────────
// 3. AI generation cost model  (for internal dashboards / cost projection)
// ─────────────────────────────────────────────────────────────────────────────

export const AI_COST_MODEL = {
  /** Claude model these rates apply to */
  model: "claude-sonnet-4-6" as const,

  /** USD per 1 million input tokens */
  inputPerMillionUsd: 3.00,

  /** USD per 1 million output tokens */
  outputPerMillionUsd: 15.00,

  /** Pipeline abort threshold — never exceed this per run */
  maxRunUsd: 50.00,

  /** Estimated average input tokens per curriculum unit */
  avgInputTokensPerUnit: 1_800,

  /** Estimated average output tokens per curriculum unit */
  avgOutputTokensPerUnit: 3_200,

  /** Estimated units per grade level */
  avgUnitsPerGrade: 30,

  /** Estimated Anthropic API cost to build one grade in English */
  get costPerGradeEnUsd(): number {
    const inputCost  = (this.avgInputTokensPerUnit  / 1_000_000) * this.inputPerMillionUsd;
    const outputCost = (this.avgOutputTokensPerUnit / 1_000_000) * this.outputPerMillionUsd;
    return Math.round((inputCost + outputCost) * this.avgUnitsPerGrade * 100) / 100;
  },

  /** Estimated cost to build one grade in EN + FR + ES */
  get costPerGrade3LangUsd(): number {
    return Math.round(this.costPerGradeEnUsd * 3 * 100) / 100;
  },
} as const;


// ─────────────────────────────────────────────────────────────────────────────
// 4. Independent teacher plans  (future — teacher tier rebuild, #57)
// ─────────────────────────────────────────────────────────────────────────────

export interface TeacherPlan {
  id: string;
  name: string;
  priceMonthly: string;
  maxStudents: number;
}

export const TEACHER_PLANS: TeacherPlan[] = [
  { id: "solo",   name: "Solo",   priceMonthly: "29.00", maxStudents: 25  },
  { id: "growth", name: "Growth", priceMonthly: "59.00", maxStudents: 75  },
  { id: "pro",    name: "Pro",    priceMonthly: "99.00", maxStudents: 200 },
];

import { Info } from "lucide-react";

import type { ReportScope } from "@/lib/api/reports";

/**
 * Says, on the page, what population the figures cover (#640, design §10).
 *
 * Since #576 a teacher's numbers mean THEIR GRADES and a school admin's mean
 * the whole school. Same tile, same label, two different populations — and
 * nothing on screen said which. Venki reported the symptom without recognising
 * it as one: "Teacher Management shows Gr 8, 10, 11 but Student Progress offers
 * 8, 10, 11, 12". Both lists were correct; they answer different questions, and
 * the page never said so.
 *
 * The defect was never the layout. It was the silence about what the numbers
 * cover — which is why this is a caption and not a redesign.
 *
 * The scope comes from the server, derived from the same filter that scoped the
 * query, so this can never describe a population the data does not.
 *
 * Two components because the three states want two shapes: a pill that sits
 * beside a heading, and a block that has to be read before the zeros below it
 * are believed.
 */

/** The inline pill: "Whole school" / "Your grades: 8, 10". */
export function ScopeNote({ scope }: { scope: ReportScope | undefined }) {
  // The no-grades case is not a pill — it needs a sentence, and it renders as
  // <NoGradesNotice> above the figures instead.
  if (!scope || (scope.kind === "grades" && scope.grades.length === 0)) return null;

  const label =
    scope.kind === "school"
      ? "Whole school"
      : `Your grades: ${[...scope.grades].sort((a, b) => a - b).join(", ")}`;

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-600"
      title={
        scope.kind === "school"
          ? "You are a school admin, so these figures cover every grade in the school."
          : "These figures cover only the grades you are assigned to teach."
      }
    >
      <Info className="h-3 w-3" aria-hidden="true" />
      {label}
    </span>
  );
}

/**
 * The teacher-with-no-assignments case.
 *
 * A real and distinct state, not an error: they see nothing because nothing is
 * in their scope. Without saying so, the page is a grid of zeroes with no way
 * to tell "not set up" from "broken" — the §4.2 empty-state problem, and the
 * one a new school hits first.
 */
export function NoGradesNotice({ scope }: { scope: ReportScope | undefined }) {
  if (!scope || scope.kind !== "grades" || scope.grades.length > 0) return null;

  return (
    <div
      className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800"
      role="status"
    >
      <Info className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span>
        <strong className="font-semibold">You have no grades assigned yet.</strong> These
        figures are empty because there is nothing in your scope — not because there is no
        activity. Ask a school admin to assign your grades.
      </span>
    </div>
  );
}

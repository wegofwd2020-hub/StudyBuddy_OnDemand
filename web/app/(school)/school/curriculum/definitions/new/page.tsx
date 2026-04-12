"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  submitDefinition,
  type DefinitionSubject,
  type DefinitionUnit,
} from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  ChevronRight,
  ChevronLeft,
  Plus,
  Trash2,
  GripVertical,
  Check,
} from "lucide-react";

const ALL_GRADES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
const SUPPORTED_LANGUAGES = [
  { code: "en", label: "English" },
  { code: "fr", label: "French" },
  { code: "es", label: "Spanish" },
];

// ── Step 1 — Name & grade ──────────────────────────────────────────────────────

function StepBasics({
  name,
  setName,
  grade,
  setGrade,
}: {
  name: string;
  setName: (v: string) => void;
  grade: number | "";
  setGrade: (v: number | "") => void;
}) {
  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <Label htmlFor="def_name">Curriculum name</Label>
        <Input
          id="def_name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Grade 8 STEM — Semester 1"
        />
        <p className="text-xs text-gray-400">
          Choose a name students and teachers will recognise.
        </p>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="def_grade">Grade</Label>
        <select
          id="def_grade"
          value={grade}
          onChange={(e) =>
            setGrade(e.target.value === "" ? "" : Number(e.target.value))
          }
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          <option value="">Select grade</option>
          {ALL_GRADES.map((g) => (
            <option key={g} value={g}>
              Grade {g}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

// ── Step 2 — Subjects & units ──────────────────────────────────────────────────

function UnitRow({
  unit,
  onChange,
  onRemove,
}: {
  unit: DefinitionUnit;
  onChange: (title: string) => void;
  onRemove: () => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <GripVertical className="h-4 w-4 shrink-0 text-gray-300" />
      <Input
        value={unit.title}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Unit title"
        className="flex-1 text-sm"
      />
      <button
        type="button"
        onClick={onRemove}
        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
        aria-label="Remove unit"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

function SubjectCard({
  subject,
  index,
  onChange,
  onRemove,
}: {
  subject: DefinitionSubject;
  index: number;
  onChange: (s: DefinitionSubject) => void;
  onRemove: () => void;
}) {
  function addUnit() {
    onChange({ ...subject, units: [...subject.units, { title: "" }] });
  }

  function updateUnit(i: number, title: string) {
    const units = subject.units.map((u, idx) => (idx === i ? { title } : u));
    onChange({ ...subject, units });
  }

  function removeUnit(i: number) {
    onChange({ ...subject, units: subject.units.filter((_, idx) => idx !== i) });
  }

  return (
    <Card className="border shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-400">Subject {index + 1}</span>
          <button
            type="button"
            onClick={onRemove}
            className="ml-auto rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
            aria-label="Remove subject"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
        <Input
          value={subject.subject_label}
          onChange={(e) => onChange({ ...subject, subject_label: e.target.value })}
          placeholder="Subject name (e.g. Mathematics)"
          className="font-medium"
        />
      </CardHeader>
      <CardContent className="space-y-2 pt-0">
        <Label className="text-xs text-gray-500">Units</Label>
        {subject.units.map((u, i) => (
          <UnitRow
            key={i}
            unit={u}
            onChange={(title) => updateUnit(i, title)}
            onRemove={() => removeUnit(i)}
          />
        ))}
        <button
          type="button"
          onClick={addUnit}
          className="flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-800"
        >
          <Plus className="h-3.5 w-3.5" />
          Add unit
        </button>
      </CardContent>
    </Card>
  );
}

function StepSubjects({
  subjects,
  setSubjects,
}: {
  subjects: DefinitionSubject[];
  setSubjects: (v: DefinitionSubject[]) => void;
}) {
  function addSubject() {
    setSubjects([...subjects, { subject_label: "", units: [{ title: "" }] }]);
  }

  function updateSubject(i: number, s: DefinitionSubject) {
    setSubjects(subjects.map((sub, idx) => (idx === i ? s : sub)));
  }

  function removeSubject(i: number) {
    setSubjects(subjects.filter((_, idx) => idx !== i));
  }

  return (
    <div className="space-y-4">
      {subjects.map((s, i) => (
        <SubjectCard
          key={i}
          subject={s}
          index={i}
          onChange={(updated) => updateSubject(i, updated)}
          onRemove={() => removeSubject(i)}
        />
      ))}
      <Button type="button" variant="outline" onClick={addSubject} className="w-full gap-2">
        <Plus className="h-4 w-4" />
        Add subject
      </Button>
    </div>
  );
}

// ── Step 3 — Languages ─────────────────────────────────────────────────────────

function StepLanguages({
  languages,
  setLanguages,
}: {
  languages: string[];
  setLanguages: (v: string[]) => void;
}) {
  function toggle(code: string) {
    if (languages.includes(code)) {
      if (languages.length === 1) return; // keep at least one
      setLanguages(languages.filter((l) => l !== code));
    } else {
      setLanguages([...languages, code]);
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-500">
        Select the languages in which content should be generated. Each language is a separate
        pipeline run.
      </p>
      <div className="flex flex-wrap gap-3">
        {SUPPORTED_LANGUAGES.map((lang) => {
          const selected = languages.includes(lang.code);
          return (
            <button
              key={lang.code}
              type="button"
              onClick={() => toggle(lang.code)}
              className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                selected
                  ? "border-indigo-300 bg-indigo-50 text-indigo-700"
                  : "border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {selected && <Check className="h-3.5 w-3.5" />}
              {lang.label}
            </button>
          );
        })}
      </div>
      <p className="text-xs text-gray-400">
        At least one language is required. Content cost scales with the number of languages.
      </p>
    </div>
  );
}

// ── Step 4 — Review & submit ───────────────────────────────────────────────────

function StepReview({
  name,
  grade,
  languages,
  subjects,
}: {
  name: string;
  grade: number | "";
  languages: string[];
  subjects: DefinitionSubject[];
}) {
  const totalUnits = subjects.reduce((acc, s) => acc + s.units.length, 0);
  return (
    <div className="space-y-4">
      <div className="rounded-lg bg-gray-50 p-4 space-y-3 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-500">Name</span>
          <span className="font-medium text-gray-900">{name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Grade</span>
          <span className="font-medium text-gray-900">Grade {grade}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Languages</span>
          <span className="font-medium text-gray-900">
            {languages.map((l) => l.toUpperCase()).join(", ")}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Subjects</span>
          <span className="font-medium text-gray-900">{subjects.length}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Total units</span>
          <span className="font-medium text-gray-900">{totalUnits}</span>
        </div>
      </div>

      <div className="space-y-3">
        {subjects.map((s, i) => (
          <div key={i} className="rounded-lg border p-3">
            <p className="text-sm font-medium text-gray-800">{s.subject_label || "(unnamed)"}</p>
            <ul className="mt-1.5 space-y-1">
              {s.units.map((u, j) => (
                <li key={j} className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span className="h-1 w-1 rounded-full bg-gray-300" />
                  {u.title || "(no title)"}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-400">
        Submitting sends this definition to the school admin for approval. No content is
        generated yet — that happens after approval and pipeline billing confirmation.
      </p>
    </div>
  );
}

// ── Stepper ────────────────────────────────────────────────────────────────────

const STEPS = ["Basics", "Subjects", "Languages", "Review"];

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-2">
      {STEPS.map((label, i) => (
        <div key={i} className="flex items-center gap-2">
          <div
            className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
              i < current
                ? "bg-green-500 text-white"
                : i === current
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-400"
            }`}
          >
            {i < current ? <Check className="h-3 w-3" /> : i + 1}
          </div>
          <span
            className={`hidden text-xs sm:block ${
              i === current ? "font-medium text-gray-900" : "text-gray-400"
            }`}
          >
            {label}
          </span>
          {i < STEPS.length - 1 && <div className="h-px w-4 bg-gray-200" />}
        </div>
      ))}
    </div>
  );
}

// ── Validation helpers ─────────────────────────────────────────────────────────

function validateStep(
  step: number,
  name: string,
  grade: number | "",
  subjects: DefinitionSubject[],
): string | null {
  if (step === 0) {
    if (!name.trim()) return "Curriculum name is required.";
    if (grade === "") return "Grade is required.";
  }
  if (step === 1) {
    if (subjects.length === 0) return "At least one subject is required.";
    for (const s of subjects) {
      if (!s.subject_label.trim()) return "All subjects must have a name.";
      if (s.units.length === 0) return "Each subject must have at least one unit.";
      for (const u of s.units) {
        if (!u.title.trim()) return "All units must have a title.";
      }
    }
  }
  return null;
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function NewDefinitionPage() {
  const teacher = useTeacher();
  const router = useRouter();
  const schoolId = teacher?.school_id ?? "";

  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [grade, setGrade] = useState<number | "">("");
  const [languages, setLanguages] = useState<string[]>(["en"]);
  const [subjects, setSubjects] = useState<DefinitionSubject[]>([
    { subject_label: "", units: [{ title: "" }] },
  ]);
  const [validationError, setValidationError] = useState<string | null>(null);

  const { mutate, isPending, error } = useMutation({
    mutationFn: () =>
      submitDefinition(schoolId, {
        name,
        grade: grade as number,
        languages,
        subjects,
      }),
    onSuccess: (defn) => {
      router.push(`/school/curriculum/definitions/${defn.definition_id}`);
    },
  });

  function next() {
    const err = validateStep(step, name, grade, subjects);
    if (err) {
      setValidationError(err);
      return;
    }
    setValidationError(null);
    setStep((s) => s + 1);
  }

  function back() {
    setValidationError(null);
    setStep((s) => s - 1);
  }

  return (
    <div className="max-w-2xl space-y-6 p-6">
      <div className="flex items-center gap-2">
        <FileText className="h-6 w-6 text-indigo-600" />
        <h1 className="text-2xl font-bold text-gray-900">New Curriculum Definition</h1>
      </div>

      <StepIndicator current={step} />

      <Card className="border shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{STEPS[step]}</CardTitle>
        </CardHeader>
        <CardContent>
          {step === 0 && (
            <StepBasics name={name} setName={setName} grade={grade} setGrade={setGrade} />
          )}
          {step === 1 && (
            <StepSubjects subjects={subjects} setSubjects={setSubjects} />
          )}
          {step === 2 && (
            <StepLanguages languages={languages} setLanguages={setLanguages} />
          )}
          {step === 3 && (
            <StepReview name={name} grade={grade} languages={languages} subjects={subjects} />
          )}

          {validationError && (
            <p className="mt-3 text-sm text-red-600">{validationError}</p>
          )}
          {error && (
            <p className="mt-3 text-sm text-red-600">
              Submission failed. Please try again.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="ghost"
          onClick={step === 0 ? () => router.push("/school/curriculum/definitions") : back}
          className="gap-2"
        >
          <ChevronLeft className="h-4 w-4" />
          {step === 0 ? "Cancel" : "Back"}
        </Button>

        {step < STEPS.length - 1 ? (
          <Button type="button" onClick={next} className="gap-2">
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        ) : (
          <Button type="button" onClick={() => mutate()} disabled={isPending} className="gap-2">
            {isPending ? "Submitting…" : "Submit for approval"}
          </Button>
        )}
      </div>
    </div>
  );
}

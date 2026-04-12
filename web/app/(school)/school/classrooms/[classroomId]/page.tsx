"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTeacher } from "@/lib/hooks/useTeacher";
import {
  getClassroom,
  assignPackageToClassroom,
  removePackageFromClassroom,
  assignStudentToClassroom,
  removeStudentFromClassroom,
  listClassrooms,
  type ClassroomPackageItem,
  type ClassroomStudentItem,
} from "@/lib/api/school-admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft,
  BookOpen,
  Users,
  Trash2,
  Plus,
  GraduationCap,
} from "lucide-react";

// ── Package row ────────────────────────────────────────────────────────────────

function PackageRow({
  pkg,
  onRemove,
  removing,
}: {
  pkg: ClassroomPackageItem;
  onRemove: () => void;
  removing: boolean;
}) {
  const [confirm, setConfirm] = useState(false);

  return (
    <div className="flex items-center justify-between rounded-lg border bg-white px-4 py-3 shadow-sm">
      <div className="min-w-0">
        <p className="font-medium text-gray-900 truncate">
          {pkg.curriculum_name ?? pkg.curriculum_id}
        </p>
        <p className="text-xs text-gray-400">
          Added {new Date(pkg.assigned_at).toLocaleDateString()} · order {pkg.sort_order}
        </p>
      </div>
      {confirm ? (
        <div className="flex items-center gap-2 ml-3 shrink-0">
          <Button
            size="sm"
            variant="outline"
            className="h-7 border-red-200 text-red-600 text-xs hover:bg-red-50"
            onClick={onRemove}
            disabled={removing}
          >
            {removing ? "…" : "Remove"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-xs"
            onClick={() => setConfirm(false)}
          >
            Cancel
          </Button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setConfirm(true)}
          className="ml-3 shrink-0 rounded-md p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"
          aria-label="Remove package"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

// ── Student row ────────────────────────────────────────────────────────────────

function StudentRow({
  student,
  onRemove,
  removing,
}: {
  student: ClassroomStudentItem;
  onRemove: () => void;
  removing: boolean;
}) {
  const [confirm, setConfirm] = useState(false);

  return (
    <div className="flex items-center justify-between rounded-lg border bg-white px-4 py-3 shadow-sm">
      <div className="min-w-0">
        <p className="font-medium text-gray-900">{student.name}</p>
        <p className="text-xs text-gray-500">{student.email}</p>
        {student.grade && (
          <span className="mt-1 inline-block rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
            Grade {student.grade}
          </span>
        )}
      </div>
      {confirm ? (
        <div className="flex items-center gap-2 ml-3 shrink-0">
          <Button
            size="sm"
            variant="outline"
            className="h-7 border-red-200 text-red-600 text-xs hover:bg-red-50"
            onClick={onRemove}
            disabled={removing}
          >
            {removing ? "…" : "Remove"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-xs"
            onClick={() => setConfirm(false)}
          >
            Cancel
          </Button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setConfirm(true)}
          className="ml-3 shrink-0 rounded-md p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"
          aria-label="Remove student"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function ClassroomDetailPage() {
  const { classroomId } = useParams<{ classroomId: string }>();
  const teacher = useTeacher();
  const schoolId = teacher?.school_id ?? "";
  const queryClient = useQueryClient();

  const { data: classroom, isLoading } = useQuery({
    queryKey: ["classroom", schoolId, classroomId],
    queryFn: () => getClassroom(schoolId, classroomId),
    enabled: !!schoolId && !!classroomId,
    staleTime: 15_000,
  });

  // ── Package assignment ──
  const [curriculumId, setCurriculumId] = useState("");
  const [pkgError, setPkgError] = useState<string | null>(null);
  const { mutate: addPackage, isPending: addingPkg } = useMutation({
    mutationFn: () => assignPackageToClassroom(schoolId, classroomId, curriculumId.trim()),
    onSuccess: () => {
      setCurriculumId("");
      setPkgError(null);
      queryClient.invalidateQueries({ queryKey: ["classroom", schoolId, classroomId] });
    },
    onError: () => setPkgError("Could not add package. Check the curriculum ID and try again."),
  });

  // ── Student assignment ──
  const [studentId, setStudentId] = useState("");
  const [stuError, setStuError] = useState<string | null>(null);
  const { mutate: addStudent, isPending: addingStu } = useMutation({
    mutationFn: () => assignStudentToClassroom(schoolId, classroomId, studentId.trim()),
    onSuccess: () => {
      setStudentId("");
      setStuError(null);
      queryClient.invalidateQueries({ queryKey: ["classroom", schoolId, classroomId] });
    },
    onError: (err: unknown) => {
      const status = (err as { response?: { status?: number } })?.response?.status;
      setStuError(
        status === 404
          ? "Student not found in this school."
          : "Could not add student. Try again.",
      );
    },
  });

  // ── Remove package ──
  const { mutate: removePkg, isPending: removingPkg, variables: removingPkgId } = useMutation({
    mutationFn: (currId: string) =>
      removePackageFromClassroom(schoolId, classroomId, currId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["classroom", schoolId, classroomId] }),
  });

  // ── Remove student ──
  const { mutate: removeStu, isPending: removingStu, variables: removingStuId } = useMutation({
    mutationFn: (stuId: string) =>
      removeStudentFromClassroom(schoolId, classroomId, stuId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["classroom", schoolId, classroomId] }),
  });

  if (isLoading) {
    return (
      <div className="max-w-3xl space-y-4 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 rounded-lg" />
        <Skeleton className="h-40 rounded-lg" />
      </div>
    );
  }

  if (!classroom) {
    return (
      <div className="p-6">
        <p className="text-sm text-gray-500">Classroom not found.</p>
        <Link href="/school/classrooms" className="mt-3 text-sm text-indigo-600 hover:underline">
          ← Back to classrooms
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-6 p-6">
      {/* ── Header ── */}
      <div>
        <Link
          href="/school/classrooms"
          className="mb-3 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          All classrooms
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">{classroom.name}</h1>
          {classroom.grade && (
            <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-sm font-medium text-indigo-700">
              Grade {classroom.grade}
            </span>
          )}
          {classroom.status === "archived" && (
            <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-sm text-gray-500">
              Archived
            </span>
          )}
        </div>
        {classroom.teacher_name && (
          <p className="mt-1 text-sm text-gray-500">Lead teacher: {classroom.teacher_name}</p>
        )}
      </div>

      {/* ── Curriculum packages ── */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-indigo-600" />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
            Curriculum packages ({classroom.packages.length})
          </h2>
        </div>

        {classroom.packages.length > 0 ? (
          <div className="space-y-2">
            {classroom.packages.map((pkg) => (
              <PackageRow
                key={pkg.curriculum_id}
                pkg={pkg}
                onRemove={() => removePkg(pkg.curriculum_id)}
                removing={removingPkg && removingPkgId === pkg.curriculum_id}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400 italic">No packages assigned yet.</p>
        )}

        {/* Add package form */}
        <div className="mt-4 rounded-lg border border-indigo-100 bg-indigo-50 p-4">
          <p className="mb-2 text-xs font-medium text-gray-600">Assign a curriculum package</p>
          <div className="flex gap-2">
            <Input
              value={curriculumId}
              onChange={(e) => { setCurriculumId(e.target.value); setPkgError(null); }}
              placeholder="Curriculum ID (UUID)"
              className="flex-1 text-sm"
            />
            <Button
              size="sm"
              onClick={() => { setPkgError(null); addPackage(); }}
              disabled={addingPkg || !curriculumId.trim()}
              className="gap-1"
            >
              <Plus className="h-3.5 w-3.5" />
              {addingPkg ? "Adding…" : "Add"}
            </Button>
          </div>
          {pkgError && <p className="mt-2 text-xs text-red-600">{pkgError}</p>}
          <p className="mt-2 text-xs text-gray-400">
            Find curriculum IDs in{" "}
            <Link href="/school/curriculum" className="text-indigo-600 hover:underline">
              Curriculum
            </Link>{" "}
            or{" "}
            <Link href="/school/curriculum/content" className="text-indigo-600 hover:underline">
              Content viewer
            </Link>
            .
          </p>
        </div>
      </section>

      {/* ── Students ── */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <GraduationCap className="h-4 w-4 text-indigo-600" />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
            Students ({classroom.students.length})
          </h2>
        </div>

        {classroom.students.length > 0 ? (
          <div className="space-y-2">
            {classroom.students.map((stu) => (
              <StudentRow
                key={stu.student_id}
                student={stu}
                onRemove={() => removeStu(stu.student_id)}
                removing={removingStu && removingStuId === stu.student_id}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400 italic">No students enrolled yet.</p>
        )}

        {/* Add student form */}
        <div className="mt-4 rounded-lg border border-green-100 bg-green-50 p-4">
          <p className="mb-2 text-xs font-medium text-gray-600">Enrol a student</p>
          <div className="flex gap-2">
            <Input
              value={studentId}
              onChange={(e) => { setStudentId(e.target.value); setStuError(null); }}
              placeholder="Student ID (UUID)"
              className="flex-1 text-sm"
            />
            <Button
              size="sm"
              onClick={() => { setStuError(null); addStudent(); }}
              disabled={addingStu || !studentId.trim()}
              className="gap-1 bg-green-600 hover:bg-green-700"
            >
              <Plus className="h-3.5 w-3.5" />
              {addingStu ? "Adding…" : "Enrol"}
            </Button>
          </div>
          {stuError && <p className="mt-2 text-xs text-red-600">{stuError}</p>}
          <p className="mt-2 text-xs text-gray-400">
            Find student IDs on the{" "}
            <Link href="/school/students" className="text-green-700 hover:underline">
              Students
            </Link>{" "}
            page.
          </p>
        </div>
      </section>
    </div>
  );
}

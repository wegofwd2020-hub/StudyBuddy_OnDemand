"use client";

import { useCurriculumTree } from "@/lib/hooks/useCurriculumTree";
import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { Skeleton } from "@/components/ui/skeleton";
import { FlaskConical } from "lucide-react";
import { OfflineBanner } from "@/components/student/OfflineBanner";

export default function SubjectsPage() {
  const { data: tree, isLoading, isError } = useCurriculumTree();

  return (
    <div className="flex flex-col">
      <OfflineBanner />
      <div className="p-6 max-w-5xl space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Subjects</h1>

        {isLoading && (
          <div className="grid gap-4 sm:grid-cols-2">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-48 rounded-lg" />
            ))}
          </div>
        )}

        {isError && (
          <p className="text-sm text-red-500">Could not load curriculum. Please retry.</p>
        )}

        {tree && (
          <div className="grid gap-6 sm:grid-cols-2">
            {tree.subjects.map((subject) => (
              <Card key={subject.subject} className="border shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{subject.subject}</CardTitle>
                  <p className="text-xs text-gray-400">{subject.units.length} units</p>
                </CardHeader>
                <CardContent className="space-y-1">
                  {subject.units.map((unit) => (
                    <div
                      key={unit.unit_id}
                      className="flex items-center justify-between py-1.5 border-b last:border-0"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-700">{unit.title}</span>
                        {unit.has_lab && (
                          <FlaskConical className="h-3.5 w-3.5 text-purple-500" />
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <LinkButton
                          href={`/lesson/${unit.unit_id}`}
                          variant="ghost"
                          size="sm"
                          className="text-xs h-7"
                        >
                          Lesson
                        </LinkButton>
                        <LinkButton
                          href={`/quiz/${unit.unit_id}`}
                          variant="ghost"
                          size="sm"
                          className="text-xs h-7"
                        >
                          Quiz
                        </LinkButton>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

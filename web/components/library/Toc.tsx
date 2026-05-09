"use client";

import {
  BookOpen as BookOpenIcon,
  GraduationCap,
  ListChecks,
  FlaskConical,
} from "lucide-react";
import { LinkButton } from "@/components/ui/link-button";

interface TocProps {
  unitId: string;
  hasLab: boolean;
}

export function Toc({ unitId, hasLab }: TocProps) {
  return (
    <ol role="list" className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      <li>
        <LinkButton
          href={`/lesson/${unitId}`}
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
        >
          <BookOpenIcon className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Lesson</span>
        </LinkButton>
      </li>
      <li>
        <LinkButton
          href={`/tutorial/${unitId}`}
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
        >
          <GraduationCap className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Tutorial</span>
        </LinkButton>
      </li>
      <li>
        <LinkButton
          href={`/quiz/${unitId}`}
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
        >
          <ListChecks className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Quiz</span>
        </LinkButton>
      </li>
      {hasLab ? (
        <li>
          <LinkButton
            href={`/experiment/${unitId}`}
            variant="outline"
            size="sm"
            className="w-full justify-start gap-2"
          >
            <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Experiment</span>
          </LinkButton>
        </li>
      ) : null}
    </ol>
  );
}

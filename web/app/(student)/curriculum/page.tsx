import { redirect } from "next/navigation";

/**
 * The standalone "Curriculum Map" page duplicated both the Subjects browser and
 * the Progress tracker (feedback #472). It has been removed from the nav; this
 * route now redirects to /subjects so existing links and bookmarks (e.g. the
 * quiz "Back to Curriculum" button) keep working.
 */
export default function CurriculumMapRedirect() {
  redirect("/subjects");
}

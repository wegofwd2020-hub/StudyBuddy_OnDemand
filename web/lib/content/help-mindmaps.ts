/**
 * web/lib/content/help-mindmaps.ts
 *
 * Mermaid mindmap definitions for each user persona.
 * Each entry has a title, subtitle, and the Mermaid source string.
 *
 * Syntax used: mermaid mindmap (available in Mermaid v9+)
 * Icons reference Font Awesome via ::icon(fa fa-*) — rendered only when
 * the consuming page loads FA; otherwise they degrade gracefully.
 */

export interface PersonaMindMap {
  id: string;
  title: string;
  subtitle: string;
  color: string; // Tailwind bg class for the header card
  diagram: string;
}

export const HELP_MINDMAPS: PersonaMindMap[] = [
  // ── Super Admin ─────────────────────────────────────────────────────────────
  {
    id: "super-admin",
    title: "Super Admin",
    subtitle: "Full platform control — content, pipeline, analytics, schools",
    color: "bg-indigo-700",
    diagram: `mindmap
  root((Super Admin))
    Content Review
      Review Queue
        Filter by status
        Filter by subject
      Version Detail
        Unit list
        Approve version
        Reject version
        Publish version
        Rollback version
      Unit Viewer
        Lesson renderer
        Quiz renderer
        Tutorial renderer
        Experiment renderer
        Inline annotations
      Version Diff
        Word-level highlights
        Compare any two versions
    Pipeline
      Upload JSON
        Grade curriculum file
        Trigger build
      Job List
        Filter by status
        Sort by date
      Job Detail
        Progress percentage
        Built vs failed count
        Payload size
    Analytics
      Subscription KPIs
        Monthly subscribers
        Annual subscribers
        MRR
        Churn rate
      Struggle Report
        Worst-performing units
        Fail rate by subject
    Demo Accounts
      Student Accounts
        Approve requests
        Extend expiry
        Revoke access
      Teacher Accounts
        Approve requests
        Extend expiry
        Revoke access
    Schools
      School list
      School detail
      Status management
    Audit Log
      Auth events
      Admin actions
      Status changes
    Build Reports
      CI pipeline artifacts
      Test result history`,
  },

  // ── School Admin ─────────────────────────────────────────────────────────────
  {
    id: "school-admin",
    title: "School Admin",
    subtitle: "Manage your school — teachers, students, curriculum, subscription",
    color: "bg-blue-700",
    diagram: `mindmap
  root((School Admin))
    Dashboard
      My Classes panel
      Quick stats
        Enrolled students
        Active teachers
      Recent pipeline jobs
    Teachers
      Full roster
      Invite new teacher
      Assign grades
        Drag-and-drop grade chips
        Save assignments
      View teacher detail
    Students
      Full school roster
      Enrolment status
      Student report card
    Curriculum
      Upload JSON
        Select grade
        Upload file
      Pipeline Jobs
        Trigger new build
        Monitor progress
      Content Library
        Browse all grades
        Filter by grade
        Subject → Unit list
        Unit Viewer
          Lesson
          Tutorial
          Quiz sets
          Experiment
    Reports
      Overview
        Lessons viewed
        Quiz attempts
        Audio play rate
      Trends
        Week-over-week
        4w or 12w periods
      At-Risk students
      Unit Performance
      Engagement metrics
      Feedback from students
      Export CSV
    Alerts
      Unacknowledged alerts
      Alert thresholds
    Digest Settings
      Email schedule
      Subscribe or unsubscribe
    Subscription
      Current plan
      Upgrade plan
      Cancel subscription
    Settings
      School profile
      Contact email`,
  },

  // ── School Teacher ───────────────────────────────────────────────────────────
  {
    id: "school-teacher",
    title: "School Teacher",
    subtitle: "Browse content and monitor student progress for your assigned grades",
    color: "bg-teal-700",
    diagram: `mindmap
  root((School Teacher))
    Dashboard
      My Classes
        Assigned grades shown
      Quick class stats
    Content Library
      Filtered to assigned grades
      Grade filter pills
      Browse by subject
      Subject → Unit list
        Unit Viewer
          Lesson text
          Tutorial sections
          Quiz questions
          Experiment steps
    Students
      Grade-scoped roster
      Individual student report
        Units completed
        Quiz scores
        Lesson views
    Reports
      Overview
        Enrolled count
        Lessons viewed
        Quiz attempts
      Trends
        4-week activity
        12-week activity
      At-Risk
        Students below threshold
      Unit Performance
        Per-unit stats
        Struggle flag
      Engagement
        Audio play rate
        Return rate
      Feedback
        Student comments by unit
    Alerts
      Threshold alerts
      Acknowledge alerts
    Digest Settings
      Weekly email digest
    Accessibility
      Dyslexia font toggle
        Eye button in header
        Alt + D shortcut
        Persists across sessions`,
  },

  // ── Demo Student ─────────────────────────────────────────────────────────────
  {
    id: "demo-student",
    title: "Demo Student",
    subtitle: "Try StudyBuddy free — no sign-up required, 30-day access",
    color: "bg-green-700",
    diagram: `mindmap
  root((Demo Student))
    Get Access
      Homepage
        Click Try it free
      Request form
        Enter email
        Submit request
      Email verification
        Check inbox
        Click magic link
      Demo login
        Enter email
        Enter password
        Auto-assigned Grade 8
    Curriculum Map
      Browse subjects
        Mathematics
        Science
        Technology
        Engineering
      Select a unit
    Learning Flow
      Lesson
        Structured text
        Key concepts
        Examples
      Tutorial
        Step-by-step sections
        Tabbed layout
      Quiz
        Multiple choice
        Immediate feedback
        Score at the end
      Experiment
        Lab procedure
        Materials list
        Expected results
    Progress
      Streak counter
      Unit history
      Quiz scores
    Accessibility
      Dyslexia font
        Eye button in header
        Alt + D shortcut
    Limitations
      No audio download
        Full account required
      Grade 8 content only
        Fixed demo grade
      Settings locked
        Demo accounts read-only`,
  },

  // ── Full Student ─────────────────────────────────────────────────────────────
  {
    id: "full-student",
    title: "Full Student",
    subtitle: "Complete STEM learning experience with your school or subscription",
    color: "bg-purple-700",
    diagram: `mindmap
  root((Full Student))
    Enrolment
      School enrolment
        Receive enrolment code
        Join school roster
      Personal subscription
        Choose plan
        Stripe checkout
        Grade unlocked
    Curriculum Map
      School curriculum
        School-uploaded content
        Custom grade mapping
      Default platform content
        Grades 5 through 12
        All STEM subjects
    Learning Flow
      Lesson
        Full text + diagrams
        Audio playback
          Streamed from CDN
          MP3 offline cache
      Tutorial
        Deep-dive sections
        Code and formulas
      Quiz
        Three quiz sets per unit
        Attempt tracking
        Pass or fail tracking
      Experiment
        Full lab guide
        Materials and steps
    Progress
      Streak counter
        Daily learning streak
      Unit history
        Attempts per unit
        Best score
      My Stats
        Total lessons
        Total quizzes
        Subject breakdown
    Account
      Settings
        Display name
        Language
          English
          French
          Spanish
        Notifications
          Streak reminders
          Weekly summary
          Quiz nudges
        Accessibility
          Dyslexia font toggle
      Subscription
        Plan status
        Upgrade or cancel
    Offline Access
      Mobile app
        Download units
        Sync progress`,
  },
];

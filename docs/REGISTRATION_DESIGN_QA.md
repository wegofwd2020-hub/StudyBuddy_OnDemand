# Registration & Onboarding Design — Q&A

> **Purpose:** Capture design intent before implementation begins.
> Fill in the **Answer:** fields below. Once complete this document
> becomes the source of truth for the registration flow design.
>
> **Context:** Three first-class registration paths — School, Teacher,
> Student — each with curriculum setup, a billing gate, pipeline
> execution, and content access.

---

## 1. Registration Hierarchy

**Q1.** When a **School** registers, is the first person who registers
automatically the `school_admin`? Or do they choose a role during signup?

> **Answer:**
The first person who registers will be set as shool_admin.
The school self-registration is still public.
The school self registers, no requirement for platform admin. 
---

**Q2.** Can a **Teacher** exist in two modes — independently registered
AND later affiliated with a school — or once they register as independent
they stay independent permanently?

> **Answer:**
Not with the same email id. If a teacher needs to be in 2 places they need to use different email ids.
---

**Q3.** When a teacher registers independently, can they later be
"claimed" by a school (i.e., their account absorbed into a school
account)? If yes, what happens to their existing curriculum and students?

> **Answer:**
No, email id needs to be unique. 
---

## 2. Adding Sub-Accounts

**Q4.** When a school or teacher **adds a student**, does the student
receive an email invite and self-complete their own profile? Or does the
school/teacher create the full credentials on their behalf?

> **Answer:**
No. When a student is added to by school with their email id, the email id will receive a notification with a default passord to access the site. for the first time they access they will be provided with a page to reset the default password.

The "School" would also need a admin page where they can reset the user password.
---

**Q5.** Same question for a **school adding a teacher** — is it an invite
flow (teacher receives email + sets own password) or does the school admin
create the account directly?

> **Answer:**
The addition of a teacher by school, is managed in a similar manner to the adding a student.
---

**Q6.** Does a **student added by a teacher** have a different app
experience than a **student who self-registers and then enrols in a
school**? If yes, what differs?

> **Answer:**
There is no self registration concept for the teacher or student. The schools adds the teachers and students. The school admin also is responsible to assigning the student to a grade program. For now a student can be assigned to only one grade program.

The independent teaher/student will be treated like a shcool on their first regitration with unique email id. that ID could be used downwards as a teacher/student.
---

## 3. Curriculum Setup

**Q7.** "Build their own curriculum JSON" — which of these did you have
in mind, or a combination?

- (a) A **form-based UI** where they fill in subject / unit / title
  fields and the app constructs the JSON
- (b) A **raw JSON editor** (upload or paste)
- (c) A **plain-English description** → AI structures the JSON for them
- (d) Something else

> **Answer:**
Only options (a) for now please.
---

**Q8.** "Consume an existing Curriculum JSON" — which of these applies?

- (a) Choose from the **platform's pre-built grade curricula** (Grade 5–12 STEM defaults)
- (b) **Import a JSON file** built by someone else (e.g., another school shares their curriculum)
- (c) **Both** of the above


> **Answer:**
Option (a) please. I am hoping we provide a set of JSON with different combination of subjects we may start with Grade curriculum of STEM and later move to different combinations.
---

**Q9.** If a teacher or school uploads their own curriculum, does it
require **admin approval** before the pipeline can run? Or does it go
straight to content generation?

> **Answer:**
There needs to be a approval process. The approval is always associated with that specific "school-admin". The platform admin will have support functionality when they require escalation path when their "school-admin" is temporarily not available. We may need to provide more then 1 persona to be associated with the role of "school-admin".
---

## 4. Billing Gate

**Q10.** Is the billing model **pay-per-pipeline-run** (usage/credit
model) or **subscribe first, runs included in the plan**?

> **Answer:**
The default subscription does not include cose for the pay-per-pipeline-run. That cost is part of the need for approval by the school admin.
---

**Q11.** If subscription-based: does the billing gate during pipeline
setup just **confirm an active plan exists**, or does the user **enter
card details right there** in the pipeline trigger flow if they don't
have one yet?

> **Answer:**
Any subscription to the SaaS solution needs the billing information which will be used for pipeline-run, and used for pipeline-run.
---

**Q12.** Should the user see a **cost/usage estimate** before confirming
a pipeline run? For example:
> *"This will generate 4 subjects × 8 units × 3 languages ≈ 96 API
> calls. Estimated cost: $X. Confirm?"*

> **Answer:**
Yes, we would need to provide with a cost estimate to the school-admin to confirm before the pipeline-run.
---

## 5. Content Access

**Q13.** When you say students and teachers can "access study pages for
whatever materials has already been made available" — is this via the
existing **web portal**, the **mobile app**, or a new unified experience?

> **Answer:**
Using existing web-portal and mobile-app
---

**Q14.** If a teacher or school registers but has **not yet run the
pipeline** (no content generated), can they give students access to the
platform's **default curriculum** (Grade 5–12 STEM) in the meantime?

> **Answer:**
The teacher or school will need to "pull-in" the curriculum ad they deem appropriate to a "Class room". They will also assign students to the "class rom"
---

## 6. Open Notes

> Use this space for anything that doesn't fit the questions above —
> edge cases, constraints, things you want to flag for later.

---

*Document created: 2026-04-11*
*Status: Awaiting answers*

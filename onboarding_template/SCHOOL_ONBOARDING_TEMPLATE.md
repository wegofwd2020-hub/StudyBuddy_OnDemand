# StudyBuddy — School Onboarding Intake

Please fill this in and send it back. We'll use it to create your school plus all
teacher and student accounts so your team can start testing. Each person receives
an email with a temporary password and is asked to set their own on first login.

---

## 1. School details

| Field | Your answer |
|---|---|
| **School name** | _e.g. MilfordWaterford_ |
| **Country** | _e.g. US / CA / IN_ |
| **School contact email** | _receives system notices; must be a real, working address_ |
| **School admin #1 email** | _the main administrator (manages users + curriculum)_ |
| **School admin #2 email** *(recommended)* | _a backup admin, so you're never locked out_ |

> A **school admin** can also be a teacher. List their email here **and** in the
> Teachers sheet if they also teach a class.

---

## 2. Teachers  →  fill in **`teachers.csv`**

| Column | Required? | Notes |
|---|---|---|
| `first_name` | ✅ | |
| `last_name` | ✅ | |
| `email` | ✅ | Must be **real, working, and unique** — they get a login email here. |
| `role` | ✅ | `teacher` **or** `school_admin` (admins can also teach). |
| `grades_taught` | ✅ | One or more grades they teach, e.g. `8` or `8;11`. Grades 5–12. |
| `stream` | only G11/G12 | `Science` / `Commerce` / `Humanities` / `English` / `STEM`. Leave blank for grades 5–10. |
| `class_section` | ✅ | The class this teacher runs, e.g. `Grade 8 - Section A`. Use the **same exact label** on the students in that class. Multiple classes → separate with `;`. |
| `subject` | optional | e.g. `Mathematics`, `Physics`. |
| `phone` | optional | Any format; placeholder is fine. |

## 3. Students  →  fill in **`students.csv`**

| Column | Required? | Notes |
|---|---|---|
| `first_name` | ✅ | |
| `last_name` | ✅ | |
| `email` | ✅ | Must be **real, working, and unique** — they get a login email here. |
| `grade` | ✅ | A single grade, 5–12. |
| `stream` | only G11/G12 | `Science` / `Commerce` / `Humanities` / `English` / `STEM`. Leave blank for grades 5–10. |
| `class_section` | ✅ | Which class this student is in, e.g. `Grade 8 - Section A`. Must **exactly match** a `class_section` used by a teacher (same spelling/spacing). |
| `phone` | optional | Any format; placeholder is fine. |

---

## Rules (so onboarding doesn't bounce)

1. **One email = one person = one role.** A person is **either** a teacher **or** a
   student — never both. Don't reuse an email across the two sheets or within a sheet.
2. **Emails must be valid and working** — the system sends each account a one-time
   password to that address; they reset it on first login.
3. **Streams apply only to Grades 11 & 12.** For grades 5–10 leave `stream` blank.
   A Grade 11/12 student or teacher should have a stream so they get the right
   subjects (e.g. Science → Physics/Chemistry/Biology/Math).
4. **At least one `school_admin`** is required; two is strongly recommended.
5. **`class_section` is the glue for classes.** We create one class per distinct
   `class_section`, make the teacher who lists it that class's teacher, assign the
   grade's curriculum, and enrol every student who lists the same label. So the
   label must be **spelled identically** on the teacher and their students (e.g.
   `Grade 8 - Section A` everywhere — not `8A` on some rows and `Section A` on
   others). A class's students should all share its grade/stream.
6. Delete the `EXAMPLE …` rows in each CSV before sending back.

Questions? Just reply and we'll help. Thanks!

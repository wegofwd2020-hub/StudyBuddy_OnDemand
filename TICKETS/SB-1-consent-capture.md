# SB-1 — Verifiable parental consent (B2C) + school consent capture (B2B)

**Labels:** P0, compliance, COPPA, FERPA
**Refs:** studybuddy-docs/compliance/COPPA_FERPA_COMPLIANCE.md §2/§3

## Acceptance criteria
- B2C signup cannot collect a child's PII until verifiable parental consent is captured and recorded.
- B2B (school-provisioned) path records the school's consent/authorization.
- Consent records are auditable (who/when/scope).

## Implementation notes
- Extend the auth flow; gate child data collection on a consent check. Tests with mock parent/school flows.

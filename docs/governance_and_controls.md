# Governance, Data Integrity, and Application Controls

This note documents how the control governs the completeness and accuracy of the
information it consumes and produces, how changes to the control are managed, and
the application controls embedded in it. It is written to support an auditor's
decision to rely on the automated control.

## 1. Completeness and accuracy of inputs (IPE)

The control consumes three data extracts: the HR termination roster (the
population) and one account extract per in-scope system. Because a conclusion is
drawn from these, they are Information Produced by the Entity (IPE) and must be
complete and accurate for the control to be relied upon.

| Input | Role | Completeness and accuracy evidence |
|-------|------|------------------------------------|
| HR termination roster | Authoritative population of terminated workers for the period | Date-bounded extract with the query parameters and run timestamp retained; row count reconciled to the HRIS termination report; no post-extract filtering that removes rows |
| System account extracts (CRM, ERP, SSO) | Population of accounts to test against | Pulled directly from each source system; field-to-model mapping documented in `config.yaml`; status vocabulary (active/disabled) mapped explicitly per system; row counts captured per run |

Two design features protect input integrity:

- **Automated input edit checks (fail-closed).** Before the review runs,
  `src/integrity.py` validates each extract: it confirms every column the config
  maps is physically present, counts rows read (population completeness), and
  flags rows with blank key fields or unparsable dates (accuracy). If a mapped
  column is missing, the run aborts with a distinct exit code and records the
  failure in the summary, so the control never reports a clean result on inputs
  it could not validate.
- **Coverage is reconciled.** Every terminated identity is either correlated to
  one or more accounts or reported as unmatched (see the run summary counts), so
  no member of the population is silently dropped from the review.
- **Weak matches are not trusted.** Accounts tied to a person by name only are
  flagged (rule R4) for manual confirmation rather than being treated as a
  reliable match, which prevents a false correlation from either raising or
  suppressing a finding.

POC limitation: the sample data is static and fictional. In production, C&A is
established by retaining the extract queries, reconciling row counts to source,
and generating extracts through an access-restricted, repeatable process.

## 2. Completeness and accuracy of outputs (IPE)

The exception log and the JSON and Markdown summaries are themselves IPE, because
they support the audit conclusion.

- **Completeness.** Evaluation is deterministic over the full correlated
  population, with no sampling. The summary reconciles totals: the findings count
  equals the number of rows in the exception log and equals the sum of the
  per-severity counts.
- **Accuracy.** Each finding is produced by a named, unit-tested rule (R1 to R4).
  The test suite asserts rule behavior and the severity-based exit-code logic, so
  the outputs are traceable to tested logic rather than ad hoc calculation.
- **Reproducibility and re-performance.** The output is a pure function of the
  input extracts, the configuration, and the code version. Recording the git
  commit SHA, `config.yaml`, and the extracts lets an auditor re-perform the run
  and obtain identical results.
- **Evidence integrity.** Each run's log and summary are retained as a timestamped
  artifact, and the exception issue provides an independent, timestamped record
  of when each exception was raised, routed, escalated, and closed.

## 3. Change management over the control

Reliance on an automated control depends on the control being unchanged, or on
its changes being controlled. Changes to this control are governed as follows:

- **Code ownership.** `.github/CODEOWNERS` requires the control owner's review on
  any pull request that touches the detection logic (`src/detection.py`),
  identity correlation (`src/correlation.py`), the control configuration
  (`config.yaml`: de-provisioning SLA, field and status mappings, system owners,
  remediation SLA, escalation owner), and the monitoring workflows.
- **Branch protection (to enable on the repository).** Require a pull request to
  merge to `main`, require the CI checks (tests) to pass, require code-owner
  review, and disallow direct pushes. This prevents unreviewed changes to the
  rules or parameters.
- **Audit trail.** Version control provides a complete who, what, and when record
  of every change to the detection rules and control parameters.
- **Separation of parameters from logic.** Routine changes such as adjusting an
  SLA, onboarding a system mapping, or updating an owner are config-only and
  reviewable without touching the detection logic; logic changes are isolated to
  the detection and correlation modules.

This supports a benchmarking strategy for the automated control under PCAOB
AS 2201: once the control is tested effective, disciplined change management and
a retained baseline allow reliance across periods without full re-performance
each period. It aligns with the NIST SP 800-53 configuration-management (CM)
family.

Honest note: in a single-maintainer repository, CODEOWNERS is a statement of
intent, because a sole owner cannot supply independent review. Enforcement
requires at least one additional reviewer (or a governance team) plus branch
protection.

## 4. Key IT application control (ITAC) considerations

The tool functions as an automated control, so the standard ITAC categories
apply. The table maps each category to how it is handled here and to the
hardening a production deployment would add.

| ITAC category | In this repository | Production hardening |
|---------------|--------------------|----------------------|
| Input controls | Automated edit checks in `integrity.py`: mapped-column presence (fail-closed), row counts, blank-key and unparsable-date flags; unmatched identities flagged, not dropped | Reject-and-log per row on schema violations; automated row-count reconciliation to source at ingest |
| Processing controls | Deterministic identity correlation (email, then name with name-only flagged); rule evaluation R1 to R4; SLA computed from termination date; deterministic severity assignment; no manual intervention in the calculation | Governed canonical identity mapping for collisions, shared, and service accounts |
| Output controls | Count reconciliation (findings equal log rows equal severity sum); full-population processing with no sampling; retained, timestamped evidence | Immutable evidence store with retention policy; hash of each artifact |
| Configuration and parameter controls | Business parameters (de-provisioning SLA, remediation SLA, mappings, status vocab, owners, escalation contact) externalized to `config.yaml` and change-controlled; segregated from code | Parameter change approvals tied to the change-management workflow above |
| Interface and data-transfer controls | Out of scope for the POC (static CSVs) | Authenticated, least-privilege extract generation; integrity of the extract in transit; run timestamp and row counts captured |

## 5. Auditor reliance posture

To rely on this control, an auditor would confirm three things: the completeness
and accuracy of the HR population and the system extracts (IPE); that the
detection logic and its parameters were effective and were not changed outside of
controlled change management (supported by the test suite, CODEOWNERS, and
version history); and that identified exceptions were surfaced, routed to the
owning system's admin, aged, escalated, and remediated (supported by the
exception queue and escalation trail). The repository is organized so that each
of these is demonstrable rather than asserted.

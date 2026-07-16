# Production Considerations

This repository is a proof of concept on sanitized, static data. Moving it to a
production control is mostly three things: real data feeds, a hardened integrity
and security posture, and operationalizing it as a control with owners and
retained evidence. The detection logic and control design carry over unchanged;
what follows is what a real deployment adds around them.

## 1. Data ingestion

Each static CSV becomes a live, authenticated extract. The config-driven field
mapping already models this, so the change is replacing the file read with a
per-system client, not rewriting the logic.

| Source | Production feed | Notes |
|--------|-----------------|-------|
| HR system of record | API pull of the terminated population for a defined window | Authoritative population; completeness matters most here |
| CRM / ERP / SSO / other apps | API or governed report export, one thin adapter per system | Adapter maps native fields to the existing normalized model |
| Orchestration | Scheduler (cron, Airflow, serverless) drives runs on cadence | Each run's inputs and outputs retained |

## 2. Data integrity and IPE completeness and accuracy

The fail-closed input checks already exist; production strengthens provenance.

- Retain each source's extract query, parameters, run timestamp, and row counts,
  and reconcile counts back to the source so the population is demonstrably
  complete.
- Establish a governed canonical identity mapping (a stable employee ID) rather
  than email-then-name matching. This is the most important accuracy upgrade;
  shared accounts, service accounts, contractors, and name collisions otherwise
  create false matches or gaps.
- Define per-system and per-termination-type SLAs. Involuntary terminations often
  require immediate revocation, unlike a standard voluntary exit.

## 3. Security and access

- Read-only, least-privilege credentials to each source system, held in a secrets
  manager, never in the repository.
- The exception log contains employee names and access data. Treat it as
  sensitive HR and security data with defined handling, storage, and access
  controls.
- The extract-generation identity itself becomes an account auditors will
  scrutinize; scope and monitor it accordingly.

## 4. Operating it as a control

- Assign real owners: a control owner and per-system remediation owners (already
  modeled; replace the placeholder handles with real people or teams).
- Route notifications to production channels: a ticketing system such as
  ServiceNow or Jira in place of GitHub issues, plus chat and email.
- Define the human remediation workflow: who acts on an exception, the expected
  turnaround, and the escalation path as it ages. The escalation logic exists;
  the process around it must be defined and documented.
- Retain per-run evidence in a durable, access-controlled store with a defined
  retention period. These are audit artifacts.

## 5. Change management and validation

- Enforce the CODEOWNERS and branch-protection model with independent reviewers,
  so detection logic and SLAs cannot change without sign-off.
- Validate before relying on it: run against a known period and confirm it catches
  the exceptions you already know about without excessive false positives. Retain
  that validation as evidence.
- Under PCAOB AS 2201, once tested effective and change-controlled, the automated
  control can be benchmarked and relied upon across periods without full
  re-performance each period, provided change management holds.

## Suggested rollout

Start with one or two systems and a single HR feed. Run it in parallel with the
existing manual review for a period to build confidence and tune the SLAs and the
identity matching, then expand system coverage. Treat the first months as
validation rather than reliance.

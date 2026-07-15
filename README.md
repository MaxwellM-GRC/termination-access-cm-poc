# Termination Access Review — Proof of Concept

![CI](https://github.com/MaxwellM-GRC/termination-access-cm-poc/actions/workflows/ci.yml/badge.svg)

**Automated detection of terminated employees who still hold live system access
— across applications, not one system at a time.**

When someone leaves, their access is supposed to be removed everywhere, quickly.
In practice the identity provider often gets disabled on schedule while a local
account in a CRM or ERP quietly stays active. A review that checks each system in
isolation sees a clean IdP and moves on. The standing access in the ERP never
surfaces.

This POC correlates every terminated identity to its accounts in *all* in-scope
systems, then tests four assertions and produces an audit-ready exception log. It
maps to the SOX ITGC over access de-provisioning (PCAOB AS 2201; COBIT DSS05;
NIST SP 800-53 AC-2).

> ⚠️ **Sanitized.** All system names, people, and data here are fictional
> (`Acme Foods`, `Meridian HR`, `Nimbus CRM`, `Coranto ERP`, `Keystone SSO`).
> No real client, employer, or production data is included.

---

## The problem it catches

The three source extracts are intentionally inconsistent — different column
names, different words for "active" vs "disabled" — because real ones are. Two
cases in the sample data show why per-system review misses things:

- **Dana Whitfield** — Keystone SSO was disabled on time, but her **Nimbus CRM**
  account is still active with a login *after* her termination date.
- **Sam Okafor** — SSO disabled on time, but his **Coranto ERP** account is still
  active. A per-app SSO review would call this clean.

Only correlating identities across all three systems surfaces both.

## What it checks

| Rule | Assertion | Flags | Severity |
|------|-----------|-------|----------|
| R1 | Access removed | Account still active after termination | Critical |
| R2 | Removal timely | Account disabled after the SLA deadline | High |
| R3 | No post-term use | Activity dated after termination | Critical |
| R4 | Identity reliable | Account matched by name only — confirm manually | Info |

## How it works

```
HR roster ─┐
CRM  ──────┤─►  loaders  ─►  correlation  ─►  detection  ─►  reporting
ERP  ──────┤   (normalize   (one identity     (R1–R4)       (console +
SSO  ──────┘    schemas)     across systems)                 CSV log)
```

- **loaders** map each system's quirky columns/status words onto one model.
- **correlation** stitches accounts to one HR identity by email, then by name
  (name-only matches are flagged, never trusted silently).
- **detection** raises a named finding per assertion, traceable for audit.
- **reporting** prints a summary and writes a timestamped exception log.

## Quick start

```bash
pip install -r requirements.txt

# Run the review and write an exception log
python -m src.main --out exception_log.csv

# Tighten the SLA to 5 days
python -m src.main --sla 5

# Run the tests
python -m pytest -q
```

## Sample output

```
INPUT INTEGRITY (completeness & accuracy of source data)
------------------------------------------------------------------------
  [ OK ] HR roster: 9 row(s)
  [ OK ] Nimbus CRM: 6 row(s)
  [ OK ] Coranto ERP: 5 row(s)
  [ OK ] Keystone SSO: 9 row(s)
========================================================================
TERMINATION ACCESS REVIEW — RUN SUMMARY
Terminated employees reviewed : 9
Accounts ingested             : 20
Identities correlated         : 9
Terminated w/ no account found: 0
------------------------------------------------------------------------
Findings: 10  (critical 9, high 1, info 0)
------------------------------------------------------------------------
[CRITICAL] R1_OPEN_ACCESS       Nadia Farouk   Nimbus CRM
           -> Account 'nfarouk' is still ACTIVE 3 days after termination.
[CRITICAL] R3_POST_TERM_ACTIVITY Sam Okafor    Coranto ERP
           -> Activity recorded 2026-05-15, after termination on 2026-04-28.
[HIGH    ] R2_LATE_DEPROVISION  Grace Chen     Nimbus CRM  [+12d]
           -> Account disabled 2026-05-30, 12 day(s) past the 7-day SLA deadline.
```

The review is fail-closed: it validates the completeness and accuracy of every
input extract first and, if a mapped column is missing, aborts before drawing any
conclusion. Exit codes: `0` clean, `2` actionable findings (with `--fail-on`),
`3` input validation failed.

> R1 "days active" is measured from the termination date to the run date, so
> those figures grow over time; the sample data is a static snapshot.

The exception log (`exception_log_*.csv`) is one row per finding — the artifact
you would hand to an external auditor.

## Continuous monitoring

This is built to run on a cadence, not once. A point-in-time termination review
tells you about the access gaps that existed on the day someone happened to look;
run on a schedule against fresh extracts, the same logic becomes a continuously
monitored control that surfaces each gap as it arises and builds a persistent
exception trail as audit evidence.

Two workflows separate concerns:

- **`ci.yml`** runs the test suite (and a smoke run) on every push and PR. This
  is what the badge above tracks, so it stays green while the code is healthy.
- **`access-review.yml`** is the monitoring job. It runs on a weekday schedule
  (`cron: "0 7 * * 1-5"`), on demand, and on merge to `main`.

When the scheduled review finds **critical or high** exceptions, it fires a
notification chain:

1. **Evidence** — the exception log, a JSON summary, and a Markdown report are
   uploaded as a downloadable run artifact.
2. **Exception queue** — a rolling GitHub Issue (label `access-exception`) is
   opened, or commented on if one is already open, so exceptions have a
   timestamped, assignable, closeable record. Each in-scope system has an
   `owner` in `config.yaml` (a GitHub `@user` or `@org/team`); the issue
   @mentions and best-effort assigns the owner of whichever system the exception
   landed in, so a stale CRM account routes to the CRM admin and an SSO gap
   routes to the IAM admin. (Assignees must be repo collaborators; the @mention
   notifies anyone, including teams.)
3. **Chat alert** — an optional Slack message, sent only if you configure a
   `SLACK_WEBHOOK_URL` repository secret (Settings → Secrets and variables →
   Actions). Without the secret this step is skipped, not failed.
4. **Email** — the monitoring run intentionally exits red on actionable findings,
   which triggers GitHub's built-in email to the repo owner for a failed
   scheduled run.

A separate **`escalation.yml`** workflow ages the open exception issues daily. Any
that stay open past the remediation SLA (`config.yaml` → `remediation.issue_sla_days`)
get an `escalated` label and a comment tagging the `escalation_owner` (typically
the control owner above the system admins). This gives the control a full
exception-aging trail: detection → assignment → escalation.

Locally or in another scheduler, the same behavior is driven by flags:

```bash
python -m src.main --out log.csv --summary-json summary.json \
  --issue-md issue.md --fail-on high   # exits non-zero on high+ findings
```

In production the same entry point would be pointed at live system extracts and
driven by cron, Airflow, or an orchestration platform, with each run's log
retained as dated evidence. This maps to the continuous-monitoring control family
in NIST SP 800-53 (CA-7) and the ongoing-monitoring intent of COBIT 2019 DSS05.

## Onboarding another system

No code change. Add a block under `systems:` in `config.yaml` mapping the new
extract's columns and its active/disabled vocabulary onto the model. The
correlation and detection layers pick it up automatically.

## Repo layout

```
.github/workflows/
  ci.yml               Tests + smoke run (badge tracks this)
  access-review.yml    Scheduled monitoring: artifact, issue, Slack, alert
  escalation.yml       Ages open exception issues past the remediation SLA
.github/CODEOWNERS      Change-management review over control logic + config
config.yaml            SLA + per-system schema mappings (audit-reproducible)
data/                  Fictional HR roster + 3 system account extracts
src/
  models.py            Normalized data structures
  integrity.py         Input edit checks (IPE completeness/accuracy), fail-closed
  loaders.py           Read + normalize each extract
  correlation.py       Identity correlation across systems
  detection.py         Control rules R1–R4
  reporting.py         Console summary, CSV log, JSON + Markdown summaries
  main.py              CLI orchestrator (--out / --summary-json / --fail-on)
tests/                 Unit tests: correlation, rules, integrity, outputs, exit codes
docs/
  control_narrative.md         Control write-up + framework mapping
  governance_and_controls.md   IPE C&A, change management, ITAC considerations
```

## Control mapping

PCAOB AS 2201 · COSO Principle 11 · COBIT 2019 DSS05/DSS06 ·
NIST SP 800-53 AC-2 & CA-7 · ISO/IEC 27001 A.5.18. Full narrative in
[`docs/control_narrative.md`](docs/control_narrative.md).

For data-integrity (IPE completeness and accuracy), change management, and ITAC
considerations, see
[`docs/governance_and_controls.md`](docs/governance_and_controls.md).

## Scope note

This is a focused proof of concept, not a production platform. It demonstrates
the approach — cross-application identity correlation for a single ITGC — on
fictional data. Production concerns (API ingestion, governed identity mapping,
per-system SLAs, change control over the tool itself) are noted in the control
narrative.

## License

MIT — see [LICENSE](LICENSE).

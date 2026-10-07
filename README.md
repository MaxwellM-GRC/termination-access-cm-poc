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
systems, then tests four assertions and produces a reviewable exception log with
supporting evidence. It illustratively aligns with the SOX ITGC over access
de-provisioning (PCAOB AS 2201; COBIT DSS05; NIST SP 800-53 AC-2); company scope,
applicability, and reliance require validation.

> ⚠️ **Sanitized.** All system names, people, and data here are fictional
> (`Acme Foods`, `Meridian HR`, `Nimbus CRM`, `Coranto ERP`, `Keystone SSO`).
> No real client, employer, or production data is included.

---

## The problem it catches

The HR roster and three account extracts are intentionally inconsistent —
different column names, different words for "active" vs "disabled" — because
real ones are. Two cases in the sample data show why per-system review misses
things:

- **Dana Whitfield** — Keystone SSO was disabled on time, but her **Nimbus CRM**
  account is still active with a login *after* her termination date.
- **Sam Okafor** — SSO disabled on time, but his **Coranto ERP** account is still
  active. A per-app SSO review would call this clean.

Only correlating identities across all three systems surfaces both.

## What a company would need to implement this

The POC supplies the detection pattern; a company supplies and approves the
operating context below.

| Implementation need | Company input or decision |
|---|---|
| Authoritative populations | Governed HR termination data and complete account populations from every in-scope system |
| Identity matching | A stable workforce identifier and rules for contractors, shared accounts, service accounts, and ambiguous matches |
| Control scope and policy | Financial-reporting scope, systems, termination types, approved removal timeframes, severity, and review cadence |
| Secure integration | Read-only connectors, least-privilege credentials, protected data transfer, and monitored service identities |
| Evidence and cases | Durable access-controlled evidence storage plus an approved ticket or case platform with retention, response, escalation, and closure controls |
| Accountable roles | Product owner, control owner, system owners, independent reviewer, and assurance stakeholders |
| Validation | A bounded historical pilot reconciled to source totals and known cases before control reliance |

The [product profile](docs/poc_product_profile.md) provides the five-minute value
and risk review. [Production considerations](docs/production_considerations.md)
describes the implementation steps in more detail.

## What this control tests

| Control ID | Control description | Severity |
|---------|---------------------|----------|
| TA-01 | Confirm access was removed. Flags an account still active after termination. | Critical |
| TA-02 | Confirm access was removed on time. Flags an account disabled after the allowed deadline. | High |
| TA-03 | Confirm there was no use after termination. Flags activity dated after the termination date. | Critical |
| TA-04 | Confirm the identity match is reliable. Flags an account matched by name only for manual confirmation. | Info |

## How it works

```
HR roster ─┐
CRM  ──────┤─►  loaders  ─►  correlation  ─►  detection  ─►  reporting
ERP  ──────┤   (normalize   (one identity     (TA-01–04)    (console +
SSO  ──────┘    schemas)     across systems)                 CSV log)
```

- **loaders** map each system's quirky columns/status words onto one model.
- **correlation** stitches accounts to one HR identity by email, then by name
  (name-only matches are flagged, never trusted silently).
- **detection** raises a named finding per assertion, traceable for audit.
- **reporting** prints a summary and writes a timestamped exception log.

## Quick start

Prerequisites: Python 3.10–3.13, Git, and network access to install the pinned
shared core package.

```bash
pip install -r requirements.txt

# Run the review and write an exception log
python -m src.main --out exception_log.csv

# Demo-only override: test a 5-day SLA without editing config.yaml
python -m src.main --sla 5

# Run the tests
python -m pytest -q
```

The command-line SLA override is for local scenario testing. A production run
should use an approved, version-controlled parameter or retain the override and
its approval in the run evidence.

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
Findings: 14  (critical 9, high 5, info 0)
------------------------------------------------------------------------
[CRITICAL] TA-01                Nadia Farouk   Nimbus CRM
           -> Account 'nfarouk' is still ACTIVE 3 days after termination.
[CRITICAL] TA-03                Sam Okafor     Coranto ERP
           -> Activity recorded 2026-05-15, after termination on 2026-04-28.
[HIGH    ] TA-02                Marcus Lindqvist Coranto ERP [+1d]
           -> Account disabled 2026-05-03, 1 day(s) past the 0-day SLA deadline.
[HIGH    ] TA-02                Grace Chen     Nimbus CRM  [+12d]
           -> Account disabled 2026-05-30, 12 day(s) past the 7-day SLA deadline.
```

The review stops when an extract fails its structural integrity checks. It tests
mapped-column presence, required keys, date formats, recognized account states,
and whether required populations are unexpectedly empty; it also records row
counts, provenance, and content hashes. These checks do not prove that a source
system returned its complete authoritative population. Production reliance
requires the captured counts and query parameters to be reconciled to each
source system. Exit codes: `0` clean, `2` actionable findings (with `--fail-on`),
`3` input validation failed.

> TA-01 "days active" is measured from the termination date to the run date, so
> those figures grow over time; the sample data is a static snapshot.

The exception log (`exception_log_*.csv`) is one row per finding and one
component of the evidence package available for auditor review alongside the
source validation, configuration, code revision, run summary, and human
response records.

## Continuous monitoring

This is built to run on a cadence, not once. A point in time termination review
tells you about the access gaps that existed on the day someone happened to look;
run on a schedule against fresh extracts, the same logic becomes a continuously
monitored control that surfaces each gap as it arises. The included GitHub
workflow demonstrates this pattern with fictional files; it is not a production
evidence repository.

Two workflows separate concerns:

- **`ci.yml`** runs the test suite (and a smoke run) on every push and PR. This
  is what the badge above tracks, so it stays green while the code is healthy.
- **`access-review.yml`** is the monitoring job. It runs on a weekday schedule
  (`cron: "0 7 * * 1-5"`), on demand, and on merge to `main`.

That weekday schedule matches the POC control metadata. The production cadence
must be approved against company policy and be capable of meeting the shortest
configured removal timeframe, including immediate or intraday requirements.

When the scheduled review finds **critical or high** exceptions, it fires a
notification chain:

1. **Evidence** — the exception log, a JSON summary, and a Markdown report are
   uploaded as a downloadable run artifact. The outputs include the code
   revision used for the run.
2. **Individual exception cases** — every actionable finding receives a stable
   finding ID and its own GitHub Issue (`access-exception-case`). The case
   records its prescribed remediation, mitigation/lookback, root cause prompt,
   closure evidence checklist, owner, and aging. If a closed finding recurs, its
   case is reopened. Each in-scope system has an `owner` in `config.yaml` (a
   GitHub `@user` or `@org/team`); the issue @mentions and best-effort assigns
   the owner of the affected system. (Assignees must be repo collaborators; an
   @mention still notifies a team.) GitHub demonstrates routing, but it does not
   enforce checklist completion, independent closure approval, or segregation
   of duties.
3. **Chat alert** — an optional Slack message, sent only if you configure a
   `SLACK_WEBHOOK_URL` repository secret (Settings → Secrets and variables →
   Actions). Without the secret this step is skipped, not failed.
4. **GitHub notification** — the monitoring run intentionally exits red on
   actionable findings. It may trigger an email or web notification depending
   on the recipient's GitHub Actions notification settings.

The repository is public and contains only fictional data. Do not send real
employee, termination, account, or activity data to these Issues, artifacts, or
chat notifications. A company implementation should use approved private
infrastructure, minimize sensitive fields, restrict access, and route cases to
its governed case-management platform.

GitHub Actions artifacts and logs in a public repository are retained for no
more than 90 days. Annual SOX evidence therefore must be exported to a durable,
access-controlled store under the company's approved retention policy.

A separate **`escalation.yml`** workflow ages each open exception case daily.
Cases open past the remediation SLA (`config.yaml` →
`remediation.issue_sla_days`) get an `escalated` label and a comment tagging the
`escalation_owner` (typically the control owner above the system admins). This
demonstrates detection, assignment, aging, and escalation. Remediation evidence,
independent approval, and closure remain human-controlled activities that a
production case platform must enforce and retain.

## Human decision boundary

Automation identifies and routes an exception; it does not disable a production
account, accept risk, or close an exception case. A designated human owner must
approve any remediation, evaluate the required lookback, and approve closure
from retained evidence.

Locally or in another scheduler, the same behavior is driven by flags:

```bash
python -m src.main --out log.csv --summary-json summary.json \
  --issue-md issue.md --fail-on high   # exits non-zero on high+ findings
```

In production the same entry point would be pointed at live system extracts and
driven by cron, Airflow, or an orchestration platform, with each run's log
retained as dated evidence. This maps to the continuous-monitoring control family
in NIST SP 800-53 (CA-7) and the ongoing-monitoring intent of COBIT 2019 DSS05.

## How to interpret workflow results

The monitoring workflow runs against sample data containing seeded exceptions.
It deliberately exits non-zero when critical or high findings exist, but a red
run must still be triaged because execution and evidence failures can also cause
it.

| Result | Meaning | Required response |
|---|---|---|
| Green Access Review | The control completed and found no finding at or above the configured failure threshold. | Confirm the evidence package is complete before relying on the result. |
| Red Access Review with valid evidence | The control completed and detected actionable access exceptions. | Review the generated cases and retained evidence. |
| Red Access Review with invalid or missing evidence | The control could not produce a reliable conclusion because inputs, dependencies, or workflow processing failed. | Investigate the control failure; do not interpret it as an access-control conclusion. |

On this repository you will typically see two states side by side:

- **CI (ci.yml)** is green. This runs the test suite and tracks code health. It is the run the README badge reflects.
- **Access Review** (`access-review.yml`) is red for the seeded sample findings.
  Verify the run summary before treating any red run as an expected alert.

To see a clean (green) Access Review run, point it at data with no outstanding exceptions.

## Onboarding another compatible extract

For a compatible flat-file extract, add a block under `systems:` in
`config.yaml` mapping its columns and active/disabled vocabulary onto the model;
the correlation and detection layers then use it without a rule-code change.
APIs, pagination, authentication, timestamp conversion, non-human identities,
shared accounts, or materially different schemas require a tested adapter.

## Repo layout

```
.github/workflows/
  ci.yml               Tests + smoke run (badge tracks this)
  access-review.yml    Scheduled monitoring: artifact, issue, Slack, alert
  escalation.yml       Ages open exception issues past the remediation SLA
.github/CODEOWNERS      Review ownership; enforcement requires branch protection
config.yaml            SLA + per-system schema mappings (audit-reproducible)
data/                  Fictional HR roster + 3 system account extracts
src/
  models.py            Normalized data structures
  integrity.py         Input evidence completeness and accuracy checks that stop the review when evidence cannot be verified
  loaders.py           Read + normalize each extract
  correlation.py       Identity correlation across systems
  detection.py         Control rules TA-01–TA-04
  reporting.py         Console summary, CSV/JSON ready for review + case summaries
  main.py              CLI orchestrator (--out / --summary-json / --fail-on)
tests/                 Unit tests: correlation, rules, integrity, outputs, exit codes
docs/
  poc_product_profile.md      Five-minute value, framework, risk, proof, and decision review
  control_narrative.md         Control write-up + framework mapping
  governance_and_controls.md   IPE C&A, change management, ITAC considerations
```

## Control mapping

PCAOB AS 2201 · COSO Principle 11 · COBIT 2019 DSS05/DSS06 ·
NIST SP 800-53 AC-2 & CA-7 · ISO/IEC 27001 A.5.18. Full narrative in
[`docs/control_narrative.md`](docs/control_narrative.md).

These are audit and control-design cross references, not a conclusion that the
POC satisfies SOX or any other framework. Company management and its assurance
professionals must validate financial-reporting scope, significant risks,
applicability, control ownership, and reliance.

For a concise review of product value, illustrative framework fit, material
risks, success metrics, and decisions, see the
[`docs/poc_product_profile.md`](docs/poc_product_profile.md).

For data-integrity (IPE completeness and accuracy), change management, and ITAC
considerations, see
[`docs/governance_and_controls.md`](docs/governance_and_controls.md).

## Scope note

This is a focused proof of concept, not a production platform. It demonstrates
the approach — cross-application identity correlation for a single ITGC — on
fictional data. Production concerns (API ingestion, governed identity mapping,
per-system SLAs, data protection, evidence retention, governed case closure, and
change control over the tool itself) are covered in
[`docs/production_considerations.md`](docs/production_considerations.md).

## Shared terminology

Plain language definitions for shared assurance terms are available in the
[portfolio glossary](https://github.com/MaxwellM-GRC/grc-control-core/blob/v0.3.0/docs/glossary.md).

## License

MIT — see [LICENSE](LICENSE).

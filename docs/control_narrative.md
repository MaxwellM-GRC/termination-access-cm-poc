# Control Narrative — Timely De-Provisioning of Terminated User Access

## Control objective

Logical access for terminated workforce members is removed from in-scope
financial applications within the defined service-level window, so that no
former employee or contractor retains the ability to transact in or access
systems relevant to financial reporting after their separation date.

## Risk addressed

A terminated individual who retains active access can initiate or alter
transactions, view confidential data, or provide an avenue for account
compromise. Because access is granted per application, the residual risk often
hides in a single downstream system even when the identity provider was
disabled correctly. This is the failure mode the POC is built to surface.

## Control activity as tested

On a defined cadence, the reviewer:

1. Obtains the termination roster from the HR system of record (the population).
2. Obtains account extracts from each in-scope application.
3. Correlates each terminated identity to its account(s) in every system.
4. Evaluates each account against four assertions (see rules below).
5. Documents every exception in a retained exception log.

## Test assertions (rule IDs match the code)

| Rule | Assertion | Exception raised when | Severity |
|------|-----------|-----------------------|----------|
| R1 | Access is removed | Account is still active post-termination | Critical |
| R2 | Removal is timely | Account disabled after the SLA deadline | High |
| R3 | No post-term use | Login/activity occurs after termination date | Critical |
| R4 | Identity is reliable | Account tied to the person by name only | Info |

## Framework mapping

| Framework | Reference | Relevance |
|-----------|-----------|-----------|
| PCAOB | AS 2201 | ITGC over access supporting reliance on automated controls and system-generated data |
| COSO | Principle 11 | Selects and develops general controls over technology |
| COBIT 2019 | DSS05, DSS06 | Managed security services; managed business process controls |
| NIST SP 800-53 | AC-2 (Account Management) | Disable accounts on termination; review activity |
| NIST SP 800-53 | CA-7 (Continuous Monitoring) | Ongoing, automated assessment of the access-removal control on a defined cadence |
| ISO/IEC 27001 | A.5.18 | Access rights removal/adjustment on termination or change |

## Evidence produced

- **Exception log** (`exception_log_*.csv`): one row per finding — the primary
  evidence artifact. Ties each exception to an employee, system, rule, and date.
- **Run summary** (console/captured): population counts and reconciliation
  (terminated reviewed, accounts ingested, identities correlated, unmatched).
- **Configuration** (`config.yaml`): documents the SLA and the exact field/status
  mapping used for the run, so the test is reproducible.
- **Exception queue** (continuous-monitoring mode): each scheduled run with
  actionable findings uploads its log/summary as a retained artifact and records
  the exceptions on a rolling GitHub Issue, routed to the owning system's admin.
  Issues left open past the remediation SLA are aged and escalated to the control
  owner, giving a timestamped trail from detection through assignment,
  escalation, and closure.

## Population completeness

The HR termination roster is the authoritative population. The run summary
reports how many terminated identities correlated to at least one account and
lists any that matched none, so completeness of the review can be reconciled and
manual follow-up scoped.

## Limitations of this POC

- Data is fictional and static; a production build would pull extracts via API
  with its own change/version controls.
- Correlation uses email then normalized name. Real environments need a
  governed identity mapping (e.g., a canonical ID) for name collisions and
  shared/service accounts.
- SLA is a single global value here; production policy often varies by system
  criticality and termination type.

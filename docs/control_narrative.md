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
| TA-01 | Access is removed | Account is still active post-termination | Critical |
| TA-02 | Removal is timely | Account disabled after the SLA deadline | High |
| TA-03 | No post-term use | Login/activity occurs after termination date | Critical |
| TA-04 | Identity is reliable | Account tied to the person by name only | Info |

## Framework mapping

The mapping IDs below are governed by the concise
[`poc_product_profile.md`](poc_product_profile.md). They are illustrative design
cross references, not a compliance conclusion.

| Mapping ID | Framework | Reference | Relevance |
|-----------|-----------|-----------|-----------|
| `MAP-TA-01` | PCAOB and COSO | AS 2201; Principle 11 | ITGC design over access supporting financial-reporting systems |
| `MAP-TA-02` | COBIT 2019 | DSS05, DSS06 | Managed access and business-process control monitoring |
| `MAP-TA-03` | NIST SP 800-53 Rev. 5 | AC-2 (Account Management) | Disable accounts on termination and review activity |
| `MAP-TA-04` | NIST SP 800-53 Rev. 5 | CA-7 (Continuous Monitoring) | Ongoing assessment on a defined cadence |
| `MAP-TA-05` | ISO/IEC 27001:2022 | A.5.18 | Review and removal or adjustment of access rights |

## Evidence produced

This evidence supports mappings `MAP-TA-01` through `MAP-TA-05` only to the
extent described in the product profile.

- **Exception log** (`exception_log_*.csv`): one row per finding — the primary
  evidence artifact. Ties each exception to an employee, system, rule, and date.
- **Run summary** (console/captured): population counts and reconciliation
  (terminated reviewed, accounts ingested, identities correlated, unmatched).
- **Configuration** (`config.yaml`): documents the SLA and the exact field/status
  mapping used for the run, so the test is reproducible.
- **Exception cases** (continuous-monitoring mode): each actionable finding has
  a stable finding ID and a dedicated GitHub Issue. The case includes the owner,
  prescribed response, aging, and closure evidence checklist, so it can be
  reopened on recurrence and audited from detection through closure.

## Default exception response

The control detects exceptions automatically but does not disable production
accounts. Each finding is issued with an RCM ready, human led response: required
remediation, mitigation/lookback procedure, root cause prompt, closure evidence,
and escalation condition. For example, an active account is disabled promptly
and its post-termination activity is reviewed; post-termination activity also
requires a transactional-risk assessment where the role could affect financial
reporting. The current response policy is versioned in `config.yaml` under
`rule_responses`.

## Population completeness

The HR termination roster is the authoritative population. The run summary
reports how many terminated identities correlated to at least one account and
lists any that matched none, so completeness of the review can be reconciled and
manual follow up scoped.

## Limitations of this POC

- Data is fictional and static; a production build would pull extracts via API
  with its own change/version controls.
- Correlation uses email then normalized name. Real environments need a
  governed identity mapping (e.g., a canonical ID) for name collisions and
  shared/service accounts.
- SLA is a single global value here; production policy often varies by system
  criticality and termination type.

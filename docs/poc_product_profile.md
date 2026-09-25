# Termination Access Review — Product Profile

This is a five-minute product-governance review. Detailed control design and
evidence considerations remain in the linked technical documents.

## 1. Decision snapshot

| Field | Entry |
|---|---|
| Product owner | POC repository owner |
| Adopting function | GRC, Internal Audit, Identity Governance, or IT Security |
| Decision requested | Pilot with company-specific data and policy |
| Evidence status | Verified for fictional fixtures; assumed for company use |
| Decision status | Proposed |
| Next validation | Reperform against one company's authoritative termination roster and complete account populations |

## 2. Value and scope

- **Company problem:** Residual access can remain in a downstream application
  even when central identity access was disabled on time.
- **Primary users:** Control owners, access governance teams, internal auditors,
  and application owners.
- **Product promise:** Reconcile terminated people to all configured account
  populations and route explainable exceptions with retained evidence.
- **POC demonstrates:** Cross-system normalization, identity correlation,
  evidence validation, four deterministic tests, exception reporting, and a
  human-owned response workflow using fictional cloud and SaaS-style data.
- **Explicit exclusions:** Production connectors, automated account changes,
  company-specific scoping, policy approval, compliance certification, and a
  conclusion about control operating effectiveness.

## 3. Control and framework fit

These mappings are illustrative design cross references, not a compliance
conclusion. A company's management and assurance professionals must validate
scope, applicability, control ownership, and reliance.

| Mapping ID | Framework reference | Control/rule IDs | POC evidence | Fit and remaining validation |
|---|---|---|---|---|
| `MAP-TA-01` | PCAOB AS 2201 and COSO Principle 11 | `ITGC-AD-001`; `TA-01`, `TA-02`, `TA-03`, `TA-04` | Configuration, source validation, run summary, exception log | Supports technology-control design over financial-reporting systems; company SOX scope and auditor reliance remain unverified. |
| `MAP-TA-02` | COBIT 2019 DSS05 and DSS06 | `TA-01`, `TA-02`, `TA-03`, `TA-04` | Account-state evaluation and routed exception cases | Supports managed access and business-process control monitoring; practice-level applicability requires company validation. |
| `MAP-TA-03` | NIST SP 800-53 Rev. 5 AC-2 | `TA-01`, `TA-02`, `TA-03` | Termination date, account state, removal date, and activity evidence | Supports account disabling and review; organization-defined timing and system scope must be approved. |
| `MAP-TA-04` | NIST SP 800-53 Rev. 5 CA-7 | `ITGC-AD-001`; `TA-01`, `TA-02`, `TA-03`, `TA-04` | Scheduled review, retained results, and exception routing | Supports ongoing monitoring; production cadence, recipients, and response workflow remain unverified. |
| `MAP-TA-05` | ISO/IEC 27001:2022 A.5.18 | `TA-01`, `TA-02`, `TA-03` | Access status, removal timing, and post-termination activity evidence | Supports review and removal of access rights; organizational applicability requires validation. |

## 4. Operating model and safeguards

- **Automation does:** Validate extracts, normalize records, correlate identities,
  evaluate configured rules, retain results, and route exceptions.
- **People decide:** System scope, policy timeframes, identity ambiguity,
  remediation, activity lookback, risk acceptance, and case closure.
- **Key roles and handoffs:** The product owner maintains the POC; a company
  control owner approves the control design; system owners remediate; an
  independent reviewer approves risk decisions and closure.

| Material requirement, risk, or assumption | Status | Safeguard or validation | Owner |
|---|---|---|---|
| HR and account extracts are complete and authoritative. | Assumed for company use | Reconcile API or report populations to source-system totals before reliance. | Control owner and system owners |
| Email and normalized-name matching identifies the correct person. | Assumed | Use a governed workforce identifier and route ambiguous matches for review. | Identity governance |
| Seven-day default and immediate involuntary-termination timing reflect policy. | Assumed | Configure approved company, system, role, and termination-type requirements. | Control owner |
| Monitoring credentials and retained evidence are protected. | Assumed | Use least-privilege service identities, encryption, access logs, and retention controls. | Security and platform owners |
| Rule results are useful without creating unacceptable false positives or gaps. | Verified only for fixtures | Run a historical sample and compare results with known cases and manual review. | Control owner and reviewer |
| Framework mappings are appropriate for the adopting company. | Assumed | Validate against the approved RCM, framework versions, scope, and assurance approach. | GRC and Internal Audit |

## 5. Proof plan

- **Success metrics:** All retained source populations pass integrity checks;
  all terminated identities are accounted for as correlated or unmatched; all
  seeded exception scenarios produce the expected rule and severity; and no
  production remediation, risk acceptance, or closure occurs automatically.
- **Pilot validation:** Use a bounded historical period, reconcile source totals,
  compare findings with known termination cases, and have control and system
  owners assess false positives, missing cases, and response usefulness.
- **Integration assumptions:** Authoritative HR data, complete account APIs or
  exports, governed identity keys, a scheduler, evidence storage, and a case or
  ticketing workflow are available.
- **Expected upkeep:** Maintain system mappings, scope, policy timeframes,
  identities, owners, credentials, and tests when source systems change.
- **Release blockers:** Do not rely on the POC in production until company scope,
  policy, source completeness, identity matching, security, retention, and human
  approval workflows are validated.

## 6. Material decisions

| Decision | Evidence status | Decision status | Rationale | Next test/action |
|---|---|---|---|---|
| Keep the POC focused on detection and evidence rather than automated deprovisioning. | Verified in code and workflow | Approved | Preserves human authority and makes the example safer and easier to review. | Confirm the boundary during a company pilot. |
| Use HR terminations as the authoritative population and evaluate every configured account source. | Verified for fixtures | Approved | Demonstrates cross-application completeness instead of an identity-provider-only review. | Reconcile live source totals. |
| Keep four explainable rule IDs with configured response guidance. | Verified in tests and configuration | Approved | Makes findings traceable without building a broad policy engine. | Compare rule coverage with the company's RCM. |
| Treat framework mappings as illustrative until company validation. | Assumed for company use | Approved | Avoids presenting a portfolio example as compliance or legal advice. | Obtain control-owner and assurance review. |
| Pilot the approach with actual company data. | Assumed | Proposed | Value, data quality, precision, effort, and operating fit cannot be established from fictional fixtures. | Run a bounded historical pilot. |

Detailed references: [control narrative](control_narrative.md),
[governance and controls](governance_and_controls.md), and
[remediation design](remediation_design.md).

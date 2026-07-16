# Remediation Design (v2 Direction)

This repository, today, detects and routes exceptions. It does not act on them.
This note describes how an actioning layer would work: how a confirmed late
termination could be remediated at the application level, and the guardrails that
make taking action on production access safe. It is a design, not an
implementation. Detection is safe to run on fictional data; remediation calls
real systems and should not run against anything live in a portfolio repo.

## Where remediation acts

An identity provider with lifecycle management (for example Okta) deprovisions a
downstream account by sending a SCIM `active = false`, which deactivates the
account rather than deleting it. That covers accounts the IdP manages. It does
not cover three cases, which are exactly where standing access hides and where
this control adds value: accounts in apps that are not SCIM integrated, accounts
created locally outside the IdP, and cases where the SCIM call was logged as sent
but the downstream account is still active. This control verifies the actual
account state through each app's own interface, independent of the IdP's logs.

Remediation therefore has two paths, chosen per finding:

| Case | Who controls the account | Remediation action |
|------|--------------------------|--------------------|
| IdP-managed account | The identity provider | Call the IdP API to deactivate the user or remove the app assignment, or trigger an IdP workflow; the IdP then pushes `active = false` to the app |
| Unmanaged / local account | The application only | Call the application's own API directly to disable the account, since the IdP has no handle on it |

In the repository this would be a tested module (for example `src/remediation.py`)
that selects the path per finding, plus a workflow that invokes it. The logic
belongs in code, not in a workflow file, because acting on access requires
handling API failures, scope checks, and logging that must be tested.

## Guardrails

A control that changes production access must be harder to fire than one that
only reads. The guardrails apply the same posture this project already uses for
inputs (fail-closed) and for its own logic (change management), now applied to
actions.

- **Dry-run by default.** The module logs exactly what it would do (deactivate
  account X in system Y via this call) without sending it. Actioning happens only
  when an explicit flag is set, so the safe state is the default and the intended
  changes can be reviewed as a diff first.
- **Human approval between detection and action.** Detection stays automated;
  deactivation requires a person to approve. In practice the review opens the
  exception as it does now, and the remediation step acts only on exceptions a
  human has marked approved (for example an `approved-for-remediation` label, or
  an approval gate on a protected deployment environment). This preserves
  segregation between finding the problem and deciding to change access.
- **Scope limits and a circuit breaker.** Remediation acts only on accounts
  matched to a confirmed HR termination, never touches systems outside an
  allow-list, and refuses to act if a single run would exceed a maximum count.
  If the limit is exceeded, it stops and escalates rather than mass-deactivating.
- **Least privilege.** The credential can deactivate but not delete, and is
  scoped only to the in-scope apps, so even a logic error has a bounded,
  reversible worst case.
- **Audit trail and reversibility.** Every action writes an immutable record:
  trigger, account, call made, timestamp, and before and after state. Because
  deactivation sets `active = false` rather than deleting, a mistaken action can
  be reversed, and the log shows exactly what to undo.

## Sequencing

Detection and routing (built) come first. The design document (this note) is the
next step, because it demonstrates safe actioning design without standing up live
credentials. An executable module would follow only in an environment with real,
least-privilege access and the guardrails above in place, starting in dry-run and
against a single low-risk system before any live actioning.

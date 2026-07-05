# UTM SecureNotes

## What This Is

UTM SecureNotes is a secure web application for Universiti Teknologi Malaysia graduate students to create, store, and share encrypted personal notes. It is the deliverable for the SECR4483 Secure Programming group project: access is restricted to verified `@graduate.utm.my` accounts, notes are encrypted at rest with per-note AES-256-GCM keys, and sharing uses RSA-2048 key wrapping. The app runs locally only (Flask dev server + self-signed TLS + local MySQL 8) — there is no production deployment target.

## Core Value

All three assignment parts pass and all 7 required security controls are demonstrably present and testable: Part 1 (auth module vulnerability analysis), Part 2 (transaction module vulnerability analysis), Part 3 (integrated secure app, ≥7 controls, Burp Suite/OWASP ZAP testing), plus a video demo of the golden path (register → OTP → login → create note → view encrypted DB → share note → admin panel → security walkthrough).

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

- [ ] Project scaffold: Flask app factory, blueprints, security headers, error handlers, dev TLS
- [ ] Database models: users, otp_tokens, notes, note_keys, note_access, audit_logs — with locked dedicated-nonce-column schema for notes/note_keys
- [ ] Crypto layer: AES-256-GCM (dedicated nonce columns for notes/note_keys), PBKDF2-SHA256 (600k) vault key derivation, RSA-2048 key wrapping
- [ ] Auth decorators: login_required, admin_required (RBAC enforcement)
- [ ] Auth blueprint: UTM-email-restricted registration, password policy, email OTP MFA, login with lockout, logout, session regeneration
- [ ] Notes blueprint: encrypted CRUD (create/view/edit/delete) with per-note AES keys, ownership checks
- [ ] Note sharing: RSA-OAEP key wrapping for cross-user access grants, permission levels (read/write)
- [ ] Admin blueprint: user management (suspend/activate), paginated audit log viewer, RBAC-gated, cryptographically barred from note content
- [ ] Base template + UI: navbar, flash messages, Bootstrap 5 styling, CSRF tokens on all forms, security headers verified
- [ ] Final integration: root redirect, full test suite green, manual golden-path walkthrough verified

### Out of Scope

- Production deployment (cloud hosting, real CA-signed TLS, managed MySQL) — explicitly local-dev-only per assignment scope
- Mobile app / responsive-native UI — Bootstrap 5 web UI is sufficient for the rubric
- Real-time collaborative editing of shared notes — sharing is read/write access grant, not live co-editing
- Automated re-encryption/re-wrapping of RSA-shared note keys on owner edit — documented academic-project limitation; recipients' shared keys go stale after an edit (would need key escrow or recipient signal in production)
- OAuth/SSO login — UTM email + password + OTP is the assignment-mandated auth model

## Context

This is a solo-developer-plus-Claude SECR4483 group project build. An approved design SPEC (`docs/superpowers/specs/2026-06-17-utm-securenotes-design.md`) and a detailed 10-task TDD implementation plan (`docs/superpowers/plans/2026-06-17-utm-securenotes.md`) already exist and were ingested as the basis for this roadmap. The implementation plan's own code diverges from the SPEC on one point (nonce storage for `notes`/`note_keys` — see Key Decisions); the SPEC's dedicated-column design is locked and wins by precedence (ADR > SPEC > PRD > DOC). The plan otherwise provides task-by-task pseudocode, test stubs, and file layout that the roadmap phases below are directly derived from.

Each roadmap phase corresponds 1:1 to one of the implementation plan's 10 tasks, preserving the plan's TDD ordering (failing tests first, then implementation, then passing tests, then commit).

## Constraints

- **Tech stack**: Python 3.12 + Flask 3, MySQL 8 via SQLAlchemy ORM, Bootstrap 5 + vanilla JS, `cryptography` lib (AES-256-GCM, PBKDF2, RSA-2048), Flask-WTF (CSRF), Flask-Mail (OTP via SMTP), `bleach` (sanitization), `bcrypt` cost 12 (passwords) — locked by Approved SPEC section 2.
- **Runtime**: Local dev only — `run.py` with `ssl_context='adhoc'` self-signed TLS, local MySQL 8 instance. No production deployment.
- **Schema (locked, SPEC > DOC)**: `notes.nonce` and `note_keys.key_nonce` MUST be dedicated `BINARY(12)` columns, separate from the ciphertext/wrapped-key blobs — NOT prepended-nonce-in-blob. This overrides the implementation plan's own `crypto.py`/`models.py` code, which used a prepended-nonce approach. The one exception remains `users.rsa_private_key_encrypted`, which has no dedicated nonce column (nonce prepended to that blob) per SPEC section 5.
- **Email restriction**: Only `@graduate.utm.my` addresses may register, enforced via regex `^[a-zA-Z0-9._%+\-]+@graduate\.utm\.my$` server-side.
- **Password policy**: >=12 chars, upper+lower+digit+symbol, bcrypt cost 12.
- **Vault key derivation**: PBKDF2HMAC-SHA256, 600,000 iterations, never persisted — derived fresh on every login from password + `vault_salt`.
- **Session management**: 30-min inactivity timeout, session ID regenerated on login (fixation prevention), vault_key cleared on logout, CSRF token required on every state-changing form.
- **RBAC**: Two roles only — `student` (own-note CRUD + share) and `admin` (user mgmt + audit log view, NO note_keys rows ever created for admin accounts — cryptographic enforcement, not just authorization).
- **Rate limiting**: 5 failed login attempts -> 15-minute lockout, tracked via audit_logs `login_failed` entries.
- **Security controls rubric (7 required, all locked by Approved SPEC section 10)**: (1) input validation/output sanitization (bleach + Jinja2 autoescape), (2) MFA (email OTP), (3) RBAC, (4) secure session mgmt, (5) encrypted storage (AES-256-GCM + RSA-2048), (6) secure transmission (self-signed TLS), (7) error handling (generic messages, no stack traces, no user enumeration).
- **Assignment coverage**: Roadmap phases must collectively satisfy SECR4483 Part 1 (auth module analysis), Part 2 (transaction module analysis), Part 3 (integrated app + Burp/ZAP testing + report), and the video demo golden path — locked by Approved SPEC section 11.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SPEC's dedicated nonce-column schema (`notes.nonce`, `note_keys.key_nonce` as separate `BINARY(12)` columns) wins over the implementation plan's prepended-nonce-in-blob code | SPEC has Approved status and outranks DOC in precedence (ADR > SPEC > PRD > DOC); the plan's own prose claimed spec-compliance but its actual `models.py`/`crypto.py` code contradicted that claim — auto-resolved per INGEST-CONFLICTS.md | — Pending (must be reflected when implementing Database Models and Crypto Layer phases; plan's example code for those two tasks needs adaptation, not verbatim use) |
| Use the existing 10-task implementation plan as the direct basis for the 10 roadmap phases | A detailed, already-reviewed TDD plan exists; rederiving phase structure from scratch would discard useful sequencing and test scaffolding | ✓ Good |
| OTP bcrypt cost factor (rounds=8) may differ from password bcrypt cost factor (rounds=12) | Plan's `_send_otp` uses a lower cost factor for the low-entropy, short-lived 6-digit OTP; SPEC does not mandate an OTP-specific cost factor, so this is not a contradiction — carried forward as an implementation detail to confirm during Auth Blueprint phase | — Pending |
| Local-dev-only runtime (no production deployment) | Assignment scope is an academic security demonstration, not a production service | ✓ Good |

---
*Last updated: 2026-06-18 after initial roadmap creation*

# Context (from supporting DOCs)

source: docs/superpowers/plans/2026-06-17-utm-securenotes.md (classified DOC — implementation/execution plan, cross-references the SPEC)

## Topic: Implementation Plan Overview
Task-by-task TDD implementation plan (10 tasks) for the UTM SecureNotes app defined in the design SPEC. Stack: Python 3.12, Flask 3, SQLAlchemy 3, Flask-WTF, Flask-Mail, Flask-Bcrypt, `cryptography`, MySQL 8, Bootstrap 5, pytest, pytest-flask. Uses subagent-driven-development / executing-plans workflow with checkbox-tracked steps.
source: docs/superpowers/plans/2026-06-17-utm-securenotes.md, header section

## Topic: Nonce-handling design note (as asserted by the plan author)
The plan's own architecture note claims: "Per the spec schema, `notes.nonce` and `note_keys.key_nonce` are dedicated columns (nonces are NOT prepended to ciphertext for these two tables). The one exception is `users.rsa_private_key_encrypted`, which has no dedicated nonce column in the spec — its nonce is prepended to that blob."
This claim is contradicted by the plan's own subsequent code (see CONFLICT-001 in INGEST-CONFLICTS.md): the actual `Note` and `NoteKey` SQLAlchemy models defined later in the same document omit `nonce`/`key_nonce` columns entirely, and the `crypto.py` helpers (`aes_encrypt`/`aes_decrypt`) always prepend the nonce to the ciphertext blob for every call site, including notes and note_keys.
source: docs/superpowers/plans/2026-06-17-utm-securenotes.md, plan preamble + Task 2 Step 2 + Task 3 Step 2

## Topic: File map / project layout
Proposed layout: `app/__init__.py` (factory, blueprints, security headers, error handlers), `app/extensions.py` (db, bcrypt, mail, csrf singletons), `app/models.py`, `app/crypto.py`, `app/decorators.py` (login_required, admin_required), `app/auth/`, `app/notes/`, `app/admin/` blueprint packages each with forms.py/routes.py, `app/templates/` tree, `tests/` (conftest.py, test_crypto.py, test_auth.py, test_notes.py, test_admin.py, test_access_control.py), config.py, requirements.txt, .env.example, run.py.
source: docs/superpowers/plans/2026-06-17-utm-securenotes.md, File Map section

## Topic: Pinned dependency versions
Flask==3.0.3, Flask-SQLAlchemy==3.1.1, Flask-WTF==1.2.1, Flask-Mail==0.10.0, Flask-Bcrypt==1.0.1, cryptography==42.0.8, bleach==6.1.0, PyMySQL==1.1.1, python-dotenv==1.0.1, email-validator==2.1.1, pytest==8.2.2, pytest-flask==1.3.0.
source: docs/superpowers/plans/2026-06-17-utm-securenotes.md, Task 1 Step 1

## Topic: Config decisions not present in SPEC
TestConfig uses sqlite in-memory DB for tests (SPEC only specifies MySQL 8 for the real app — sqlite-for-tests is an implementation detail, not a contradiction). PERMANENT_SESSION_LIFETIME=1800 matches SPEC's 30-min inactivity timeout. SESSION_COOKIE_HTTPONLY=True and SESSION_COOKIE_SAMESITE='Lax' are implementation additions not explicitly mandated by the SPEC text (not contradictory, just additive hardening).
source: docs/superpowers/plans/2026-06-17-utm-securenotes.md, Task 1 Step 5

## Topic: Known/documented limitation — note edit re-encryption for RSA-shared recipients
The plan explicitly documents a gap: when an owner edits a note, the note is re-encrypted with a brand-new note_key, but only the owner's own `note_keys` row is re-wrapped. RSA-shared recipients' existing wrapped keys become stale and will fail to decrypt the new ciphertext after an edit. The plan author flags this for the security report as an accepted academic-project limitation ("in production this would use a key escrow or signal to recipients") rather than something to silently fix.
source: docs/superpowers/plans/2026-06-17-utm-securenotes.md, Task 6 Step 3 (note after routes.py listing)

## Topic: OTP bcrypt cost factor differs from password bcrypt cost factor
SPEC says password hashing uses bcrypt cost 12 (section 2, section 6). The plan's `_send_otp` implementation hashes the 6-digit OTP with `bcrypt.generate_password_hash(otp, rounds=8)` — a different (lower) cost factor than the cost-12 used for user passwords. The SPEC does not specify an OTP-hash cost factor explicitly, so this is not a direct contradiction, but it's a detail worth carrying forward since OTPs are short numeric codes already low-entropy; rounds=8 vs rounds=12 may be a deliberate performance/security tradeoff worth confirming with the user.
source: docs/superpowers/plans/2026-06-17-utm-securenotes.md, Task 5 Step 3 (`_send_otp`)

## Topic: Self-review checklist (plan author's own coverage claim)
The plan ends with a checklist self-asserting full SPEC coverage (UTM email enforcement, OTP flow, AES-256-GCM, PBKDF2 600k, RSA-2048 sharing, bcrypt cost 12, rate limiting, CSRF, sanitization, RBAC, admin functions, audit logging, security headers, error handlers, ownership checks, admin cannot read notes). This is the plan author's self-assessment, not independently verified by this synthesis pass — useful as a checklist for downstream QA/roadmap planning.
source: docs/superpowers/plans/2026-06-17-utm-securenotes.md, Self-Review Checklist section

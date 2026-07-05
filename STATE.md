# Roadmap: UTM SecureNotes

## Overview

UTM SecureNotes is built in ten phases that mirror the existing 10-task TDD implementation plan, in the same order: scaffold the Flask app and test harness, define the encrypted-data schema, build the crypto primitives that schema depends on, add RBAC decorators, then layer on the auth flow (registration/OTP/login), encrypted notes CRUD, RSA-based sharing, the admin console, the shared UI shell, and finally an integration pass that wires the root route and verifies the full golden path plus the security-control rubric end to end. Each phase produces a working, test-verified slice; by Phase 10 all three SECR4483 assignment parts and all 7 required security controls are demonstrable.

**Locked constraint carried through Phases 2 and 3:** the SPEC's dedicated-nonce-column schema (`notes.nonce`, `note_keys.key_nonce` as separate `BINARY(12)` columns) is the source of truth, not the implementation plan's own prepended-nonce-in-blob code. Any plan pseudocode for models/crypto must be adapted to add and use these dedicated columns rather than copied verbatim.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Project Setup** - Flask app factory, blueprints, security headers, error handlers, and test harness exist and boot.
- [ ] **Phase 2: Database Models** - All six tables exist via SQLAlchemy models, with locked dedicated nonce columns on notes/note_keys.
- [ ] **Phase 3: Crypto Layer** - AES-256-GCM, PBKDF2 vault-key derivation, and RSA-2048 key wrapping all round-trip correctly using the dedicated-nonce-column scheme.
- [ ] **Phase 4: Auth Decorators** - login_required and admin_required enforce authentication/RBAC on stub routes.
- [ ] **Phase 5: Auth Blueprint** - Students can register with a UTM email, verify via emailed OTP, log in/out securely, and trigger lockout on repeated failures.
- [ ] **Phase 6: Notes CRUD** - Authenticated students can create, view, edit, and delete their own encrypted notes; others are blocked.
- [ ] **Phase 7: Note Sharing** - Note owners can share notes with other UTM students via RSA-wrapped keys and permission grants.
- [ ] **Phase 8: Admin Blueprint** - Admins can manage user status and view audit logs, without ever gaining access to note content.
- [ ] **Phase 9: Base Template & UI Hardening** - Consistent UI shell, CSRF-protected forms, and verified security headers across the app.
- [ ] **Phase 10: Final Integration** - Root redirect wired, full test suite green, golden path and security-control rubric manually verified end to end.

## Phase Details

### Phase 1: Project Setup
**Goal**: A bootable Flask application skeleton exists with all extensions wired, blueprints registered, security headers and error handlers in place, and a test harness that can run a smoke test.
**Depends on**: Nothing (first phase)
**Requirements**: SETUP-01, SETUP-02, SETUP-03, SETUP-04, SETUP-05, SETUP-06, SETUP-07
**Success Criteria** (what must be TRUE):
  1. Running `pytest tests/test_smoke.py` exercises a real (if minimal) route through the full app factory.
  2. Every HTTP response includes X-Content-Type-Options, X-Frame-Options, and Content-Security-Policy headers.
  3. Visiting a non-existent route or triggering a server error renders a generic error page, not a stack trace.
  4. `python run.py` starts the app locally over self-signed HTTPS.
**Plans**: TBD

### Phase 2: Database Models
**Goal**: The complete encrypted-notes data model exists and persists correctly, with the locked dedicated-nonce-column schema for notes and note_keys.
**Depends on**: Phase 1
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06
**Success Criteria** (what must be TRUE):
  1. A User, Note, NoteKey, NoteAccess, OTPToken, and AuditLog row can each be created and persisted via SQLAlchemy with all required fields.
  2. `notes` has a dedicated `nonce` column (BINARY(12)) separate from its ciphertext columns — verified by schema inspection, not by reading ciphertext length.
  3. `note_keys` has a dedicated `key_nonce` column (BINARY(12)) separate from `encrypted_note_key` for vault-type rows.
  4. Deleting a Note cascades to delete its associated NoteKey and NoteAccess rows.
**Plans**: TBD

### Phase 3: Crypto Layer
**Goal**: All cryptographic primitives the app depends on (AES-256-GCM, PBKDF2 vault-key derivation, RSA-2048 wrapping) are implemented, tested, and consistent with the dedicated-nonce-column schema from Phase 2.
**Depends on**: Phase 2
**Requirements**: CRYPTO-01, CRYPTO-02, CRYPTO-03, CRYPTO-04, CRYPTO-05, CRYPTO-06
**Success Criteria** (what must be TRUE):
  1. Encrypting then decrypting the same plaintext with the same key (and its dedicated nonce passed separately) returns the original plaintext for both notes and note_keys use cases.
  2. Two encryptions of identical plaintext produce different nonces/ciphertexts.
  3. Tampering with ciphertext or its auth tag causes decryption to raise, not silently return wrong data.
  4. The same password + salt always derives the same 32-byte vault key; different passwords derive different keys.
  5. A note key wrapped with a vault key, and a note key wrapped with an RSA public key, both unwrap to the original key with the corresponding private/vault key.
  6. The RSA private key blob (`users.rsa_private_key_encrypted`) still uses prepended-nonce format, confirming the dedicated-column change applies only to notes/note_keys as locked.
**Plans**: TBD

### Phase 4: Auth Decorators
**Goal**: Route-level authentication and role-based access control are enforced consistently before any real blueprint logic is built on top of them.
**Depends on**: Phase 3
**Requirements**: ACCESS-01, ACCESS-02, ACCESS-03
**Success Criteria** (what must be TRUE):
  1. An unauthenticated request to a `login_required` route is redirected to `/auth/login`.
  2. An authenticated non-admin request to an `admin_required` route receives a 403, not a redirect.
  3. A session referencing a deleted, unverified, or deactivated user is treated as unauthenticated.
**Plans**: TBD

### Phase 5: Auth Blueprint
**Goal**: Students can self-register with a verified UTM identity, prove control of their email via OTP, and log in/out through a session that resists fixation and brute force.
**Depends on**: Phase 4
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09, AUTH-10
**Success Criteria** (what must be TRUE):
  1. Registering with a non-`@graduate.utm.my` email or a weak password is rejected with a specific, helpful error; registering with a valid UTM email and strong password creates an unverified user and emails a 6-digit OTP.
  2. Submitting the correct OTP within its 10-minute window marks the account verified; an incorrect or expired OTP shows a generic invalid/expired message and does not verify the account.
  3. Logging in with a verified, active account succeeds, regenerates the session ID, derives and stores the vault key in session, and is redirected to the notes list.
  4. Logging in with a wrong password, unverified account, or inactive account fails with a generic "invalid credentials" message (no enumeration of which condition failed).
  5. Five consecutive failed login attempts for the same account lock out further attempts for 15 minutes; logging out clears the session including the vault key.
**Plans**: TBD

### Phase 6: Notes CRUD
**Goal**: A logged-in student can manage their own encrypted notes end-to-end, with content unreadable to anyone else and unrecoverable in plaintext form anywhere but the live response.
**Depends on**: Phase 5
**Requirements**: NOTES-01, NOTES-02, NOTES-03, NOTES-04, NOTES-05, NOTES-06, NOTES-07
**Success Criteria** (what must be TRUE):
  1. Creating a note with a title and body stores only ciphertext in the database, plus a vault-wrapped per-note key in `note_keys` — the original plaintext is recoverable only via decryption with the owner's vault key.
  2. Viewing an owned note renders the correct decrypted title and body, with any HTML/script content escaped on output.
  3. Editing a note updates its displayed content to the new value and the owner can still decrypt it afterward.
  4. Deleting a note removes it and all its `note_keys` rows; it no longer appears in the owner's list.
  5. A second user with no access grant attempting to view, edit, or delete someone else's note receives a 403 with no note content in the response.
**Plans**: TBD

### Phase 7: Note Sharing
**Goal**: A note owner can grant another verified UTM student access to a specific note without ever exposing the note's symmetric key in a form only the recipient can't decrypt.
**Depends on**: Phase 6
**Requirements**: SHARE-01, SHARE-02, SHARE-03, SHARE-04, SHARE-05
**Success Criteria** (what must be TRUE):
  1. Sharing a note with a valid, verified UTM recipient succeeds and the recipient can subsequently view the note's correct decrypted content.
  2. The recipient's access is backed by an RSA-OAEP-wrapped copy of the note key plus a `note_access` row recording their permission level (read or write).
  3. Sharing with a non-UTM email, or an email with no verified account, is rejected with a clear error and no `note_keys`/`note_access` rows are created.
  4. Attempting to share the same note with the same recipient a second time is rejected rather than creating duplicate access.
**Plans**: TBD

### Phase 8: Admin Blueprint
**Goal**: An administrator can manage the student population and review the security audit trail, while remaining cryptographically incapable of reading any note's plaintext content.
**Depends on**: Phase 7
**Requirements**: ADMIN-01, ADMIN-02, ADMIN-03, ADMIN-04, ADMIN-05, ADMIN-06
**Success Criteria** (what must be TRUE):
  1. An admin can view a list of all users showing role, verification, and active status.
  2. An admin can suspend an active student (their `is_active` flips to false and they can no longer log in) and reactivate a suspended one, with both actions recorded in the audit log.
  3. An admin can browse a paginated view of all audit log entries.
  4. A non-admin (student) hitting any `/admin` route receives a 403.
  5. No `note_keys` row exists for any admin account at any point, even after notes are created/shared by students — confirmed by inspecting the table, not just by route behavior.
**Plans**: TBD

### Phase 9: Base Template & UI Hardening
**Goal**: Every page in the app shares a consistent, secure UI shell: protected against CSRF, instrumented with verifiable security headers, and usable via a real navigation flow.
**Depends on**: Phase 8
**Requirements**: UI-01, UI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. Every page renders within a shared base layout with working navigation (login/register when logged out; notes/admin/logout when logged in) and flash messages for user feedback.
  2. Every form that changes state includes a CSRF token, and a request missing or forging that token is rejected.
  3. An automated test confirms the required security headers are present on responses.
**Plans**: TBD
**UI hint**: yes

### Phase 10: Final Integration
**Goal**: The application is demonstrably complete: the full automated test suite passes, the root URL routes sensibly, and the manual golden path plus security-control rubric have been walked through end to end exactly as the assignment and video demo require.
**Depends on**: Phase 9
**Requirements**: INTEG-01, INTEG-02, INTEG-03, INTEG-04
**Success Criteria** (what must be TRUE):
  1. Visiting `/` with no session redirects to the login page.
  2. Running the full test suite (`pytest -v`) reports zero failures.
  3. A manual walkthrough succeeds for the entire golden path: register -> OTP verify -> login -> create note -> view decrypted note -> edit note -> share note with a second account -> recipient views the shared note -> admin views the user list -> admin suspends the student -> the suspended student cannot log in -> admin views audit logs showing every prior action.
  4. Manual or tool-based checks (Burp Suite/OWASP ZAP) confirm each of the 6 required vulnerability tests behaves as expected: SQL injection blocked, XSS blocked, session ID changes on login, forged CSRF rejected, brute-force lockout triggers, unauthorized note access returns 403 with no leaked data.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Setup | 0/TBD | Not started | - |
| 2. Database Models | 0/TBD | Not started | - |
| 3. Crypto Layer | 0/TBD | Not started | - |
| 4. Auth Decorators | 0/TBD | Not started | - |
| 5. Auth Blueprint | 0/TBD | Not started | - |
| 6. Notes CRUD | 0/TBD | Not started | - |
| 7. Note Sharing | 0/TBD | Not started | - |
| 8. Admin Blueprint | 0/TBD | Not started | - |
| 9. Base Template & UI Hardening | 0/TBD | Not started | - |
| 10. Final Integration | 0/TBD | Not started | - |

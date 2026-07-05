# Requirements: UTM SecureNotes

**Defined:** 2026-06-18
**Core Value:** All 3 assignment parts pass + 7 security controls demoed (SECR4483 group project rubric: auth module analysis, transaction module analysis, integrated secure app with >=7 controls, plus video demo golden path)

## v1 Requirements

Requirements for initial release. Each maps to exactly one roadmap phase. Derived from the Approved design SPEC (`docs/superpowers/specs/2026-06-17-utm-securenotes-design.md`) and the 10-task implementation plan (`docs/superpowers/plans/2026-06-17-utm-securenotes.md`).

### Setup

- [ ] **SETUP-01**: Project dependencies are pinned and installable (Flask 3, SQLAlchemy, Flask-WTF, Flask-Mail, Flask-Bcrypt, `cryptography`, `bleach`, PyMySQL, pytest)
- [ ] **SETUP-02**: App factory creates a configured Flask app with db/bcrypt/mail/csrf extensions initialized
- [ ] **SETUP-03**: Three blueprints (`auth`, `notes`, `admin`) are registered with correct URL prefixes
- [ ] **SETUP-04**: HTTP security headers (X-Content-Type-Options, X-Frame-Options, Content-Security-Policy) are set on every response
- [ ] **SETUP-05**: 403/404/500 error handlers render generic templates (no stack traces exposed)
- [ ] **SETUP-06**: App runs locally over self-signed TLS via `run.py` (`ssl_context='adhoc'`, debug=False)
- [ ] **SETUP-07**: Test harness (pytest + pytest-flask + sqlite in-memory TestConfig) is in place and a smoke test runs

### Data

- [ ] **DATA-01**: `users` table stores email (UNIQUE, UTM-restricted), bcrypt password_hash, vault_salt, RSA public/encrypted-private keypair, role, is_verified, is_active, timestamps
- [ ] **DATA-02**: `otp_tokens` table stores bcrypt-hashed OTP, expiry, and used flag per user
- [ ] **DATA-03**: `notes` table stores title/body ciphertext blobs with a **dedicated `nonce BINARY(12)` column** (locked: not prepended to ciphertext)
- [ ] **DATA-04**: `note_keys` table stores wrapped per-note key, key_type, and a **dedicated `key_nonce BINARY(12)` column** for vault-wrapped rows (locked: not prepended to the wrapped-key blob)
- [ ] **DATA-05**: `note_access` table stores per-(note, user) permission grants (read/write) with timestamp
- [ ] **DATA-06**: `audit_logs` table stores user_id, action, ip_address, user_agent, created_at for every security-relevant event

### Crypto

- [ ] **CRYPTO-01**: AES-256-GCM encrypt/decrypt helpers exist and round-trip correctly, using the dedicated nonce-column scheme (nonce passed/read separately, not prepended) for notes and note_keys call sites
- [ ] **CRYPTO-02**: Each AES-256-GCM encryption call uses a unique random 12-byte nonce; tampered ciphertext fails authentication
- [ ] **CRYPTO-03**: `derive_vault_key` deterministically derives a 32-byte key via PBKDF2HMAC-SHA256 with 600,000 iterations from password + vault_salt
- [ ] **CRYPTO-04**: Per-note AES-256 key generation, vault-key wrapping, and unwrapping round-trip correctly
- [ ] **CRYPTO-05**: RSA-2048 keypair generation and RSA-OAEP encrypt/decrypt of a note key round-trip correctly
- [ ] **CRYPTO-06**: `users.rsa_private_key_encrypted` continues to use prepended-nonce blob format (no dedicated column) per locked SPEC exception

### Access

- [ ] **ACCESS-01**: `login_required` decorator redirects unauthenticated/unverified/inactive users to login
- [ ] **ACCESS-02**: `admin_required` decorator returns 403 for non-admin users and redirects unauthenticated users to login
- [ ] **ACCESS-03**: Stub routes exist so decorator behavior is independently testable before full blueprints are built

### Auth

- [ ] **AUTH-01**: Registration accepts only `@graduate.utm.my` emails (regex-enforced) and rejects others with a clear error
- [ ] **AUTH-02**: Registration enforces password policy (>=12 chars, upper+lower+digit+symbol) and rejects weak passwords
- [ ] **AUTH-03**: Registration hashes password with bcrypt (cost 12), generates vault_salt, generates RSA-2048 keypair, encrypts private key with vault_key derived from the submitted password, and creates an unverified user
- [ ] **AUTH-04**: Registration generates a 6-digit OTP, bcrypt-hashes it, stores it with a 10-minute TTL, and emails it via SMTP
- [ ] **AUTH-05**: OTP verification checks the hash and expiry, marks the user verified on success, and shows a generic invalid/expired message on failure
- [ ] **AUTH-06**: OTP can be resent on request (rate-limited)
- [ ] **AUTH-07**: Login rejects unverified or inactive users and wrong passwords with a generic message (no user enumeration)
- [ ] **AUTH-08**: Login enforces rate limiting — 5 failed attempts trigger a 15-minute lockout
- [ ] **AUTH-09**: Successful login derives and stores vault_key in session, regenerates the session ID (fixation prevention), records last_login_at, and logs a `login` audit event
- [ ] **AUTH-10**: Logout clears the session (including vault_key) immediately and logs a `logout` audit event

### Notes

- [ ] **NOTES-01**: Authenticated user can create a note; title/body are sanitized (bleach), encrypted with a fresh per-note AES-256 key, and the key is wrapped with the user's vault_key and stored in note_keys
- [ ] **NOTES-02**: Authenticated user can view a note they own or have access to; title/body are decrypted and rendered with output escaping
- [ ] **NOTES-03**: Note owner can edit a note; content is re-encrypted with a new per-note key and the owner's note_keys row is re-wrapped
- [ ] **NOTES-04**: Note owner can delete a note; the note and all its note_keys rows are removed
- [ ] **NOTES-05**: User can list their owned notes and notes shared with them, showing decrypted titles only
- [ ] **NOTES-06**: Non-owner without an access grant cannot view a note (403, no data leaked)
- [ ] **NOTES-07**: Only the owner can edit or delete a note (non-owner edit/delete attempts are rejected)

### Share

- [ ] **SHARE-01**: Note owner can share a note with another verified, active `@graduate.utm.my` user by email, choosing read or write permission
- [ ] **SHARE-02**: Sharing wraps the note's AES key with the recipient's RSA public key (RSA-OAEP) and inserts a `note_keys` (key_type='rsa') row plus a `note_access` row
- [ ] **SHARE-03**: Sharing rejects non-UTM recipient emails and unknown/unverified recipients with a clear error
- [ ] **SHARE-04**: Recipient can decrypt and view a shared note using their RSA private key (itself unwrapped via their own vault_key)
- [ ] **SHARE-05**: Sharing the same note with the same recipient twice is rejected (no duplicate access rows)

### Admin

- [ ] **ADMIN-01**: Admin can view a list of all users with role/verified/active status
- [ ] **ADMIN-02**: Admin can suspend a non-admin user (sets is_active=False) and the action is audit-logged
- [ ] **ADMIN-03**: Admin can reactivate a suspended user (sets is_active=True) and the action is audit-logged
- [ ] **ADMIN-04**: Admin can view a paginated audit log of all security-relevant actions
- [ ] **ADMIN-05**: Non-admin (student) users are blocked from all `/admin` routes with 403
- [ ] **ADMIN-06**: Admin accounts have no `note_keys` rows ever created for them — cryptographically barred from reading any note content, not merely access-control barred

### UI

- [ ] **UI-01**: A shared base template provides consistent navbar, flash messages, and Bootstrap 5 styling across all pages
- [ ] **UI-02**: Every state-changing form includes a CSRF token, and CSRF validation rejects forged requests
- [ ] **UI-03**: Security headers (CSP, X-Frame-Options, X-Content-Type-Options) are verified present via automated test

### Integration

- [ ] **INTEG-01**: Root URL (`/`) redirects to the login page
- [ ] **INTEG-02**: Full automated test suite passes with zero failures
- [ ] **INTEG-03**: Manual golden-path walkthrough succeeds end-to-end: register -> OTP verify -> login -> create note -> view decrypted note -> edit note -> share note with second account -> recipient views shared note -> admin views user list -> admin suspends a user -> suspended user blocked from login -> admin views audit logs showing all prior actions
- [ ] **INTEG-04**: Manual/tool-based vulnerability checks confirm: SQL injection blocked on login, XSS blocked in note title/body, session ID changes on login (fixation prevention), CSRF rejected on forged note delete, brute-force lockout triggers, unauthorized note access returns 403 with no data leaked

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap (academic project — no v2 planned, listed for completeness per template).

### Future Hardening

- **FUT-01**: Automatic re-encryption/re-wrapping of RSA-shared note keys when the owner edits a note (currently a documented limitation — shared recipients' keys go stale after an edit)
- **FUT-02**: Optional OTP step at login (SPEC marks OTP as required at registration, optional at login — not implemented as a login-time toggle in v1)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Production deployment (real CA TLS, cloud hosting, managed MySQL) | Assignment is local-dev-only; no production target exists |
| OAuth/SSO login | Assignment mandates UTM email + password + OTP as the auth model |
| Real-time collaborative note editing | Sharing is access-grant based, not live co-editing |
| Mobile-native app | Bootstrap 5 responsive web UI satisfies the rubric |
| Automatic key re-wrap for RSA-shared recipients on edit | Documented academic-project limitation (see FUT-01); would need key escrow design in production |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 1 | Pending |
| SETUP-02 | Phase 1 | Pending |
| SETUP-03 | Phase 1 | Pending |
| SETUP-04 | Phase 1 | Pending |
| SETUP-05 | Phase 1 | Pending |
| SETUP-06 | Phase 1 | Pending |
| SETUP-07 | Phase 1 | Pending |
| DATA-01 | Phase 2 | Pending |
| DATA-02 | Phase 2 | Pending |
| DATA-03 | Phase 2 | Pending |
| DATA-04 | Phase 2 | Pending |
| DATA-05 | Phase 2 | Pending |
| DATA-06 | Phase 2 | Pending |
| CRYPTO-01 | Phase 3 | Pending |
| CRYPTO-02 | Phase 3 | Pending |
| CRYPTO-03 | Phase 3 | Pending |
| CRYPTO-04 | Phase 3 | Pending |
| CRYPTO-05 | Phase 3 | Pending |
| CRYPTO-06 | Phase 3 | Pending |
| ACCESS-01 | Phase 4 | Pending |
| ACCESS-02 | Phase 4 | Pending |
| ACCESS-03 | Phase 4 | Pending |
| AUTH-01 | Phase 5 | Pending |
| AUTH-02 | Phase 5 | Pending |
| AUTH-03 | Phase 5 | Pending |
| AUTH-04 | Phase 5 | Pending |
| AUTH-05 | Phase 5 | Pending |
| AUTH-06 | Phase 5 | Pending |
| AUTH-07 | Phase 5 | Pending |
| AUTH-08 | Phase 5 | Pending |
| AUTH-09 | Phase 5 | Pending |
| AUTH-10 | Phase 5 | Pending |
| NOTES-01 | Phase 6 | Pending |
| NOTES-02 | Phase 6 | Pending |
| NOTES-03 | Phase 6 | Pending |
| NOTES-04 | Phase 6 | Pending |
| NOTES-05 | Phase 6 | Pending |
| NOTES-06 | Phase 6 | Pending |
| NOTES-07 | Phase 6 | Pending |
| SHARE-01 | Phase 7 | Pending |
| SHARE-02 | Phase 7 | Pending |
| SHARE-03 | Phase 7 | Pending |
| SHARE-04 | Phase 7 | Pending |
| SHARE-05 | Phase 7 | Pending |
| ADMIN-01 | Phase 8 | Pending |
| ADMIN-02 | Phase 8 | Pending |
| ADMIN-03 | Phase 8 | Pending |
| ADMIN-04 | Phase 8 | Pending |
| ADMIN-05 | Phase 8 | Pending |
| ADMIN-06 | Phase 8 | Pending |
| UI-01 | Phase 9 | Pending |
| UI-02 | Phase 9 | Pending |
| UI-03 | Phase 9 | Pending |
| INTEG-01 | Phase 10 | Pending |
| INTEG-02 | Phase 10 | Pending |
| INTEG-03 | Phase 10 | Pending |
| INTEG-04 | Phase 10 | Pending |

**Coverage:**
- v1 requirements: 53 total
- Mapped to phases: 53
- Unmapped: 0

---
*Requirements defined: 2026-06-18*
*Last updated: 2026-06-18 after initial roadmap creation*

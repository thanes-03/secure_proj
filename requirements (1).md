# Constraints (from SPECs)

source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md (status: Approved)

## CONST-tech-stack
type: nfr
Backend: Python 3.12 + Flask. Database: MySQL 8 via SQLAlchemy ORM. Frontend: HTML + Bootstrap 5 + vanilla JS. Cryptography: Python `cryptography` library (AES-256-GCM, PBKDF2, RSA-2048). Forms/CSRF: Flask-WTF. Email (OTP): Flask-Mail via SMTP. Input sanitization: `bleach`. Password hashing: `bcrypt` (cost factor 12).
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 2

## CONST-architecture
type: protocol
Flask app with three blueprints: `auth` (register, OTP, login, logout), `notes` (CRUD, share), `admin` (user management, audit logs). Browser communicates over HTTPS (self-signed TLS in dev) to Flask app, which talks to MySQL.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 3

## CONST-user-roles
type: nfr
Two roles: `student` (register, login, full CRUD + share on own notes) and `admin` (view/suspend/activate users, view audit logs; explicitly cannot access note content — no `note_keys` rows exist for admin accounts, a cryptographic enforcement, not just an authorization check).
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 4

## CONST-db-schema-users
type: schema
`users` table: id PK, email UNIQUE (must end `@graduate.utm.my`), password_hash (bcrypt cost 12), vault_salt BINARY(32), rsa_public_key TEXT (PEM), rsa_private_key_encrypted BLOB (encrypted with vault_key, nonce prepended to blob — no dedicated nonce column), role ENUM('student','admin') default student, is_verified BOOLEAN, is_active BOOLEAN, created_at, last_login_at.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 5

## CONST-db-schema-otp-tokens
type: schema
`otp_tokens` table: id PK, user_id FK, token_hash (bcrypt hash of 6-digit OTP), expires_at (10-min TTL), used BOOLEAN (one-time use enforced).
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 5

## CONST-db-schema-notes
type: schema
`notes` table: id PK, owner_id FK, title_ciphertext BLOB (AES-256-GCM), body_ciphertext BLOB (AES-256-GCM), **nonce BINARY(12) as a dedicated column** (random per encryption — NOT prepended to ciphertext), created_at, updated_at.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 5
NOTE: see conflicts report — implementation (DOC) does not implement a dedicated nonce column; see CONFLICT-001.

## CONST-db-schema-note-keys
type: schema
`note_keys` table: id PK, note_id FK, user_id FK (one row per note/user pair), encrypted_note_key BLOB (note's AES key wrapped with user's vault_key or RSA public key), **key_nonce BINARY(12) as a dedicated column** (nonce used when wrapping the note key, vault-type rows only), key_type ENUM('vault','rsa').
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 5
NOTE: see conflicts report — implementation (DOC) does not implement a dedicated key_nonce column; see CONFLICT-001.

## CONST-db-schema-note-access
type: schema
`note_access` table: note_id FK, user_id FK, permission ENUM('read','write'), shared_at.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 5

## CONST-db-schema-audit-logs
type: schema
`audit_logs` table: id PK, user_id FK, action VARCHAR(100) (e.g. 'login', 'note_create', 'share_note', 'login_failed'), ip_address VARCHAR(45), user_agent TEXT, created_at.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 5

## CONST-auth-registration-flow
type: protocol
Registration: email + password submitted → server validates email regex `^[a-zA-Z0-9._%+\-]+@graduate\.utm\.my$` and password policy (>=12 chars, upper+lower+digit+symbol) → bcrypt hash (cost 12) → vault_salt = os.urandom(32) → RSA-2048 keypair generated, private key encrypted with vault_key derived immediately from submitted password → user saved with is_verified=False → 6-digit OTP generated, bcrypt-hashed, stored with 10-min TTL → OTP emailed via SMTP → user submits OTP → server verifies hash → is_verified=True.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 6

## CONST-auth-login-flow
type: protocol
Login: check user exists, is_verified=True, is_active=True → bcrypt.verify password → on success: derive vault_key = PBKDF2HMAC(SHA-256, password, vault_salt, 600,000 iterations), store vault_key in server-side session (signed Flask cookie), regenerate session ID (prevents session fixation), log 'login' to audit_logs → on failure: log 'login_failed', generic error message (no user enumeration), rate limit 5 failed attempts -> 15-minute lockout.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 6

## CONST-session-management
type: nfr
Inactivity timeout 30 minutes. Session ID regenerated on login and privilege change. Logout clears vault_key from session immediately. CSRF token required on every state-changing form (Flask-WTF).
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 6

## CONST-encryption-vault-key
type: schema
vault_key = PBKDF2HMAC(SHA-256, length=32, salt=user.vault_salt, iterations=600,000)(password). Derived on every successful login — never stored in the database.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 7

## CONST-encryption-note-create
type: protocol
note_key = os.urandom(32) (random AES-256 key); nonce = os.urandom(12) (random GCM nonce); title_ct/body_ct = AES_256_GCM.encrypt(note_key, nonce, plaintext); key_nonce = os.urandom(12); encrypted_note_key = AES_256_GCM.encrypt(vault_key, key_nonce, note_key); insert into notes(title_ct, body_ct, nonce); insert into note_keys(note_id, user_id, encrypted_note_key, key_type='vault').
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 7

## CONST-encryption-note-read
type: protocol
encrypted_note_key = SELECT FROM note_keys WHERE note_id AND user_id; note_key = AES_256_GCM.decrypt(vault_key, encrypted_note_key); plaintext = AES_256_GCM.decrypt(note_key, nonce, ciphertext); plaintext served in response, never written to disk.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 7

## CONST-encryption-note-share
type: protocol
Sharer already holds note_key (unwrapped from own note_keys row); recipient_pub_key = SELECT rsa_public_key FROM users WHERE email = recipient_email; encrypted_note_key = RSA_OAEP.encrypt(recipient_pub_key, note_key); insert into note_keys(note_id, recipient_id, encrypted_note_key, key_type='rsa'); insert into note_access(note_id, recipient_id, permission). Recipient decrypts RSA-wrapped note key with their RSA private key, itself unwrapped via their vault_key.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 7

## CONST-routes-auth
type: api-contract
`/auth` blueprint: GET/POST `/auth/register`, GET/POST `/auth/verify-otp`, POST `/auth/resend-otp` (rate-limited), GET/POST `/auth/login`, POST `/auth/logout`.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 8

## CONST-routes-notes
type: api-contract
`/notes` blueprint: GET `/notes/` (list titles, decrypt titles only), GET/POST `/notes/new`, GET `/notes/<id>` (view, decrypt+render), GET/POST `/notes/<id>/edit` (owner only), POST `/notes/<id>/delete` (owner only, deletes note + all note_keys), GET/POST `/notes/<id>/share`.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 8

## CONST-routes-admin
type: api-contract
`/admin` blueprint: GET `/admin/users`, POST `/admin/users/<id>/suspend`, POST `/admin/users/<id>/activate`, GET `/admin/audit-logs` (paginated).
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 8

## CONST-access-control-rules
type: nfr
Every `/notes` request requires is_authenticated AND is_verified AND is_active. Edit/delete restricted to note.owner_id == current_user.id. Reading a shared note requires a note_access row for current_user.id. All `/admin` routes require current_user.role == 'admin'. Admin accounts have no note_keys rows — cryptographically barred from note content (not just access-control barred).
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 9

## CONST-security-controls-rubric
type: nfr
Seven required security controls: (1) input validation & output sanitization (bleach + Jinja2 auto-escape), (2) MFA (email OTP, required on registration, optional on login), (3) RBAC (student vs admin via decorator), (4) secure session management (30-min timeout, session regen on login, CSRF tokens), (5) encrypted storage (AES-256-GCM per-note + RSA-2048 wrapping), (6) secure transmission (self-signed TLS/HTTPS in dev), (7) error handling (generic messages, no stack traces in prod, no user enumeration).
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 10

## CONST-assignment-coverage
type: nfr
Maps to SECR4483 Secure Programming group project rubric: Part 1 Auth Module Analysis (5 marks) — naive vs secure registration/login showing SQLi/XSS/weak-password/session fixes; Part 2 Transaction Module Analysis (5 marks) — naive vs secure note CRUD/sharing showing session fixation/authorization/client-state/sanitization fixes; Part 3 Integrated Secure App (7 marks) — full app, all 7 controls, Burp Suite/OWASP ZAP testing, technical report; Video Presentation (3 marks) — full demo walkthrough.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 11

## CONST-input-sanitization
type: nfr
All user text input processed through bleach.clean() before encryption. SQLAlchemy ORM parameterizes all queries (no raw SQL). Jinja2 templates use `{{ var }}` auto-escaping. No raw exception messages exposed to users. `flask run --no-debugger` in production. HTTP security headers required: X-Content-Type-Options, X-Frame-Options, Content-Security-Policy.
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 12

## CONST-vulnerability-testing-plan
type: nfr
Tools: Burp Suite Community or OWASP ZAP. Required test coverage: SQL injection on login (parameterized queries block it), XSS in note title/body (bleach+Jinja2 escaping blocks it), session fixation (session ID changes on login), CSRF on note delete (CSRF token validation rejects forged requests), brute force login (rate limit + lockout triggers), unauthorized note access (403 returned, no data leaked).
source: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md, section 13

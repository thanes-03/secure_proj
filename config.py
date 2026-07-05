# Transaction Receipts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a transaction module that records a signed, tamper-evident receipt every time a note is shared, downloadable only by the sender and receiver; then make the app runnable locally for a browser demo.

**Architecture:** Extend the existing `notes` blueprint. On share, snapshot the note title into a new `transactions` row encrypted under a per-transaction key `K_t` (wrapped for both parties, mirroring the note-key pattern), and sign a canonical `{file_name, sender, receiver, time}` message with the sender's RSA private key. Downloads decrypt the snapshot, verify the signature, and serve a JSON receipt. A dev config (SQLite + OTP echo) makes the golden path clickable without MySQL or SMTP.

**Tech Stack:** Flask 3, Flask-SQLAlchemy, `cryptography` (RSA-PSS/SHA-256, RSA-OAEP, AES-256-GCM), pytest, Bootstrap (CDN) templates.

## Global Constraints

- **Signing:** RSA-PSS with SHA-256 and MGF1-SHA256, using each user's existing RSA-2048 keypair. Verification returns a boolean, never raises.
- **Zero plaintext at rest:** the note title ("file name") is never stored in plaintext. It lives only as AES-256-GCM ciphertext under `K_t`.
- **Two parties only:** only a transaction's `sender_id` or `receiver_id` may list or download it. Admins are not exempt → `403`.
- **Self-contained receipts:** a receipt must remain downloadable and verifiable after the underlying note is edited or deleted. It must not read from the live `notes`/`note_keys` rows at download time.
- **Nonce discipline:** every AES-GCM encryption uses a fresh 12-byte nonce via `generate_nonce()`, stored in its own column (never prepended), consistent with the existing schema.
- **Follow existing patterns:** module-level helpers in `app/notes/routes.py`, `bleach.clean` on user input, `_audit(...)` for audit logging, Bootstrap templates extending `base.html`, tests on in-memory SQLite via the `client`/`app`/`db` fixtures.
- **Production security is never weakened:** all dev conveniences (SQLite default, OTP echo) are opt-in behind config flags that are OFF in `Config` and `TestConfig`.

---

## File Structure

**Create:**
- `.env` — local-only (gitignored) env vars so `config` imports and the app runs locally.
- `app/templates/notes/transactions.html` — the Transactions list page.
- `tests/test_transactions.py` — feature tests for the transaction module.
- `tests/test_dev_run.py` — smoke test for local-run enablement.

**Modify:**
- `app/crypto.py` — add `rsa_sign` / `rsa_verify`.
- `app/models.py` — add `Transaction` model.
- `app/notes/routes.py` — receipt helpers, transaction creation in `share_note`, `list_transactions`, `download_transaction`, null-out in `delete_note`.
- `app/templates/base.html` — add "Transactions" nav link for logged-in users.
- `config.py` — add `DevConfig` with SQLite + `OTP_DEV_ECHO`.
- `run.py` — select config via `FLASK_CONFIG`.
- `app/__init__.py` — register an `init-db` CLI command.
- `app/auth/routes.py` — dev-only OTP echo in `_send_otp`, gated by `OTP_DEV_ECHO`.
- `tests/test_crypto.py` — add sign/verify tests.

---

## Task 1: Local environment so the suite runs

**Files:**
- Create: `.env` (gitignored — never committed)

**Interfaces:**
- Produces: importable `config` module; a working `pytest` run. All later tasks depend on this.

Rationale: `config.py:7-8,14-16` read `os.environ['SECRET_KEY']`, `['DATABASE_URL']`, `['MAIL_USERNAME']`, `['MAIL_PASSWORD']` at import time in the base `Config` class. `TestConfig` subclasses `Config`, so importing `config` at all requires these vars. `load_dotenv()` (`config.py:4`) reads `.env`, which does not exist yet. `.env` is already in `.gitignore:21`, so it stays local.

- [ ] **Step 1: Create `.env`**

Create `C:\Users\NAVVEEN\projects\UTM-SecureNotes\.env` with:

```
SECRET_KEY=dev-local-secret-change-me-0123456789abcdef0123456789abcdef
DATABASE_URL=sqlite:///securenotes.db
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=dev@example.com
MAIL_PASSWORD=dev-placeholder
```

- [ ] **Step 2: Confirm the existing suite runs green**

Run: `python -m pytest -q`
Expected: all existing tests pass (this proves Python, deps, and config import work). If this fails to import `config`, re-check `.env` exists in the project root.

- [ ] **Step 3: Commit**

Note: `.env` is gitignored, so nothing is committed here. This is a local setup gate only. Do not `git add .env`. Proceed to Task 2.

---

## Task 2: RSA signing primitives

**Files:**
- Modify: `app/crypto.py`
- Test: `tests/test_crypto.py`

**Interfaces:**
- Produces:
  - `rsa_sign(private_pem: bytes, message: bytes) -> bytes`
  - `rsa_verify(public_pem: bytes, message: bytes, signature: bytes) -> bool`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_crypto.py` (extend the existing import from `app.crypto` to include `rsa_sign, rsa_verify`):

```python
def test_rsa_sign_verify_roundtrip():
    from app.crypto import generate_rsa_keypair, rsa_sign, rsa_verify
    private_pem, public_pem = generate_rsa_keypair()
    message = b'{"file_name":"note","sender":"a","receiver":"b","time":"t"}'
    sig = rsa_sign(private_pem, message)
    assert rsa_verify(public_pem, message, sig) is True

def test_rsa_verify_rejects_altered_message():
    from app.crypto import generate_rsa_keypair, rsa_sign, rsa_verify
    private_pem, public_pem = generate_rsa_keypair()
    sig = rsa_sign(private_pem, b'original')
    assert rsa_verify(public_pem, b'tampered', sig) is False

def test_rsa_verify_rejects_wrong_key():
    from app.crypto import generate_rsa_keypair, rsa_sign, rsa_verify
    priv1, _ = generate_rsa_keypair()
    _, pub2 = generate_rsa_keypair()
    sig = rsa_sign(priv1, b'msg')
    assert rsa_verify(pub2, b'msg', sig) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_crypto.py -k rsa_sign or rsa_verify -v`
Expected: FAIL with `ImportError` / `cannot import name 'rsa_sign'`.

- [ ] **Step 3: Implement the primitives**

In `app/crypto.py`, add the import near the top (with the other `cryptography` imports):

```python
from cryptography.exceptions import InvalidSignature
```

Append at the end of the file:

```python
def rsa_sign(private_pem: bytes, message: bytes) -> bytes:
    """RSA-PSS/SHA-256 sign a message with a PEM private key."""
    priv = serialization.load_pem_private_key(private_pem, password=None)
    return priv.sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )


def rsa_verify(public_pem: bytes, message: bytes, signature: bytes) -> bool:
    """Verify an RSA-PSS/SHA-256 signature. Returns False on any failure."""
    pub = serialization.load_pem_public_key(public_pem)
    try:
        pub.verify(
            signature,
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_crypto.py -v`
Expected: all crypto tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/crypto.py tests/test_crypto.py
git commit -m "feat: add RSA-PSS sign/verify primitives"
```

---

## Task 3: Transaction model

**Files:**
- Modify: `app/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `Transaction` model with columns:
  `id, note_id (nullable FK notes.id ON DELETE SET NULL), sender_id, receiver_id, sender_email, receiver_email, created_at, filename_ciphertext, filename_nonce, kt_sender_wrapped, kt_sender_nonce, kt_receiver_wrapped, signature`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_models.py`:

```python
def test_transaction_persists(app, db):
    import os
    from app.models import User, Transaction
    from app.extensions import db as _db
    from datetime import datetime
    with app.app_context():
        u1 = User(email='s@graduate.utm.my', password_hash='x', vault_salt=os.urandom(32))
        u2 = User(email='r@graduate.utm.my', password_hash='x', vault_salt=os.urandom(32))
        _db.session.add_all([u1, u2])
        _db.session.flush()
        tx = Transaction(
            note_id=None,
            sender_id=u1.id, receiver_id=u2.id,
            sender_email=u1.email, receiver_email=u2.email,
            created_at=datetime.utcnow().replace(microsecond=0),
            filename_ciphertext=b'ct', filename_nonce=os.urandom(12),
            kt_sender_wrapped=b'sw', kt_sender_nonce=os.urandom(12),
            kt_receiver_wrapped=b'rw', signature=b'sig',
        )
        _db.session.add(tx)
        _db.session.commit()
        got = Transaction.query.first()
        assert got.sender_email == 's@graduate.utm.my'
        assert got.receiver_email == 'r@graduate.utm.my'
        assert got.signature == b'sig'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py::test_transaction_persists -v`
Expected: FAIL with `cannot import name 'Transaction'`.

- [ ] **Step 3: Implement the model**

In `app/models.py`, append after the `AuditLog` class:

```python
class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('notes.id', ondelete='SET NULL'), nullable=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender_email = db.Column(db.String(255), nullable=False)
    receiver_email = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    filename_ciphertext = db.Column(db.LargeBinary, nullable=False)
    filename_nonce = db.Column(db.LargeBinary(12), nullable=False)
    kt_sender_wrapped = db.Column(db.LargeBinary, nullable=False)
    kt_sender_nonce = db.Column(db.LargeBinary(12), nullable=False)
    kt_receiver_wrapped = db.Column(db.LargeBinary, nullable=False)
    signature = db.Column(db.LargeBinary, nullable=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py::test_transaction_persists -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models.py
git commit -m "feat: add Transaction model for share receipts"
```

---

## Task 4: Create signed transaction on share

**Files:**
- Modify: `app/notes/routes.py`
- Test: `tests/test_transactions.py` (create)

**Interfaces:**
- Consumes: `rsa_sign` (Task 2), `Transaction` (Task 3), existing `aes_encrypt`, `aes_decrypt`, `generate_nonce`, `generate_note_key`, `wrap_key_with_vault`, `rsa_encrypt_key`, `aes_decrypt_sealed`, `_resolve_note_key`, `_audit`.
- Produces:
  - module-level `_receipt_message(file_name: str, sender_email: str, receiver_email: str, created_at: datetime) -> bytes` (canonical JSON, sorted keys, compact separators, time as `%Y-%m-%dT%H:%M:%SZ`).
  - A `Transaction` row written inside `share_note`'s success branch, in the same commit as the existing `NoteKey`/`NoteAccess`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_transactions.py`:

```python
import os
from app.extensions import db as _db, bcrypt
from app.crypto import (
    derive_vault_key, generate_rsa_keypair, aes_encrypt_sealed, rsa_verify,
)


def _make_verified_user(app, email, password='TxPass1!abcd'):
    vault_salt = os.urandom(32)
    vault_key = derive_vault_key(password, vault_salt)
    private_pem, public_pem = generate_rsa_keypair()
    from app.models import User
    with app.app_context():
        user = User(
            email=email,
            password_hash=bcrypt.generate_password_hash(password, rounds=4).decode(),
            vault_salt=vault_salt,
            rsa_public_key=public_pem.decode(),
            rsa_private_key_encrypted=aes_encrypt_sealed(vault_key, private_pem),
            is_verified=True, is_active=True,
        )
        _db.session.add(user)
        _db.session.commit()
        return user.id, vault_key


def _login(client, user_id, vault_key, is_admin=False):
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['vault_key'] = vault_key.hex()
        sess['is_admin'] = is_admin


def _share(client, app, sender_id, sender_vault, recipient_email, title='Meeting notes'):
    _login(client, sender_id, sender_vault)
    client.post('/notes/new', data={'title': title, 'body': 'body text'})
    from app.models import Note
    with app.app_context():
        note = Note.query.filter_by(owner_id=sender_id).order_by(Note.id.desc()).first()
        note_id = note.id
    client.post(f'/notes/{note_id}/share',
                data={'recipient_email': recipient_email, 'permission': 'read'})
    return note_id


def test_share_creates_signed_transaction(client, app, db):
    s_id, s_vault = _make_verified_user(app, 'sender@graduate.utm.my')
    r_id, _ = _make_verified_user(app, 'recv@graduate.utm.my')
    _share(client, app, s_id, s_vault, 'recv@graduate.utm.my', title='Budget')

    from app.models import Transaction, User
    from app.notes.routes import _receipt_message
    with app.app_context():
        tx = Transaction.query.first()
        assert tx is not None
        assert tx.sender_email == 'sender@graduate.utm.my'
        assert tx.receiver_email == 'recv@graduate.utm.my'
        # signature verifies against the sender's public key over the canonical message
        sender = User.query.get(tx.sender_id)
        msg = _receipt_message('Budget', tx.sender_email, tx.receiver_email, tx.created_at)
        assert rsa_verify(sender.rsa_public_key.encode(), msg, tx.signature) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_transactions.py::test_share_creates_signed_transaction -v`
Expected: FAIL (`cannot import name '_receipt_message'` / no `Transaction` row created).

- [ ] **Step 3: Implement receipt message + transaction creation**

In `app/notes/routes.py`, update imports. Add near the top:

```python
import json
import base64
from datetime import datetime
from flask import Response, current_app
```

Extend the models import to include `Transaction`, and the crypto import to include `rsa_sign, rsa_verify`:

```python
from ..models import User, Note, NoteKey, NoteAccess, AuditLog, Transaction
from ..crypto import (
    generate_nonce, aes_encrypt, aes_decrypt, aes_decrypt_sealed,
    generate_note_key,
    wrap_key_with_vault, unwrap_key_with_vault,
    rsa_encrypt_key, rsa_decrypt_key,
    rsa_sign, rsa_verify,
)
```

Add a module-level helper (near `_audit`):

```python
def _receipt_message(file_name, sender_email, receiver_email, created_at):
    """Canonical, deterministic byte string that gets signed/verified."""
    return json.dumps({
        'file_name': file_name,
        'sender': sender_email,
        'receiver': receiver_email,
        'time': created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
    }, sort_keys=True, separators=(',', ':')).encode()
```

In `share_note`, inside the `if form.validate_on_submit():` block, after the existing
`db.session.add(NoteAccess(...))` line and **before** `db.session.commit()`, insert:

```python
        # --- Transaction receipt (signed, self-contained snapshot) ---
        title_plain = aes_decrypt(note_key, note.nonce, note.title_ciphertext)
        kt = generate_note_key()
        fn_nonce = generate_nonce()
        filename_ciphertext = aes_encrypt(kt, fn_nonce, title_plain)
        kt_sender_nonce, kt_sender_wrapped = wrap_key_with_vault(vault_key, kt)
        kt_receiver_wrapped = rsa_encrypt_key(recipient.rsa_public_key.encode(), kt)
        tx_created_at = datetime.utcnow().replace(microsecond=0)
        private_pem = aes_decrypt_sealed(vault_key, user.rsa_private_key_encrypted)
        signature = rsa_sign(private_pem, _receipt_message(
            title_plain.decode(), user.email, recipient.email, tx_created_at))
        db.session.add(Transaction(
            note_id=note.id,
            sender_id=user.id, receiver_id=recipient.id,
            sender_email=user.email, receiver_email=recipient.email,
            created_at=tx_created_at,
            filename_ciphertext=filename_ciphertext, filename_nonce=fn_nonce,
            kt_sender_wrapped=kt_sender_wrapped, kt_sender_nonce=kt_sender_nonce,
            kt_receiver_wrapped=kt_receiver_wrapped, signature=signature,
        ))
```

Then, immediately after the existing `_audit(user.id, 'note_share')` line, add:

```python
        _audit(user.id, 'transaction_create')
```

(Note: `note_key`, `vault_key`, `user`, and `recipient` are already in scope in this branch — see the existing `note_key = _resolve_note_key(...)` line.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_transactions.py::test_share_creates_signed_transaction -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite (regression check)**

Run: `python -m pytest -q`
Expected: all tests pass (existing share tests unaffected).

- [ ] **Step 6: Commit**

```bash
git add app/notes/routes.py tests/test_transactions.py
git commit -m "feat: create signed transaction receipt on note share"
```

---

## Task 5: Download route with verification and access control

**Files:**
- Modify: `app/notes/routes.py`
- Test: `tests/test_transactions.py`

**Interfaces:**
- Consumes: `_receipt_message` (Task 4), `Transaction`, `rsa_verify`, `unwrap_key_with_vault`, `rsa_decrypt_key`, `aes_decrypt`, `aes_decrypt_sealed`.
- Produces:
  - module-level `_resolve_kt(tx, user, vault_key) -> bytes`
  - route `download_transaction` at `GET /notes/transactions/<int:tx_id>/download`, serving `transaction-<id>.json`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_transactions.py`:

```python
import json


def _get_tx_id(app):
    from app.models import Transaction
    with app.app_context():
        return Transaction.query.first().id


def test_both_parties_download_and_verify(client, app, db):
    s_id, s_vault = _make_verified_user(app, 'snd2@graduate.utm.my')
    r_id, r_vault = _make_verified_user(app, 'rcv2@graduate.utm.my')
    _share(client, app, s_id, s_vault, 'rcv2@graduate.utm.my', title='Report')
    tx_id = _get_tx_id(app)

    # sender downloads
    _login(client, s_id, s_vault)
    resp = client.get(f'/notes/transactions/{tx_id}/download')
    assert resp.status_code == 200
    assert resp.mimetype == 'application/json'
    payload = json.loads(resp.data)
    assert payload['file_name'] == 'Report'
    assert payload['sender'] == 'snd2@graduate.utm.my'
    assert payload['receiver'] == 'rcv2@graduate.utm.my'
    assert 'signature' in payload

    # receiver downloads
    _login(client, r_id, r_vault)
    resp = client.get(f'/notes/transactions/{tx_id}/download')
    assert resp.status_code == 200
    assert json.loads(resp.data)['file_name'] == 'Report'


def test_third_party_and_admin_cannot_download(client, app, db):
    s_id, s_vault = _make_verified_user(app, 'snd3@graduate.utm.my')
    _make_verified_user(app, 'rcv3@graduate.utm.my')
    third_id, third_vault = _make_verified_user(app, 'third@graduate.utm.my')
    admin_id, admin_vault = _make_verified_user(app, 'admin@graduate.utm.my')
    _share(client, app, s_id, s_vault, 'rcv3@graduate.utm.my')
    tx_id = _get_tx_id(app)

    _login(client, third_id, third_vault)
    assert client.get(f'/notes/transactions/{tx_id}/download').status_code == 403

    _login(client, admin_id, admin_vault, is_admin=True)
    assert client.get(f'/notes/transactions/{tx_id}/download').status_code == 403


def test_download_rejects_tampered_signature(client, app, db):
    s_id, s_vault = _make_verified_user(app, 'snd4@graduate.utm.my')
    r_id, r_vault = _make_verified_user(app, 'rcv4@graduate.utm.my')
    _share(client, app, s_id, s_vault, 'rcv4@graduate.utm.my')
    tx_id = _get_tx_id(app)

    from app.models import Transaction
    with app.app_context():
        tx = Transaction.query.get(tx_id)
        tx.signature = tx.signature[:-1] + bytes([tx.signature[-1] ^ 0xFF])
        _db.session.commit()

    _login(client, r_id, r_vault)
    resp = client.get(f'/notes/transactions/{tx_id}/download', follow_redirects=False)
    assert resp.status_code == 302  # refused → redirect with flash, not a JSON file
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_transactions.py -k download -v`
Expected: FAIL (route does not exist → 404).

- [ ] **Step 3: Implement `_resolve_kt` and the download route**

In `app/notes/routes.py`, add the helper near `_resolve_note_key`:

```python
def _resolve_kt(tx, user, vault_key: bytes) -> bytes:
    """Recover a transaction's per-receipt key K_t for the requesting party."""
    if user.id == tx.sender_id:
        return unwrap_key_with_vault(vault_key, tx.kt_sender_nonce, tx.kt_sender_wrapped)
    private_pem = aes_decrypt_sealed(vault_key, user.rsa_private_key_encrypted)
    return rsa_decrypt_key(private_pem, tx.kt_receiver_wrapped)
```

Add the route (place it after `share_note`):

```python
@bp.route('/transactions/<int:tx_id>/download')
@login_required
def download_transaction(tx_id):
    tx = Transaction.query.get_or_404(tx_id)
    user = _current_user()
    if user.id not in (tx.sender_id, tx.receiver_id):
        abort(403)
    vault_key = _vault_key()
    kt = _resolve_kt(tx, user, vault_key)
    file_name = aes_decrypt(kt, tx.filename_nonce, tx.filename_ciphertext).decode()
    sender = User.query.get(tx.sender_id)
    message = _receipt_message(file_name, tx.sender_email, tx.receiver_email, tx.created_at)
    if not rsa_verify(sender.rsa_public_key.encode(), message, tx.signature):
        flash('Receipt failed signature verification — it may have been tampered with.', 'danger')
        return redirect(url_for('notes.list_transactions'))
    receipt = {
        'file_name': file_name,
        'sender': tx.sender_email,
        'receiver': tx.receiver_email,
        'time': tx.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'signature': base64.b64encode(tx.signature).decode(),
        'signature_algorithm': 'RSASSA-PSS / SHA-256',
        'sender_public_key': sender.rsa_public_key,
    }
    _audit(user.id, 'transaction_download')
    return Response(
        json.dumps(receipt, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename=transaction-{tx.id}.json'},
    )
```

Note: the route references `notes.list_transactions`, added in Task 6. Implement Task 6 before running the app, but the download tests here do not hit the redirect success path except in the tamper test — which needs `list_transactions` to exist for `url_for`. Implement Task 6 immediately after this task's code (they can share one test run) OR temporarily point the redirect at `notes.list_notes`. Recommended: proceed to Task 6 code before Step 4 so `url_for` resolves.

- [ ] **Step 4: Run tests to verify they pass**

(After Task 6's route exists.)
Run: `python -m pytest tests/test_transactions.py -k download -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/notes/routes.py tests/test_transactions.py
git commit -m "feat: download signed transaction receipt with verification + access control"
```

---

## Task 6: Transactions list page and nav link

**Files:**
- Modify: `app/notes/routes.py`
- Create: `app/templates/notes/transactions.html`
- Modify: `app/templates/base.html`
- Test: `tests/test_transactions.py`

**Interfaces:**
- Consumes: `Transaction`, `_resolve_kt` (Task 5), `aes_decrypt`.
- Produces: route `list_transactions` at `GET /notes/transactions` rendering `notes/transactions.html` with `sent` and `received` lists of `(transaction, file_name)` tuples.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_transactions.py`:

```python
def test_transactions_list_scoped_to_parties(client, app, db):
    s_id, s_vault = _make_verified_user(app, 'lsnd@graduate.utm.my')
    r_id, r_vault = _make_verified_user(app, 'lrcv@graduate.utm.my')
    other_id, other_vault = _make_verified_user(app, 'lother@graduate.utm.my')
    _share(client, app, s_id, s_vault, 'lrcv@graduate.utm.my', title='SharedDoc')

    # sender sees it under Sent
    _login(client, s_id, s_vault)
    resp = client.get('/notes/transactions')
    assert resp.status_code == 200
    assert b'SharedDoc' in resp.data
    assert b'lrcv@graduate.utm.my' in resp.data

    # receiver sees it too
    _login(client, r_id, r_vault)
    assert b'SharedDoc' in client.get('/notes/transactions').data

    # uninvolved user does not
    _login(client, other_id, other_vault)
    assert b'SharedDoc' not in client.get('/notes/transactions').data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_transactions.py::test_transactions_list_scoped_to_parties -v`
Expected: FAIL (route 404 / template missing).

- [ ] **Step 3: Implement the list route**

In `app/notes/routes.py`, add:

```python
@bp.route('/transactions')
@login_required
def list_transactions():
    user = _current_user()
    vault_key = _vault_key()
    txs = Transaction.query.filter(
        (Transaction.sender_id == user.id) | (Transaction.receiver_id == user.id)
    ).order_by(Transaction.created_at.desc()).all()

    def _fn(tx):
        try:
            kt = _resolve_kt(tx, user, vault_key)
            return aes_decrypt(kt, tx.filename_nonce, tx.filename_ciphertext).decode()
        except Exception:
            return '[Decryption error]'

    sent = [(t, _fn(t)) for t in txs if t.sender_id == user.id]
    received = [(t, _fn(t)) for t in txs if t.receiver_id == user.id]
    return render_template('notes/transactions.html', sent=sent, received=received)
```

- [ ] **Step 4: Create the template**

Create `app/templates/notes/transactions.html`:

```html
{% extends 'base.html' %}
{% block title %}Transactions{% endblock %}
{% block content %}
<div class="mt-4">
  <h2>Transaction Receipts</h2>

  <h4 class="mt-4">Sent</h4>
  {% if sent %}
  <table class="table table-sm align-middle">
    <thead><tr><th>File</th><th>Recipient</th><th>Time</th><th></th></tr></thead>
    <tbody>
    {% for tx, fname in sent %}
      <tr>
        <td>{{ fname | e }}</td>
        <td>{{ tx.receiver_email | e }}</td>
        <td>{{ tx.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
        <td><a class="btn btn-sm btn-outline-primary"
               href="{{ url_for('notes.download_transaction', tx_id=tx.id) }}">Download</a></td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}<p class="text-muted">No sent transactions.</p>{% endif %}

  <h4 class="mt-4">Received</h4>
  {% if received %}
  <table class="table table-sm align-middle">
    <thead><tr><th>File</th><th>Sender</th><th>Time</th><th></th></tr></thead>
    <tbody>
    {% for tx, fname in received %}
      <tr>
        <td>{{ fname | e }}</td>
        <td>{{ tx.sender_email | e }}</td>
        <td>{{ tx.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
        <td><a class="btn btn-sm btn-outline-primary"
               href="{{ url_for('notes.download_transaction', tx_id=tx.id) }}">Download</a></td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}<p class="text-muted">No received transactions.</p>{% endif %}

  <a href="{{ url_for('notes.list_notes') }}" class="btn btn-sm btn-link">Back to notes</a>
</div>
{% endblock %}
```

- [ ] **Step 5: Add the nav link**

In `app/templates/base.html`, replace this block:

```html
      {% if session.get('user_id') %}
        {% if session.get('is_admin') %}
        <a href="{{ url_for('admin.users') }}" class="btn btn-sm btn-outline-light">Admin</a>
        {% endif %}
```

with:

```html
      {% if session.get('user_id') %}
        <a href="{{ url_for('notes.list_transactions') }}" class="btn btn-sm btn-outline-light">Transactions</a>
        {% if session.get('is_admin') %}
        <a href="{{ url_for('admin.users') }}" class="btn btn-sm btn-outline-light">Admin</a>
        {% endif %}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_transactions.py -v`
Expected: all transaction tests PASS (including the download tests from Task 5, whose redirect target now resolves).

- [ ] **Step 7: Commit**

```bash
git add app/notes/routes.py app/templates/notes/transactions.html app/templates/base.html tests/test_transactions.py
git commit -m "feat: transactions list page and nav link"
```

---

## Task 7: Receipts survive note edit and deletion

**Files:**
- Modify: `app/notes/routes.py` (`delete_note`)
- Test: `tests/test_transactions.py`

**Interfaces:**
- Consumes: `Transaction`.
- Produces: `delete_note` nulls `transactions.note_id` for the deleted note before deleting it (DB-agnostic; does not rely on SQLite FK enforcement).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_transactions.py`:

```python
def test_receipt_survives_note_edit(client, app, db):
    s_id, s_vault = _make_verified_user(app, 'esnd@graduate.utm.my')
    r_id, r_vault = _make_verified_user(app, 'ercv@graduate.utm.my')
    note_id = _share(client, app, s_id, s_vault, 'ercv@graduate.utm.my', title='Original Title')
    tx_id = _get_tx_id(app)

    # owner edits the note (rotates its key/nonce)
    _login(client, s_id, s_vault)
    client.post(f'/notes/{note_id}/edit', data={'title': 'Changed Title', 'body': 'new'})

    # receipt still downloads and shows the SHARE-TIME title
    _login(client, r_id, r_vault)
    resp = client.get(f'/notes/transactions/{tx_id}/download')
    assert resp.status_code == 200
    assert json.loads(resp.data)['file_name'] == 'Original Title'


def test_receipt_survives_note_deletion(client, app, db):
    s_id, s_vault = _make_verified_user(app, 'dsnd@graduate.utm.my')
    r_id, r_vault = _make_verified_user(app, 'drcv@graduate.utm.my')
    note_id = _share(client, app, s_id, s_vault, 'drcv@graduate.utm.my', title='Doomed Note')
    tx_id = _get_tx_id(app)

    _login(client, s_id, s_vault)
    client.post(f'/notes/{note_id}/delete')

    from app.models import Transaction
    with app.app_context():
        tx = Transaction.query.get(tx_id)
        assert tx is not None
        assert tx.note_id is None

    _login(client, r_id, r_vault)
    resp = client.get(f'/notes/transactions/{tx_id}/download')
    assert resp.status_code == 200
    assert json.loads(resp.data)['file_name'] == 'Doomed Note'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_transactions.py -k survives -v`
Expected: `test_receipt_survives_note_deletion` FAILS on `tx.note_id is None` (still points at the deleted note). `test_receipt_survives_note_edit` should already PASS (receipt is self-contained) — that confirms the design; keep the test.

- [ ] **Step 3: Null out `note_id` on delete**

In `app/notes/routes.py`, in `delete_note`, replace:

```python
    db.session.delete(note)
    db.session.commit()
```

with:

```python
    Transaction.query.filter_by(note_id=note.id).update({'note_id': None})
    db.session.delete(note)
    db.session.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_transactions.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add app/notes/routes.py tests/test_transactions.py
git commit -m "feat: keep transaction receipts when their note is deleted"
```

---

## Task 8: Dev config with SQLite + config selection

**Files:**
- Modify: `config.py`
- Modify: `run.py`

**Interfaces:**
- Produces: `DevConfig(Config)` with SQLite URI, suppressed mail, `OTP_DEV_ECHO=True`, `SESSION_COOKIE_SECURE=False`. `run.py` selects config via `FLASK_CONFIG` (`dev` → `DevConfig`, else `Config`).

- [ ] **Step 1: Add `DevConfig`**

In `config.py`, append after `TestConfig`:

```python
class DevConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///securenotes.db')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-not-for-production')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'dev@example.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'dev')
    MAIL_DEFAULT_SENDER = MAIL_USERNAME
    MAIL_SUPPRESS_SEND = True
    SESSION_COOKIE_SECURE = False
    OTP_DEV_ECHO = True
```

Also add the default flag to the base `Config` so it always exists. In `config.py`, inside `class Config`, add one line (e.g. after `WTF_CSRF_ENABLED = True`):

```python
    OTP_DEV_ECHO = False
```

- [ ] **Step 2: Select config in `run.py`**

Replace the contents of `run.py` with:

```python
import os
from app import create_app
from config import Config, DevConfig

_configs = {'dev': DevConfig, 'production': Config}
app = create_app(_configs.get(os.environ.get('FLASK_CONFIG', 'production'), Config))

if __name__ == '__main__':
    app.run(ssl_context='adhoc', debug=False)
```

- [ ] **Step 3: Verify import + existing suite still green**

Run: `python -m pytest -q`
Expected: all tests pass (no behavior change for `Config`/`TestConfig`).

- [ ] **Step 4: Commit**

```bash
git add config.py run.py
git commit -m "feat: add DevConfig (SQLite, dev OTP flag) and FLASK_CONFIG selection"
```

---

## Task 9: init-db CLI command

**Files:**
- Modify: `app/__init__.py`

**Interfaces:**
- Produces: `flask --app run init-db` CLI command that runs `db.create_all()`.

- [ ] **Step 1: Register the command**

In `app/__init__.py`, inside `create_app`, before `return app`, add:

```python
    @app.cli.command('init-db')
    def init_db():
        """Create all database tables (dev/local use)."""
        db.create_all()
        print('Database tables created.')
```

(`db` is already imported at the top of `app/__init__.py`.)

- [ ] **Step 2: Verify the command creates tables on SQLite**

Run:
```bash
FLASK_CONFIG=dev flask --app run init-db
```
Expected output: `Database tables created.` and a `securenotes.db` file appears in the project root. (It is gitignored via `*.db`.)

- [ ] **Step 3: Commit**

```bash
git add app/__init__.py
git commit -m "feat: add init-db CLI command for local table creation"
```

---

## Task 10: Dev-only OTP echo

**Files:**
- Modify: `app/auth/routes.py`
- Test: `tests/test_dev_run.py` (created in Task 11 also exercises this; a focused unit test is added here)

**Interfaces:**
- Consumes: `current_app.config['OTP_DEV_ECHO']`.
- Produces: when `OTP_DEV_ECHO` is true, `_send_otp` flashes and logs the plaintext OTP so the demo can proceed without a real inbox. Default (`Config`/`TestConfig`) behavior is unchanged.

- [ ] **Step 1: Write the failing test**

Create `tests/test_dev_run.py`:

```python
import re
from app.crypto import derive_vault_key


def test_register_echoes_otp_in_dev(monkeypatch, app, client, db):
    # Force dev echo on for this app instance
    app.config['OTP_DEV_ECHO'] = True
    resp = client.post('/auth/register', data={
        'email': 'echo@graduate.utm.my',
        'password': 'StrongPass1!xy',
    }, follow_redirects=True)
    # the 6-digit code is surfaced on the page in dev mode
    assert re.search(rb'\b\d{6}\b', resp.data)
```

Note: form fields verified against `app/auth/forms.py` — `RegistrationForm` = `email` + `password` (no confirm), `OTPForm` = `token`, `LoginForm` = `email` + `password`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dev_run.py::test_register_echoes_otp_in_dev -v`
Expected: FAIL (no 6-digit code in the response).

- [ ] **Step 3: Implement the echo**

In `app/auth/routes.py`, add `current_app` to the flask import:

```python
from flask import render_template, redirect, url_for, session, request, flash, current_app
```

In `_send_otp`, replace:

```python
    msg = Message('UTM SecureNotes — Verification Code', recipients=[user.email])
    msg.body = f'Your code: {otp}\n\nExpires in 10 minutes. Do not share this.'
    mail.send(msg)
```

with:

```python
    msg = Message('UTM SecureNotes — Verification Code', recipients=[user.email])
    msg.body = f'Your code: {otp}\n\nExpires in 10 minutes. Do not share this.'
    mail.send(msg)
    if current_app.config.get('OTP_DEV_ECHO'):
        current_app.logger.warning('DEV OTP for %s: %s', user.email, otp)
        flash(f'[DEV MODE] Your verification code is {otp}', 'info')
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dev_run.py::test_register_echoes_otp_in_dev -v`
Expected: PASS.

- [ ] **Step 5: Confirm default behavior unchanged**

Run: `python -m pytest -q`
Expected: all tests pass; existing auth tests (which run under `TestConfig`, `OTP_DEV_ECHO` false) are unaffected.

- [ ] **Step 6: Commit**

```bash
git add app/auth/routes.py tests/test_dev_run.py
git commit -m "feat: dev-only OTP echo behind OTP_DEV_ECHO flag"
```

---

## Task 11: End-to-end dev-run smoke test

**Files:**
- Modify: `tests/test_dev_run.py`

**Interfaces:**
- Consumes: `DevConfig` (Task 8), `init-db` behavior via `create_all` (Task 9), OTP echo (Task 10), the full share + download flow.
- Produces: a smoke test proving the golden path works under a DevConfig-like setup on a file-backed SQLite DB, no external services.

- [ ] **Step 1: Write the smoke test**

Append to `tests/test_dev_run.py`:

```python
import re
import pytest
from app import create_app
from app.extensions import db as _db
from config import DevConfig


@pytest.fixture()
def dev_app(tmp_path):
    class _SmokeConfig(DevConfig):
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{tmp_path / "smoke.db"}'
        WTF_CSRF_ENABLED = False  # exercise the flow, not CSRF (see config.py TestConfig note)
        OTP_DEV_ECHO = True
    app = create_app(_SmokeConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


def _register_verify_login(app, client, email, password='SmokePass1!xy'):
    resp = client.post('/auth/register', data={
        'email': email, 'password': password,
    }, follow_redirects=True)
    otp = re.search(rb'\b(\d{6})\b', resp.data).group(1).decode()
    client.post('/auth/verify-otp', data={'token': otp}, follow_redirects=True)
    client.post('/auth/login', data={'email': email, 'password': password},
                follow_redirects=True)


def test_dev_golden_path(dev_app):
    client = dev_app.test_client()
    sender_client = dev_app.test_client()
    _register_verify_login(dev_app, sender_client, 'gsnd@graduate.utm.my')

    recv_client = dev_app.test_client()
    _register_verify_login(dev_app, recv_client, 'grcv@graduate.utm.my')

    # sender creates + shares a note
    sender_client.post('/notes/new', data={'title': 'Demo Note', 'body': 'hello'})
    from app.models import Note, Transaction
    with dev_app.app_context():
        note = Note.query.first()
        note_id = note.id
    sender_client.post(f'/notes/{note_id}/share',
                       data={'recipient_email': 'grcv@graduate.utm.my', 'permission': 'read'})

    with dev_app.app_context():
        tx_id = Transaction.query.first().id

    # receiver downloads the receipt
    resp = recv_client.get(f'/notes/transactions/{tx_id}/download')
    assert resp.status_code == 200
    import json
    assert json.loads(resp.data)['file_name'] == 'Demo Note'
```

Note: form fields verified against `app/auth/forms.py` — register uses `email`+`password`, verify uses `token`, login uses `email`+`password`.

- [ ] **Step 2: Run the smoke test**

Run: `python -m pytest tests/test_dev_run.py::test_dev_golden_path -v`
Expected: PASS.

- [ ] **Step 3: Run the entire suite**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_dev_run.py
git commit -m "test: end-to-end dev-run golden path smoke test"
```

---

## Manual verification (after the plan is complete)

For the video demo, run the app live over local HTTPS with SQLite and dev OTP:

```bash
FLASK_CONFIG=dev flask --app run init-db      # once, creates securenotes.db
FLASK_CONFIG=dev python run.py                # serves https://127.0.0.1:5000 (adhoc TLS; accept the browser warning)
```

Golden path: register (read the `[DEV MODE]` OTP flash) → verify → login → create note → share with a second account → open **Transactions** → Download the receipt (JSON with file name, sender, receiver, time, signature) → log in as the recipient → Transactions → Download the same receipt. Confirm a third account gets 403 on that receipt's download URL.

---

## Self-Review Notes

- **Spec coverage:** signed receipt (T2, T4), sender-key signing (T4), title-encrypted-at-rest via `K_t` snapshot (T3, T4), two-party-only access incl. admin 403 (T5), Transactions page + nav (T6), survives edit/delete (T7), crypto unit tests (T2), local-run: SQLite DevConfig (T8), table creation (T9), dev OTP echo (T10), dev smoke test (T11). All spec sections mapped.
- **Type consistency:** `_receipt_message(file_name, sender_email, receiver_email, created_at)` and `_resolve_kt(tx, user, vault_key)` used identically in creation (T4), download (T5), and list (T6). Column names match the `Transaction` model (T3) everywhere.
- **Known cross-task ordering:** Task 5's tamper test and download success path reference `notes.list_transactions` (Task 6). Implement Task 6's route before running Task 5 Step 4, as flagged in Task 5 Step 3.
- **Form field names:** verified against `app/auth/forms.py` — `RegistrationForm`=`email`+`password` (no confirm field), `OTPForm`=`token`, `LoginForm`=`email`+`password`. Test data in Tasks 10–11 matches.

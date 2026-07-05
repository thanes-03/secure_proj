## Conflict Detection Report

### BLOCKERS (0)

None. No ADRs were present in this ingest batch (only one SPEC and one DOC), so no LOCKED-vs-LOCKED contradictions, no LOCKED-vs-existing-context contradictions, and no UNKNOWN-confidence-low classifications were found. Cycle detection on the cross-ref graph (DOC → SPEC, single edge) found no cycles.

### WARNINGS (0)

None. No PRD-type documents were present in this ingest batch, so there are no competing acceptance-criteria variants to reconcile.

### INFO (1)

[INFO] Auto-resolved: SPEC > DOC on note/note_key nonce storage — DOC's own implementation contradicts DOC's own narrative claim of spec-compliance
  Found: docs/superpowers/specs/2026-06-17-utm-securenotes-design.md (status: Approved) section 5 defines `notes.nonce BINARY(12)` and `note_keys.key_nonce BINARY(12)` as dedicated columns, explicitly separate from the ciphertext blobs.
  Found: docs/superpowers/plans/2026-06-17-utm-securenotes.md preamble asserts: "Per the spec schema, `notes.nonce` and `note_keys.key_nonce` are dedicated columns (nonces are NOT prepended to ciphertext for these two tables)."
  Found: docs/superpowers/plans/2026-06-17-utm-securenotes.md Task 2 Step 2 (`app/models.py`) defines `Note` with only `title_ciphertext`/`body_ciphertext` (no `nonce` column) and `NoteKey` with only `encrypted_note_key` (no `key_nonce` column).
  Found: docs/superpowers/plans/2026-06-17-utm-securenotes.md Task 3 Step 2 (`app/crypto.py`) implements `aes_encrypt`/`aes_decrypt` to always prepend the 12-byte nonce to the ciphertext blob ("Returns nonce(12) + ciphertext + tag"), and this same helper is used for notes, note_keys, and the RSA-private-key blob alike — i.e. every call site uses prepended-nonce, not a dedicated column.
  Note: SPEC (Approved status) outranks DOC by default precedence ["ADR","SPEC","PRD","DOC"]. The SPEC's dedicated-column schema wins for synthesized intel (recorded in constraints.md as CONST-db-schema-notes and CONST-db-schema-note-keys). The DOC's actual code (prepended-nonce, no dedicated columns) is the losing variant, even though the DOC's own prose falsely claims compliance with the dedicated-column design.
  Impact: This is not a simple precedence pick — it indicates the implementation plan's code does not match its own stated intent, which suggests the plan was not verified against the spec before being written, or the spec changed after the plan was drafted. If the DOC's code is later treated as ground truth (e.g. by an agent that already started building from it), the resulting DB schema will silently diverge from the Approved SPEC.
  → Recommend: before routing to the roadmapper, decide whether the SPEC's dedicated-nonce-column design is still wanted (more relational/queryable, slightly more verbose) or whether the simpler prepended-nonce approach (less schema, what the plan's code already implements) should be retroactively approved and the SPEC updated to match. Either way, the SPEC document and the implementation plan currently disagree and only one should remain the source of truth for the `notes` and `note_keys` table definitions going forward.

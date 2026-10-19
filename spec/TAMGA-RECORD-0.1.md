# TAMGA Record 0.1

**Status:** draft · **Editors:** TAMGA project · **Date:** 2026-10-17

> **Qisqacha (o'zbekcha):** TAMGA Record — AI agent harakatlarini o'zgartirib bo'lmaydigan jurnalga yozish
> uchun ochiq format. Har bir yozuv kanonik JSON (RFC 8785) qatori. Yozuvlar SHA-256 xesh-zanjir
> bilan bog'lanadi va RFC 9162 uslubidagi Merkle daraxtiga tushadi. Davriy checkpoint'lar
> Ed25519 va ML-DSA-65 bilan **ikkalasi birga** imzolanadi. Har qanday uchinchi tomon shu hujjat
> va `test-vectors/` bo'yicha jurnalni mustaqil tekshira oladi.

The key words MUST, MUST NOT, SHOULD and MAY are to be interpreted as described in RFC 2119.

> **Naming.** Earlier drafts called this format "AAR (Agent Action Record)". It was renamed before
> publication because "Agent Action Receipt" and its "AARP" profile are already used by Pipelock.
> The version member is `tamga`, the JSON profile is *TR-JSON*.

## 1. Goals

A TAMGA log is an append-only record of what an AI agent did, what it was allowed to do, and who
decided. It is designed so that a third party holding only this document, the log files and a
public key can determine — without trusting the software that wrote them — whether any record
was altered, removed, reordered or inserted.

Non-goals for 0.1: confidentiality of the log itself (payloads are kept out of the log, §5),
preventing deletion of the whole log by a privileged local user (detected via external
checkpoint witnesses, §7.4).

## 2. Encoding

### 2.1 Canonical JSON

Every record and checkpoint is serialized as **JCS** (RFC 8785) restricted to the following
subset, called *TR-JSON*:

- Values are objects, arrays, strings, `true`, `false`, `null` and **integers**.
- Integers MUST lie in `[-(2^53 - 1), 2^53 - 1]` and are written in shortest decimal form with no
  sign for zero, no leading zeros, no fraction and no exponent. Non-integer numbers MUST NOT appear.
  The token `-0` MUST NOT appear (JSON parsers disagree on whether it is an integer); a line
  containing it is rejected by the byte comparison of §2.2.
  (This removes the ECMAScript number-formatting step of RFC 8785 and makes independent
  implementations trivial.)
- Object members are sorted by key, comparing keys as sequences of **UTF-16 code units**.
  Duplicate keys MUST NOT appear.
- Strings are emitted between `"` with these escapes only: `\"`, `\\`, `\b`, `\f`, `\n`, `\r`,
  `\t`; any other code point below U+0020 as `\u00XX` with **lowercase** hex; every other code point
  literally in UTF-8. Lone surrogates MUST NOT appear.
- No whitespace between tokens.

### 2.2 Log files

A log is a UTF-8 text file. Each line is one record in TR-JSON followed by a single `\n`
(0x0A). A line MUST be byte-identical to the canonical serialization of the value it parses to.
A verifier detects non-canonical lines by re-serializing and comparing bytes; this also rejects
duplicate keys, whitespace and floats.

### 2.3 Primitive encodings

| Name | Encoding |
|---|---|
| digest | `"sha256:"` followed by 64 lowercase hex characters |
| bytes (keys, signatures) | base64url without padding (RFC 4648 §5) |
| timestamp | `YYYY-MM-DDTHH:MM:SS.sssZ` — UTC, exactly 3 fractional digits, 24 characters |

`H(x)` denotes SHA-256. `||` denotes byte concatenation. `JCS(v)` denotes the TR-JSON bytes of `v`.
`v \ k` denotes object `v` with member `k` removed.

## 3. Records

### 3.1 Required members

| Member | Type | Meaning |
|---|---|---|
| `tamga` | string | format version, `"0.1"` |
| `log` | string | log identifier, 1–128 characters from `[A-Za-z0-9._:-]` |
| `seq` | integer | position in the log, starting at `0`, incremented by exactly 1 |
| `ts` | timestamp | time the record was written |
| `session` | string | agent session identifier |
| `event` | string | event type, §3.3 |
| `prev` | digest | `hash` of record `seq - 1`; for `seq = 0` the *genesis digest* `"sha256:" + "0"×64` |
| `hash` | digest | record hash, §3.2 |

### 3.2 Record hash

```
hash = "sha256:" || hex( H( 0x00 || JCS(record \ "hash") ) )
```

The `0x00` prefix makes the record hash identical to the RFC 9162 Merkle **leaf hash** of
`JCS(record \ "hash")`, so the hash chain and the Merkle tree (§6) commit to the same values.

### 3.3 Events

| `event` | Written when |
|---|---|
| `session.start` / `session.end` | an agent session begins / ends |
| `prompt` | a user prompt is submitted to the agent |
| `tool.pre` | the agent announces a tool call, before execution; carries `decision` |
| `tool.post` | the tool call finished; carries the result digest |
| `decision.human` | a human resolved an `ask` decision |
| `os.observed` | the operating system observed an action (file, process, network) |
| `key.rotate` | the signing key is replaced; carries `key_rotation` (§7.5) |
| `control` | a control request to the log writer (accepted or refused), or a configuration / agent-integration change it observed; carries `control` |

Verifiers MUST accept unknown `event` values (and report them as warnings) so that the format
can grow without breaking old verifiers.

### 3.4 Optional members

| Member | Shape |
|---|---|
| `agent` | `{"kind": string, "version"?: string, "model"?: string}` |
| `actor` | `{"user": string, "host": string}` |
| `tool` | `{"name": string, "input": payload-ref}` |
| `result` | payload-ref (for `tool.post`) |
| `decision` | `{"verdict": "allow" \| "deny" \| "ask", "by": "policy" \| "human" \| "default", "policy"?: string, "reason"?: string}` |
| `ref` | integer — `seq` of the record this one answers (e.g. `tool.post` → its `tool.pre`) |
| `control` | `{"op": string, "accepted": bool, "client"?: {"pid": integer, "image": string, "from_agent": bool}, "reason"?: string, ...}` — for `event` = `control`; `ref` names the record a `decide` answers |
| `ext` | object — vendor extensions, keys SHOULD be reverse-DNS names |

Unknown top-level members MUST be accepted; they are covered by `hash` like any other member.

## 4. Example

```json
{"tamga":"0.1","decision":{"by":"policy","policy":"no-secret-exfil","verdict":"deny"},"event":"tool.pre","hash":"sha256:…","log":"demo","prev":"sha256:…","seq":1,"session":"s1","tool":{"input":{"digest":"sha256:…","size":42},"name":"Bash"},"ts":"2026-10-17T10:41:07.118Z"}
```

Exact bytes and hashes for a complete chain are in `test-vectors/chain.json`.

## 5. Payload commitments

Command lines, file contents and tool outputs can contain secrets and personal data. They are
therefore **not** written into the log. A record carries a *payload-ref*:

```
payload-ref = {"digest": digest, "size": integer, "vault"?: string}
digest      = "sha256:" || hex( H( "TAMGA-PAYLOAD-v1" || 0x00 || salt || payload ) )
```

`salt` is 32 random bytes generated per payload. The salt and the payload are stored together,
encrypted, outside the log (the *vault*). Destroying the vault entry (or its key) makes the
payload unrecoverable — crypto-shredding — while every record still verifies, because the log
commits only to the salted digest. Without the salt the digest reveals nothing about short or
guessable payloads.

## 6. Merkle tree

The tree is the RFC 9162 §2.1 Merkle Tree Hash over the sequence of record hashes, where the
record hash (§3.2) **is** the leaf hash:

```
MTH({})        = H("")                                   (the empty tree)
MTH({d0})      = d0                                      (d0 is a record hash)
MTH(D[n])      = H( 0x01 || MTH(D[0:k]) || MTH(D[k:n]) )  k = largest power of 2 < n
```

Inclusion proofs and consistency proofs follow RFC 9162 §2.1.3 and §2.1.4 exactly, with leaf
hashes taken from the records.

A proof binds a leaf to a root, not to a tree size: the size is trusted only when it comes from a
verified checkpoint (§7) that signs `size` and `root` together.

## 7. Checkpoints

### 7.1 Format

A checkpoint (a signed tree head) is an TR-JSON object, stored one per line in a separate
checkpoint file:

| Member | Type | Meaning |
|---|---|---|
| `tamga` | string | `"0.1"` |
| `type` | string | `"checkpoint"` |
| `log` | string | the log identifier |
| `size` | integer | number of records covered (`seq` 0 … `size-1`), ≥ 1 |
| `root` | digest | `MTH` of the first `size` record hashes |
| `last` | digest | `hash` of record `size - 1` |
| `ts` | timestamp | time of signing |
| `key` | string | key identifier, §7.3 |
| `sig` | object | `{"ed25519": bytes, "ml-dsa-65": bytes}` |

### 7.2 Signatures (hybrid AND)

```
M = "TAMGA-CHECKPOINT-v1" || 0x00 || JCS(checkpoint \ "sig")
sig.ed25519   = Ed25519.Sign(sk_ed, M)                          (RFC 8032, pure Ed25519)
sig.ml-dsa-65 = ML-DSA-65.Sign(sk_ml, M, ctx = "tamga-checkpoint")   (FIPS 204, pure ML-DSA)
```

A checkpoint is valid only if **both** signatures verify. Ed25519 verification MUST be strict:
non-canonical `S` and small-order public keys or `R` values are rejected (as in `verify_strict`
of ed25519-dalek). An attacker must therefore break both
a classical and a post-quantum scheme to forge one.

### 7.3 Keys

A public key file is an TR-JSON object:

```json
{"tamga":"0.1","ed25519":"<32 bytes>","key":"k:<32 hex>","ml-dsa-65":"<1952 bytes>","type":"public-key"}
```

```
key = "k:" || first 32 hex characters of hex( H( "TAMGA-KEY-v1" || 0x00 || pk_ed || pk_ml ) )
```

A verifier MUST recompute `key` from the two public keys and reject a mismatch.

### 7.4 Witnessing

Checkpoints SHOULD be copied to at least one witness that the log writer cannot rewrite (another
machine, a git remote, an RFC 3161 timestamp authority). A witness that holds checkpoint
`(size, root)` detects truncation or rewriting of the first `size` records, and a consistency
proof (§6) shows that a later checkpoint extends an earlier one.

### 7.5 Key rotation

A log outlives its signing key: keys are rotated on a schedule, replaced after a suspected
compromise, or re-established after a restore. Rotation is recorded **in the log itself**, so an
auditor needs only the first key (the *anchor*) from the operator.

A rotation is a record with `event` = `"key.rotate"` and the member:

```json
"key_rotation": {"from": key-id, "to": key-id, "reason": "scheduled" | "compromise" | "restore",
                 "ed25519": "<32 bytes>", "ml-dsa-65": "<1952 bytes>",
                 "proof": {"ed25519": bytes, "ml-dsa-65": bytes}}
```

```
P = "TAMGA-ROTATE-v1" || 0x00 || JCS({"from": from, "log": log, "seq": seq, "to": to})
proof = hybrid signature of P by the NEW key; ML-DSA context = "tamga-rotate"
```

`to` MUST equal the key identifier (§7.3) of the two new public keys, and `from` ≠ `to`. The proof
shows possession of the new key and binds it to this log and position; it cannot be moved to
another record.

The rotation is **authorized** by the first checkpoint that covers the record (`size > seq`) and
verifies under the key active at that time. Verification (extends §8):

1. The anchor is the active key.
2. Checkpoints are processed in file order. Each MUST verify under the active key (`key`
   mismatch → `E_CKPT_FORMAT`). After the checkpoint is fully checked, every not yet applied
   rotation with `seq < size` is applied in `seq` order: its `from` MUST equal the active key
   (`E_KEY_ROTATE` at the record's `seq`), and its `to` becomes the active key.
3. A rotation that no checkpoint authorizes yet is reported as a warning.
4. A rotation with `reason` = `"compromise"` is reported as a warning: checkpoints signed earlier
   by the compromised key are only as trustworthy as an independent witness copy of them.

Writers append the rotation record, immediately write a checkpoint with the **old** key, and only
then switch to the new key. The old private key is destroyed afterwards.

## 8. Verification

Given a log file, optionally a checkpoint file and a public key, a verifier processes lines in
order and stops at the **first** error, reporting its code and the zero-based line index
(which equals the expected `seq`).

| Code | Condition |
|---|---|
| `E_PARSE` | line is not valid JSON, or not an object |
| `E_NONCANONICAL` | line bytes differ from the canonical serialization (§2.2) |
| `E_VERSION` | `tamga` is not `"0.1"` |
| `E_FIELD` | a required member is missing or has the wrong type or format |
| `E_LOG` | `log` differs from the first record's `log` |
| `E_SEQ` | `seq` is not equal to the line index |
| `E_HASH` | `hash` does not match §3.2 — the record content was altered |
| `E_PREV` | `prev` is not the previous record's `hash` — a record was removed, inserted or reordered |
| `E_CKPT_FORMAT` | a checkpoint is malformed, or its `key` does not match the public key |
| `E_CKPT_SIG` | a checkpoint signature does not verify |
| `E_CKPT_SIZE` | a checkpoint covers more records than the log contains — the log was truncated |
| `E_CKPT_ROOT` | `root` or `last` does not match the log — records covered by the checkpoint were rewritten |
| `E_KEY_ROTATE` | a `key.rotate` record is malformed, its proof does not verify, or it rotates away from a key that is not active (§7.5); index = the record's `seq` |

Notes:

- `E_HASH` versus `E_PREV`: editing a record's content without recomputing its hash yields
  `E_HASH` at that record. Recomputing the hash yields `E_PREV` at the **next** record. Rewriting
  the whole tail consistently passes the chain check but fails `E_CKPT_ROOT` against any earlier
  checkpoint — which is why checkpoints and witnesses exist.
- Timestamps that go backwards are reported as warnings, not errors (clocks are adjusted).

## 9. Test vectors

`test-vectors/` contains, in TR-JSON:

| File | Content |
|---|---|
| `jcs.json` | input JSON text → canonical text, plus inputs that MUST be rejected |
| `chain.json` | a complete log (lines and record hashes) built from fixed inputs |
| `merkle.json` | roots for every prefix of the chain, inclusion and consistency proofs |
| `checkpoint.json` | key seeds, public keys, signed message `M` (hex), checkpoint line |
| `tamper.json` | modified logs with the exact expected error code and index |
| `rotation.json` | a log rotating key A → B (§7.5), valid and invalid checkpoint sets with expected results |

ML-DSA-65 key generation in the vectors uses the 32-byte seed ξ (FIPS 204 `ML-DSA.KeyGen_internal`)
and signing uses the deterministic variant (`rnd` = 32 zero bytes), so the vectors are
reproducible. Production signers SHOULD use the hedged (randomized) variant; verification is
identical for both.

## 10. Security considerations

- The log alone proves internal consistency, not completeness. Completeness against deletion of
  the tail requires checkpoints held by a witness.
- Signing keys SHOULD be protected by the operating system (DPAPI, TPM, Secure Enclave).
- A verifier MUST NOT trust any field of the log for verification parameters (e.g. it MUST take
  the public key from the operator, not from the log directory).
- Implementations SHOULD bound line length (TAMGA: 1 MiB) to avoid resource exhaustion.

## 11. Relationship to draft-sharif-agent-audit-trail-08

`draft-sharif-agent-audit-trail-08` (IETF individual draft, 2026-10-13; "the draft") specifies a
JSONL audit trail for AI agents with the same building blocks: SHA-256 over RFC 8785 JCS, a hash
chain, RFC 6962 Merkle batches, ML-DSA-65 with an optional hybrid classical signature, signed
tombstones and pre-execution recording of denied actions. TAMGA Record is **not byte-compatible**
with the draft; it is designed so that a TAMGA log can be **projected** into a draft-conformant
trail without loss of the security-relevant facts.

### 11.1 Deliberate differences

| Aspect | The draft | TAMGA Record | Reason |
|---|---|---|---|
| Chain input | `prev_hash = hex(SHA-256(JCS(previous record)))`, genesis `null` | `prev` = previous `hash` = `SHA-256(0x00 ‖ JCS(record \ "hash"))`, genesis all-zero digest | one value serves as chain link **and** Merkle leaf; no separate leaf computation |
| Digest encoding | 64 lowercase hex | `sha256:` + 64 lowercase hex | algorithm agility visible in the value |
| Numbers | JSON numbers incl. fractions (`risk_score`) | integers only (§2.1) | removes ECMAScript number formatting from every implementation |
| What is signed | each record (optional `signature`) | periodic checkpoints over a Merkle root (§7) | one hybrid signature (≈3.4 KB) per checkpoint instead of per record keeps hook latency and log size low |
| Hybrid mode | ML-DSA-65 + **ES256**, separate key ids (RFC 7638 thumbprints) | ML-DSA-65 + **Ed25519**, one combined key id (§7.3); both MUST verify | deterministic classical signatures, no nonce-reuse failure mode |
| Merkle | RFC 6962, batch object detached from the record | RFC 9162 over the whole log, inclusion and consistency proofs | consistency proofs let witnesses check that later checkpoints extend earlier ones |
| Pre-execution | `record_phase: "pre_execution"` REQUIRED for denied/escalated decisions | `event: "tool.pre"` with `decision` is written **before** the tool runs, for every verdict | same guarantee, applied to all decisions |
| Erasure | signed tombstone replaces the record; `content_fingerprint` retained | the record never contains the payload; the vault entry is destroyed (§5) | the chain and every checkpoint stay verifiable without rewriting any record |
| Completeness | inconclusive unless the trail ends with a session close record | signed checkpoints and witnesses detect truncation (§7.4, `E_CKPT_SIZE`) | — |

### 11.2 Projection to the draft

A TAMGA implementation MAY export a log as a draft-conformant trail (`tamga export --format
draft-sharif-08`, planned). The export is a **new, separately chained** trail: it recomputes
`prev_hash` with the draft's rule and signs records with an export key. It never replaces the
TAMGA log, which remains the evidence of record. Field mapping:

| Draft field | Source in TAMGA Record |
|---|---|
| `record_id` | UUIDv8 derived from `hash` (first 16 bytes, version/variant bits set) |
| `timestamp` | `ts` |
| `session_id` | `session` (or a UUIDv8 derived from it when not a UUID) |
| `agent_id`, `agent_version`, `model_id` | `agent.kind`, `agent.version`, `agent.model` |
| `principal` | `actor` → `{"principal_type": "human", "principal_id": "urn:tamga:user:<user>@<host>", "authority_ref": null}` |
| `action_type` | `tool.pre` → `"decision"`, `tool.post` → `"tool_response"`, `prompt`/`session.*` → `"lifecycle"`, `os.observed` → `"lifecycle"` with `ext` detail |
| `record_phase` | `tool.pre` → `"pre_execution"`, `tool.post` → `"post_execution"`, others → `"concurrent"` |
| `outcome` | `decision.verdict`: `allow` → `"success"`, `deny` → `"denied"`, `ask` → `"escalated"` |
| `action_detail` | `tool.name`, `decision.policy` → `policy_ref`; payloads only as their salted digests |
| `input_hash`, `output_hash` | `tool.input.digest`, `result.digest` (without the `sha256:` prefix) |
| `parent_record_id` | `record_id` of the previous exported record |
| `sequence_number` | `seq` |
| `trust_level` | configured per deployment (default `"L1"`) |
| `content_fingerprint` | not exported: TAMGA payload digests are salted and therefore not draft fingerprints |

Every exported record SHOULD carry the TAMGA `hash` it was derived from in an extension member so
that an auditor can cross-check the export against the signed TAMGA checkpoints.

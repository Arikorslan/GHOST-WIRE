# GHOSTWIRE — GW1 Encryption Documentation

**Protocol:** GW1 · **App version:** 1.1.0 · **Document edition:** 1.2 (2026-09-21)
**Authors:** @Ariko & Arena

This document is the authoritative reference for every cryptographic
mechanism used by the GHOSTWIRE messenger. The companion volume
(`GHOSTWIRE_Cryptography_Book.pdf`) covers the same material in
tutorial depth, prints the complete annotated source, and ships a
generated test-vector corpus.

---

## 1. Overview

GW1 is a two-party, session-based encrypted channel protocol designed
for hostile local networks (Wi-Fi segments, Bluetooth RFCOMM bridges,
ad-hoc relays). It is a **SIGMA-style authenticated ephemeral ECDH
handshake** followed by a **per-message ratcheted AES-256-GCM
transport**.

Design pillars:

1. **Mutual authentication** — every hello is signed with a long-term
   Ed25519 identity key; the server's signature additionally binds the
   client's hello (transcript binding), defeating relay/rebind attacks.
2. **Forward secrecy at message granularity** — a fresh AES-256 key is
   derived for *every* frame, then the previous chain state is erased.
3. **Explicit key confirmation** — both peers exchange HMAC proofs of
   the derived root key before any application traffic is accepted.
4. **Fail-closed verification** — every parse, length, signature and
   tag check raises `SecurityError`; there is no warning-only path.
5. **Auditable pure-Python public-key core** — X25519/Ed25519 run in
   interpreter-only Python (RFC 7748 / RFC 8032 designs), so the
   Android build can never fail on native-library loading.

---

## 2. Primitive inventory

| Layer | Primitive | Parameters | Source |
|---|---|---|---|
| Hash | SHA-256 | FIPS 180-4 | `hashlib` (CPython) |
| MAC | HMAC-SHA256 | RFC 2104 | `hmac` (stdlib), constant-time compare only |
| KDF | HKDF-SHA256 | RFC 5869, single-block OKM | PyCryptodome `Crypto.Protocol.KDF.HKDF` |
| AEAD | AES-256-GCM | 12-byte nonce, 16-byte tag | PyCryptodome `Crypto.Cipher.AES` |
| Key agreement | X25519 | RFC 7748, clamped scalars | pure Python, `gw/_curve25519.py` |
| Signatures | Ed25519 | RFC 8032 | pure Python, `gw/_curve25519.py` |
| Randomness | OS CSPRNG | — | `os.urandom` exclusively |

No legacy or custom primitives. No encryption is invented in-house;
composition and the key schedule are the protocol's contribution.

---

## 3. Identities

Each node owns one long-term **Ed25519 identity key**:

* secret seed: 32 bytes from `os.urandom(32)`;
* public key: `ed25519_public(secret)` (32 bytes);
* identity keys are used **only to sign hellos** — never for key
  agreement and never for transport (strict sign/encrypt role
  separation);
* UI fingerprint: `SHA-256(public)` rendered as the first 16 hex
  digits in four uppercase groups, e.g. `A1B2 C3D4 E5F6 0718`. Two
  users comparing fingerprints out-of-band detect MITM substitution.

---

## 4. Handshake

### 4.1 Message flow

```
client                                      server
──────                                      ──────
hello_c  ────────────────────────────────►  verify sig (bind="")
         ◄────────────────────────────────  hello_s  (bind=canonical(hello_c))
verify sig
derive()                                    derive()
confirm_c ───────────────────────────────►  verify MAC("client")
         ◄───────────────────────────────   confirm_s
verify MAC("server")
                ══ secure link ══
```

All messages travel in 4-byte big-endian length-prefixed frames;
`MAX_FRAME = 1 000 000` bytes is enforced before reading.

### 4.2 Hello object (JSON)

| Field | Meaning |
|---|---|
| `t` | `"hello"` |
| `role` | `"client"` or `"server"` (a peer claiming our role is rejected) |
| `e` | base64 ephemeral X25519 public key (fresh per session) |
| `i` | base64 long-term Ed25519 identity public key |
| `s` | base64 Ed25519 signature over the payload below |
| `v` | `"GW1"` protocol version literal |

**Signed payload** (UTF-8, exact string):

```
GW1|{role}|{e_b64}|{i_b64}|{bind}
```

* Client signs with `bind = ""`.
* Server signs with `bind = json.dumps(hello_c, sort_keys=True)` —
  the canonical JSON of the client's hello. This cryptographically
  binds the server's hello to this exact transcript: a recorded
  server hello cannot be replayed against a different client hello.

Both hellos' payloads are absorbed into a running
`SHA-256("GW1|session|v1")` transcript hash.

### 4.3 Verification rules (all fail-closed)

* role must be the opposite of ours, and one of the two literals;
* version must equal `GW1`;
* identity public key must be exactly 32 bytes;
* Ed25519 signature must verify over the exact payload;
* ephemeral key must be exactly 32 bytes;
* any violation raises `SecurityError` and tears the link down.

---

## 5. Key schedule

Let `shared = X25519(my_eph_secret, peer_eph_pub)` and
`sid = SHA-256(transcript)` (the **session id**, shown in the UI).
All derivations are HKDF-SHA256 with empty salt unless noted.

```
root      = HKDF(ikm=shared, salt=sid, info="GW1|root",            L=32)

chain_c2s = HKDF(ikm=root,                  info="GW1|chain|c2s",  L=32)
chain_s2c = HKDF(ikm=root,                  info="GW1|chain|s2c",  L=32)

# per frame, in each direction:
msg_key   = HKDF(ikm=chain,                 info="GW1|message-key", L=32)
chain'    = HKDF(ikm=chain,                 info="GW1|ratchet-step",L=32)

confirm_k = HKDF(ikm=root,                  info="GW1|confirm",    L=32)
mac(role) = HMAC-SHA256(confirm_k, role)          # role ∈ {"client","server"}
```

Properties:

* domain separation is by literal `info` strings — no two derived
  keys can collide across purpose or direction;
* the transcript salt binds the root key to the signed hello
  exchange (downgrade/relay resistance);
* the ratchet is one-way: `chain'` reveals nothing about `chain`,
  so later process compromise cannot decrypt earlier frames
  (message-granularity forward secrecy).

---

## 6. Key confirmation

After `derive()`, each side holds `root`. Before any traffic:

1. client sends `{t:"confirm", role:"client", mac: b64(mac("client"))}`
   encrypted with its c2s chain;
2. server verifies with `hmac.compare_digest`, then answers with
   `mac("server")`;
3. client verifies the server MAC.

A mismatch means at least one peer holds a different key (active
attack or bug) — the link is aborted. Confirmation MACs ride inside
the already-authenticated transport, so they are themselves sealed.

---

## 7. Transport

### 7.1 Frame layout

Wire frame = `>I length ‖ GW1 sealed record`, where the sealed record is:

```
offset  size  field
0       4     counter n (big-endian; equals the ratchet step)
4       12    nonce = direction byte (b"c" or b"s") ‖ n as 11-byte BE
16      …     ciphertext
-16     16    GCM tag
```

Encryption of each frame:

* key: the frame's ratchet `msg_key` (fresh, then erased);
* nonce: as above — the direction byte separates the two chains even
  if a key were ever reused, and the 11-byte counter makes nonce
  reuse impossible within a chain;
* AAD: the literal `b"GW1"` — authenticates protocol context.

### 7.2 Receive discipline

* frames < 32 bytes (counter+nonce+tag floor) are rejected as
  truncated;
* the counter in the frame MUST equal the receiver's next expected
  ratchet step — exact, gapless, no reordering (`ratchet sequence
  desync` otherwise). This is deliberately strict for a two-party
  tactical link: reordering/replay is treated as an attack;
* GCM tag verification via `decrypt_and_verify`; any exception maps
  to `SecurityError("AES-GCM authentication failed")`;
* transport JSON objects: `msg` (chat, carries `ttl` and `ts`),
  `ack`/`del` (delivery state), `ping`/`pong` (liveness).

---

## 8. Security properties and residual risks

**Achieved:** mutual entity authentication · explicit key
confirmation · confidentiality + integrity per frame · forward
secrecy per message · replay and reordering rejection · transcript
binding (anti-relay) · fail-closed error model.

**Residual, by design:**

* **Endpoint compromise** — the protocol cannot protect against a
  seized, unlocked device; keys live in process memory.
* **Metadata** — timing, endpoints and traffic volume are visible to
  a network observer; the probe mechanism answers reconnaissance
  without revealing protocol state, but presence is detectable.
* **Post-quantum** — X25519/Ed25519 are not quantum-resistant.
  Harvest-now-decrypt-later against *recorded* sessions is a risk if
  the adversary expects a cryptographically relevant quantum
  computer; the per-session ephemeral design limits exposure to
  recorded transcripts of that session only.
* **Pure-Python timing** — the curve core is constant-*sequence* but
  CPython bigint arithmetic is not constant-*time*; accepted for a
  local-telemetry threat model where remote sub-microsecond timing
  is not assumed.

---

## 9. Failure catalogue

Every cryptographic failure raises `gw.crypto.SecurityError`. The
receiver-visible messages (also the expected verdicts of the book's
negative-vector corpus) are:

| Message | Cause |
|---|---|
| `malformed identity key` | identity public key ≠ 32 bytes |
| `identity signature check failed` | Ed25519 verification failed |
| `handshake role mismatch` | peer claimed our role / invalid role |
| `protocol version mismatch` | `v` field ≠ `GW1` |
| `derive() before peer hello` | API misuse / truncated handshake |
| `malformed ephemeral key` | ephemeral public ≠ 32 bytes |
| `key confirmation MAC mismatch` | root keys disagree between peers |
| `truncated frame` | sealed record < 32 bytes |
| `ratchet sequence desync` | counter ≠ expected step |
| `AES-GCM authentication failed` | tag, ciphertext or nonce tampered |
| `oversized frame` | length prefix > `MAX_FRAME` |

---

## 10. Implementation notes (Android build)

* **PyCryptodome** supplies AES-256-GCM and HKDF. It cross-compiles
  cleanly in the python-for-android SDL2 bundle; the `cryptography`
  package was rejected after its Rust `.so` failed `dlopen` on device.
* **`gw/_curve25519.py`** (195 lines, interpreter-only) implements
  X25519 (Montgomery ladder, clamped scalars) and Ed25519 (extended
  coordinates, SHA-512 expansion). It cannot fail with a native
  loader error by construction.
* **Entropy:** every secret (identity seeds, ephemeral secrets) comes
  from `os.urandom`. There is no user-supplied key material and no
  persisted key store (unchanged since v1.0.0) — identities are regenerated per
  install, matching the session-oriented threat model.
* Bundle manifest hardening: `android:allowBackup="false"` (no key
  exfiltration via ADB backup), `targetSdkVersion 34`.

---

## 11. Constants reference

| Constant | Value |
|---|---|
| Protocol literal | `GW1` |
| Key length | 32 bytes everywhere |
| GCM nonce | 12 bytes (1 dir byte + 11-byte BE counter) |
| GCM tag | 16 bytes |
| `MAX_FRAME` | 1 000 000 bytes |
| Probe magic | `GW1PROBE` (8 bytes) |
| Handshake recv timeout | 15 s |
| Probe timeouts | connect 0.35 s / read 1.0 s |
| HKDF info strings | `GW1\|root`, `GW1\|chain\|c2s`, `GW1\|chain\|s2c`, `GW1\|message-key`, `GW1\|ratchet-step`, `GW1\|confirm` |
| AAD | `b"GW1"` |
| Transcript seed | `GW1\|session\|v1` |

---

## 12. Validation and maintenance

* **`docs/validate_gw1.py`** — Tier-1 + Tier-3 suite: pinned RFC 7748 /
  RFC 8032 / RFC 5869 / NIST GCM vectors plus 25 full handshakes with
  tamper injection. Exit code 0 is the release gate; run it on every
  host/CI before packaging.
* **Book Appendix A corpus** — ~4 200 deterministic vectors (HKDF,
  X25519, Ed25519, AES-GCM, full-session transcripts, ratchet-chain
  interiors, negative must-reject frames) generated from labelled
  SHA-256 expansions. Any reimplementation must reproduce them
  bit-for-bit.
* **Change control:** any edit to `gw/crypto.py`, `gw/_curve25519.py`
  or the key-schedule literals requires (1) validator pass, (2)
  corpus regeneration of the book, (3) a versioned protocol bump —
  GW1 verifies `v` strictly, so incompatible peers refuse each other
  instead of silently downgrading.
* **Key-rotation guidance:** identities are per-install; rotate by
  reinstalling or regenerating `Identity`. There is no re-keying
  inside a session — the per-message ratchet subsumes it.

---

## 13. File map

| File | Role |
|---|---|
| `gw/crypto.py` | Identity, handshake, key schedule, ratchet, AEAD composition (218 lines) |
| `gw/_curve25519.py` | Pure-Python X25519 + Ed25519 (195 lines) |
| `gw/net.py` | Framed I/O, `SecureLink`, `NodeServer`, discovery probe (413 lines) |
| `docs/validate_gw1.py` | Release-gate validation suite |
| `docs/GHOSTWIRE_Cryptography_Book.pdf` | Full book: theory, annotated source, vector corpus, field manual |

---

## 14. Using the program (operator summary)

Full walkthrough in book Chapter 26; condensed here.

* **Requirements:** Android 10+ (minSdk 24 / targetSdk 34), APK
  installs without store warnings; only INTERNET, network-state and
  BLUETOOTH_* permissions. Desktop testing runs the same modules
  under CPython + Kivy.
* **Home → NODE CONTROL:** set BIND ADDR (default `0.0.0.0`) and
  PORT (default `9999`), then DEPLOY NODE. The node listens (backlog
  8) and triages incoming connections: `GW1PROBE` traffic gets the
  reconnaissance path, everything else is parked at the request
  gate — no handshake may begin until the operator decides (below).
* **Request gate (strictly two-party):** v1.1.0 hosts exactly ONE
  live link. Every inbound dial raises `<ip:port> REQUESTS A CHAT`
  with ACKNOWLEDGE / REJECT buttons. Unanswered requests expire
  after 60 s; REJECT closes before any crypto is exchanged. A new
  client can therefore never silently displace an active peer —
  answering ACKNOWLEDGE while a peer is connected drops that peer
  first, explicitly. The Bluetooth node applies the identical gate.
* **ESTABLISH UPLINK:** enter TARGET HOST/IP + PORT, pick transport
  (WIFI/LAN, BLUETOOTH RFCOMM on channel 7, or WAN RELAY pointing at
  a `relay_server.py` host), press INITIATE HANDSHAKE. The console
  prints every phase and the exact `SecurityError` on failure;
  success ends in SECURE LINK ESTABLISHED plus a session id. Relay
  seats: the first dialer becomes the GW1 server, the second the
  client — keys are derived end-to-end through the pipe.
* **SCAN:** capped sweep (≤ 1024 hosts, 0.35 s connect / 1.0 s
  probe) that lists ONLY hosts answering with a valid GW1 PONG —
  open-port hits are ignored so stealth keeps its promise. Results
  are hints; stealth nodes stay invisible.
* **CHAT:** header shows endpoint + peer fingerprint; shield-check
  opens the fingerprint-verification dialog (the MITM tripwire),
  delete-forever triggers bilateral burn, power disconnects. The
  fire button cycles message-expiry presets: **60 s default, then
  1.5 m / 2 m / 3 m / 5 m**. Messages are never persisted.
* **SECURITY screen:** read-only view of the cipher suite, the
  STANDARDS panel (RFC 7748/8032/5869/2104, NIST SP 800-38D, FIPS
  180-4), the live session id and the peer fingerprint.

Standard session: deploy node → uplink from peer → operator
ACKNOWLEDGEs → compare session ids → verify fingerprints
out-of-band → chat → burn or disconnect.

---

## 15. Strengths and limitations

### Strengths
* Mutual authentication by construction (signed hellos, transcript
  binding) — no passwords, no PKI, no trust-on-first-use.
* Explicit key confirmation before any traffic.
* Forward secrecy per message; compromise mid-session exposes only
  future frames.
* Strict sequencing rejects replay, reordering and injection.
* Fail-closed everywhere; no warning-only paths.
* Fully auditable: ~830 lines of protocol code, public-key core
  printed in the book (195 lines of pure Python).
* Stealth discipline + bilateral burn + no at-rest storage.

### Limitations (by design)
* Endpoint trust: a seized unlocked device ends every guarantee.
* Two-party sessions only; no group ratchet. A node hosts several
  parallel two-party channels, but a true multi-party conversation
  does not exist.
* Synchronous: no store-and-forward, no offline delivery, no
  history — both parties online simultaneously.
* Strict counters assume TCP/RFCOMM ordering; no multipath, no
  lossy-pipe tolerance.
* Identities are per-install and not exportable; reinstall means a
  new fingerprint to re-verify.
* Pure-Python curves are constant-sequence, not constant-time.

### Limitations (of the medium)
* Metadata (who/when/how-much) is visible to observers.
* An open GW1 port is port-scan-detectable even in stealth mode.
* No post-quantum component (harvest-now-decrypt-later on recorded
  sessions is a residual risk).
* Messenger-scale throughput by intent, not bulk transfer.

---

## 16. WAN operation

Book Chapter 28 in full; summary:

* **The protocol is WAN-transparent.** GW1 needs only an ordered,
  reliable byte pipe — TCP provides it across any number of hops,
  and the strict counters are satisfied by TCP ordering. The
  handshake is four short messages, so WAN latency adds ~one second
  of setup, once. Mutual authentication already built into GW1 is
  what TLS would otherwise provide; no extra layer is needed.
* **Reachability is the operator's job.** Options: direct public
  address; NAT port forwarding to the device; a reverse tunnel to
  a rendezvous host both operators control; or the shipped
  `relay_server.py` on any mutually reachable host — both devices
  dial it with WAN RELAY selected. The relay is a pipe, not a
  trust dependency: it pairs dialers, assigns server/client seats,
  and shuttles ciphertext it can neither read nor forge. Recon
  probes addressed to it are closed silently.
* **Deliberately not provided:** NAT hole-punching and rendezvous
  infrastructure — introducing third parties would break the
  protocol's central promise. The relay keeps that promise because
  it is blind by construction and operator-controlled.
* **Discovery does not work across WAN:** sweeps are segment-local;
  addresses must be exchanged out-of-band.
* **WAN-specific risks:** amplified metadata exposure to global
  passive observers (mitigate: short contact windows, steady
  scheduling); scanners still see the open port; active MITM and
  passive content recovery remain defeated by the handshake and the
  ratchet.
* **Mandatory at distance:** fingerprints exchanged over an
  independent channel and verified at first session; session id read
  back verbally once; agreed burn discipline; node stowed outside
  contact windows.

Verdict: LAN is GW1's native terrain; WAN is fully supported by the
cryptography and transport, limited only by ordinary IP reachability
and the metadata cost of the public internet.

*Developed by @Ariko & Arena.*

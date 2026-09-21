"""Part I — Foundations (Chapters 1-4)."""


def build(F):
    F.part("PART I — FOUNDATIONS")

    # ---------------------------------------------------------- ch 1
    F.chapter("Chapter 1 — Design Goals and Threat Model")
    F.p("GHOSTWIRE assumes the network is hostile. Every byte that "
        "traverses Wi-Fi or Bluetooth is assumed to be recorded, "
        "replayed, injected into and selectively deleted by an active "
        "adversary with full control of the medium. The design goals "
        "that follow from that assumption are, in priority order: "
        "mutual authentication of the two endpoints; confidentiality "
        "and integrity of every frame; per-message forward secrecy; "
        "transience of content; and fail-closed behaviour on any "
        "anomaly.")
    F.h2("1.1  What GW1 provides")
    F.bullets([
        "Mutual entity authentication via long-term Ed25519 identity "
        "keys whose SHA-256 fingerprints are compared out-of-band.",
        "Authenticated key agreement via ephemeral X25519 ECDH bound "
        "to signed transcripts (SIGMA family), defeating relay and "
        "rebinding attacks.",
        "Confidentiality and integrity with AES-256-GCM under a fresh "
        "key per message, derived from a symmetric ratchet.",
        "Per-message forward secrecy: ratchet chain state is deleted "
        "after each step, so compromising a process at time t does not "
        "decrypt frames from before t.",
        "Transience: time-to-live enforced on both peers; bilateral "
        "burn-after-read deletion; nothing persisted to disk.",
    ])
    F.h2("1.2  What GW1 does not provide")
    F.p("Honesty about residual risk is a security feature. GW1 does "
        "not provide anonymity or metadata hiding (an observer sees "
        "who talks to whom, when, and at what volume); post-quantum "
        "resistance (a quantum adversary recording today's traffic "
        "could break X25519 retrospectively); deniability of a "
        "different flavour than signatures imply; or protection "
        "against a compromised endpoint — a device under your "
        "adversary's control reads plaintext before encryption and "
        "after decryption. These limits are displayed inside the "
        "application itself on its Security screen.")
    F.h2("1.3  Attacker classes")
    F.table([
        ["Class", "Capability", "GW1 outcome"],
        ["Passive eavesdropper", "records all frames", "no plaintext, "
         "no session keys; transcript hash public only as session id"],
        ["Active MITM", "inject/modify/replay", "handshake signature + "
         "confirmation MAC fail closed; ratchet desync kills link"],
        ["Relay / rebinder", "forwards hellos between pairs", "server "
         "signature binds client hello; transcript mismatch fails"],
        ["Later compromise", "full memory at time t", "frames before t "
         "protected by ratchet erasure; identities are signing-only"],
        ["Quantum (store-now)", "future QC", "broken — see §1.2"],
        ["Compromised endpoint", "rooted device", "broken — see §1.2"],
    ], widths=[95, 120, 235])

    # ---------------------------------------------------------- ch 2
    F.chapter("Chapter 2 — Cryptographic Preliminaries")
    F.p("A cipher is a family of functions indexed by a key; security "
        "means that a bounded adversary cannot distinguish its use "
        "from an ideal object (a random permutation, a random "
        "function, a private channel). This chapter fixes the "
        "vocabulary used for the rest of the book.")
    F.h2("2.1  Kerckhoffs' principle")
    F.p("The algorithm is public; only the key is secret. Everything "
        "in this volume — including this book — is part of the public "
        "description. Consequently no security argument in GHOSTWIRE "
        "may rely on an opponent not having read this document.")
    F.h2("2.2  Keys, entropy and uniqueness")
    F.p("All secret material is drawn from the operating system CSPRNG "
        "(`os.urandom`, backed by the kernel ChaCha20 pool): 32-byte "
        "identity secrets, 32-byte ephemeral X25519 secrets, and every "
        "ratchet seed. Two properties matter more than raw randomness: "
        "uniqueness (no nonce, no ephemeral key, no ratchet state is "
        "ever repeated) and secrecy-after-use erasure (ratchet chain "
        "values are overwritten by the next step). AES-GCM's entire "
        "security collapses under nonce reuse with the same key; the "
        "ratchet design makes reuse structurally impossible because "
        "the counter is embedded in the nonce and monotonic per "
        "direction.")
    F.h2("2.3  Security notions used")
    F.bullets([
        "PRF/PRP indistinguishability for HMAC and AES.",
        "EUF-CMA (existential unforgeability under chosen message "
        "attack) for Ed25519 signatures.",
        "AEAD security (IND-CPA + INT-CTXT) for AES-256-GCM.",
        "Computational Diffie–Hellman on Curve25519 for ECDH secrecy.",
        "Random-oracle modelling of SHA-256 inside HKDF proofs.",
    ])
    F.h2("2.4  Fail-closed philosophy")
    F.p("Every verification in GW1 raises SecurityError and tears the "
        "link down: bad signature, wrong protocol tag, role mismatch, "
        "malformed key length, MAC mismatch, GCM tag failure, ratchet "
        "counter desynchronisation. There is no warning mode, no "
        "plaintext fallback, no ‘proceed anyway’. A link that died is "
        "information; a link that continued with weakened guarantees "
        "would be the vulnerability.")

    # ---------------------------------------------------------- ch 3
    F.chapter("Chapter 3 — Data Representation and Framing")
    F.h2("3.1  Byte-level conventions")
    F.bullets([
        "All multi-byte integers on the wire are big-endian "
        "(`struct.pack('&gt;I', n)`); curve scalars/points are "
        "little-endian per RFC 7748/8032.",
        "Base64 (standard alphabet) encodes binary fields inside the "
        "JSON hello messages (`e`, `i`, `s`).",
        "Human-readable payloads are UTF-8; protocol control strings "
        "are ASCII.",
        "MAX_FRAME = 1,000,000 bytes bounds allocation attacks.",
    ])
    F.h2("3.2  Frame layout of the transport cipher")
    F.code("""
    sealed frame (bytes):
      +0..3    u32  ratchet counter n            (big-endian)
      +4..15   12B  nonce  = dir_byte || n (11B big-endian)
      +16..    ct   AES-256-GCM ciphertext
      last 16B tag  GCM authentication tag
    """)
    F.p("The counter is repeated in the clear so a receiver can detect "
        "desynchronisation before spending a decryption; the nonce "
        "embeds a direction byte (first byte of the chain label) so "
        "the two directions can never mirror each other's nonces even "
        "under identical counters.")
    F.h2("3.3  Length-prefixed transport framing")
    F.p("TCP and RFCOMM carry identical 4-byte big-endian length-"
        "prefixed frames. A probe frame (GW1PROBE) outside the secure "
        "session answers with the node fingerprint (GW1PONG) unless "
        "stealth mode silences it — reconnaissance data intentionally "
        "contains no secrets beyond the public fingerprint.")

    # ---------------------------------------------------------- ch 4
    F.chapter("Chapter 4 — Randomness and Key Generation")
    F.h2("4.1  The only entropy source")
    F.code("""
    import os
    identity_secret = os.urandom(32)      # Ed25519 seed
    eph_secret      = os.urandom(32)      # X25519 scalar, per session
    """)
    F.p("On Linux/Android `os.urandom` reads the kernel pool "
        "(getrandom(2)), which seeds ChaCha20 from interrupt timing, "
        "and blocks until initialised on modern kernels. GHOSTWIRE "
        "never seeds, never mixes, never persists. Adding custom "
        "‘entropy sources’ is a classic way to weaken a CSPRNG and is "
        "forbidden by the maintenance guide.")
    F.h2("4.2  Key clamping and validation")
    F.p("X25519 secrets are clamped per RFC 7748 (low three bits "
        "cleared, top bit set, second-top bit set) inside the ladder; "
        "Ed25519 seeds are expanded with SHA-512 and clamped per RFC "
        "8032. Peer points are validated: 32-byte length checks, "
        "on-curve recovery failure → SecurityError; low-order point "
        "checks are inherent in the RFC 8032 verification formula "
        "used (sB = R + hA).")
    F.h2("4.3  Key hierarchy")
    F.table([
        ["Key", "Derivation", "Lifetime"],
        ["identity secret", "urandom(32)", "process"],
        ["ephemeral scalar", "urandom(32)", "session"],
        ["shared (ECDH)", "X25519(eph, peer_eph)", "session"],
        ["root", "HKDF(shared, 'GW1|root', salt=session_id)", "session"],
        ["chain c/s", "HKDF(root, 'GW1|chain|' + dir)", "erased per msg"],
        ["msg key", "HKDF(chain, 'GW1|message-key')", "one frame"],
        ["confirm key", "HKDF(root, 'GW1|confirm')", "handshake"],
    ], widths=[105, 205, 140])

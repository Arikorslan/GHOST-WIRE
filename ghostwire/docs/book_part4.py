"""Part IV — Public-Key Primitives (Chapters 11-14)."""


def build(F):
    F.part("PART IV — PUBLIC-KEY PRIMITIVES")

    # ---------------------------------------------------------- ch 11
    F.chapter("Chapter 11 — Elliptic Curve Primer")
    F.p("An elliptic curve over a prime field is the set of solutions "
        "to a cubic equation together with a group law: the chord-and-"
        "tangent rule. GHOSTWIRE uses the curve birationally "
        "equivalent to Edwards25519 via its Montgomery form "
        "Curve25519: y² + x² = 1 − 121665/121666·x²y² (Edwards, d = "
        "−121665·121666⁻¹ mod p) with p = 2²⁵⁵ − 19. The group order "
        "is 8·ℓ with ℓ = 2²⁵² + 27742317777372353535851937790883648493 "
        "prime.")
    F.h2("11.1  Why 25519")
    F.bullets([
        "A 2⁵-scale prime shaped for fast reduction (2²⁵⁵−19).",
        "A complete(ish) addition law in Edwards coordinates: unified "
        "formulas resist timing channels.",
        "128-bit security with 32-byte keys — half the size of P-256 "
        "encodings for signatures.",
        "RFCs 7748/8032 give byte-exact, test-vectored specifications.",
    ])
    F.h2("11.2  The two problems assumed hard")
    F.p("Discrete logarithm in the prime-order subgroup (best generic "
        "attack Pollard-rho ≈ 2¹²⁶ group ops) underlies both X25519 "
        "secrecy (Computational DH) and Ed25519 unforgeability.")

    # ---------------------------------------------------------- ch 12
    F.chapter("Chapter 12 — X25519 Diffie–Hellman")
    F.h2("12.1  The Montgomery ladder")
    F.p("Scalar multiplication on the u-line uses only the u-"
        "coordinate: differential additions and doublings on the pair "
        "(x₂,z₂),(x₃,z₃). The ladder processes bits top-down with a "
        "constant-time conditional swap (cswap), so the sequence of "
        "field operations is identical for every scalar — no branch "
        "depends on the key.")
    F.code("""
    # gw/_curve25519.py — ladder core (see Chapter 19 for the
    # annotated full listing)
    for t in range(254, -1, -1):
        bit = (k >> t) & 1
        x2, x3 = cswap(swap ^ bit, x2, x3)
        ...
        x2 = AA * BB
        z2 = E * (AA + 121665 * E)
    """)
    F.h2("12.2  Clamping")
    F.p("The RFC 7748 clamp (k &amp;= ~7; k |= 2²⁵⁴) clears the cofactor "
        "bits and fixes the top bit, making the operation cofactor-"
        "safe and ladder-stable. GW1 clamps on every use; peer u-"
        "coordinates are accepted as arbitrary field elements — the "
        "ladder is total, and small-subgroup inputs yield the all-zero "
        "shared secret which HKDF then treats as fixed public "
        "material; authentication (signatures + MACs) is what kills "
        "such peers, not point validation.")
    F.h2("12.3  Correctness vectors")
    F.p("Appendix A reproduces RFC 7748 §6.1 and adds 300 generated "
        "ladder vectors; the validator (Appendix B) re-derives them "
        "on device at maintenance time.")

    # ---------------------------------------------------------- ch 13
    F.chapter("Chapter 13 — Ed25519 Signatures")
    F.h2("13.1  Signing")
    F.p("The seed expands via SHA-512 into a clamped scalar a and a "
        "prefix; the nonce r = H(prefix || m) mod ℓ makes signing "
        "deterministic (no RNG failure mode); R = rB; h = H(R || A || "
        "m) mod ℓ; s = r + h·a. The signature is R || s (64 bytes).")
    F.h2("13.2  Verification")
    F.p("The check sB = R + hA is performed in extended twisted-"
        "Edwards coordinates with a double-and-add scalar multiplier; "
        "point decompression recovers x from y with the sign bit, "
        "rejecting non-residues. This is exactly the RFC 8032 "
        "verification equation — it subsumes cofactor and small-order "
        "checks for GW1's purposes.")
    F.h2("13.3  Determinism as a feature")
    F.p("Deterministic nonces remove the single largest real-world "
        "EdDSA/ECDSA failure class (biased or repeated nonces leaking "
        "keys). Two signatures of the same message are identical — "
        "acceptable here because messages already carry fresh "
        "transcripts.")
    F.h2("13.4  Usage in GW1")
    F.p("Identities sign exactly one payload shape: "
        "`GW1|role|eph_b64|id_b64|bind`. The responder's `bind` field "
        "contains the initiator's hello signature, making the server "
        "signature untransferable between candidate sessions and "
        "yielding the SIGMA property that the key is bound to both "
        "identities and both ephemerals.")

    # ---------------------------------------------------------- ch 14
    F.chapter("Chapter 14 — Pure-Python Cryptography on Android: "
              "A Case Study")
    F.h2("14.1  The incident")
    F.p("The first Android builds used the `cryptography` package. "
        "Its Rust extension (`_rust.abi3.so`) cross-compiled cleanly "
        "and was a valid ARM64 ELF, yet at import time Android's "
        "linker failed: `cannot locate symbol \"PyExc_TypeError\"`. "
        "Stable-ABI (abi3) modules resolve CPython symbols from the "
        "embedding process at load; the SDL2 bootstrap embeds Python "
        "in a way that leaves those symbols unexported to dlopen'd "
        "abi3 libraries. Result: a perfectly built binary that can "
        "never load.")
    F.h2("14.2  The fix")
    F.p("Two-layer substitution: (1) AES/HKDF moved to PyCryptodome, "
        "whose C modules are ordinary (non-abi3) extensions linked "
        "during the p4a build and loaded without symbol interposition "
        "problems; (2) X25519/Ed25519 moved to the pure-Python "
        "`gw/_curve25519.py` — interpreter bytecode cannot fail to "
        "dlopen. Performance: a full handshake (two ladders, three "
        "Ed operations) completes in well under a second on modern "
        "ARM cores and ~60 ms on the development host; per-session "
        "cost, irrelevant for telemetry cadence.")
    F.h2("14.3  Lessons codified as maintenance rules")
    F.bullets([
        "Never introduce an abi3/Rust extension into the Android "
        "bundle without an on-device import test.",
        "Prefer primitives whose failure mode is a Python exception "
        "over ones whose failure mode is a linker abort.",
        "Keep a generated vector corpus (Appendix A) so a pure-Python "
        "core is re-proven correct at every release.",
    ])

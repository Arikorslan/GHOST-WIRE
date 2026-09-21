"""Part II — Hashes and Message Authentication (Chapters 5-7)."""


def build(F):
    F.part("PART II — HASHES AND MESSAGE AUTHENTICATION")

    # ---------------------------------------------------------- ch 5
    F.chapter("Chapter 5 — SHA-256")
    F.h2("5.1  Construction")
    F.p("SHA-256 (FIPS 180-4) maps arbitrary-length input to 32 bytes "
        "via Merkle–Damgård iteration over a 512-bit block function: "
        "64 rounds mixing eight 32-bit words with the operations "
        "Ch(e,f,g)=(e∧f)⊕(¬e∧g), Maj(a,b,c), rotations σ0/σ1, and "
        "addition modulo 2³² against 64 round constants derived from "
        "cube roots of primes. Message schedule expands 16 words to 64 "
        "with σ0/σ1 feedback.")
    F.h2("5.2  Security properties relied upon")
    F.bullets([
        "Collision resistance (~2¹²⁸ work) — fingerprints, transcript "
        "hashes.",
        "Preimage resistance (~2²⁵⁶) — session ids reveal nothing "
        "about the transcript.",
        "PRF-like behaviour when keyed via HMAC (Chapter 6).",
    ])
    F.h2("5.3  Uses inside GW1")
    F.bullets([
        "Identity fingerprints: uppercase hex of SHA-256(public key), "
        "grouped 4-4-4-4, for out-of-band comparison.",
        "Transcript hash: incremental `hashlib.sha256` absorbing both "
        "signed hello payloads; the digest becomes the session id and "
        "the HKDF salt.",
        "HKDF and HMAC inner hash (Chapters 6–7).",
    ])
    F.h2("5.4  Implementation notes")
    F.p("The host CPU path uses the platform's optimised hashlib "
        "(SHA-NI on x86, ARMv8 crypto extensions on Android). No pure-"
        "Python SHA-256 is shipped; there is no reason to re-implement "
        "a primitive the silicon already accelerates. Maintenance "
        "rule: never replace hashlib with a third-party hash "
        "implementation.")

    # ---------------------------------------------------------- ch 6
    F.chapter("Chapter 6 — HMAC-SHA256")
    F.h2("6.1  Definition")
    F.p("HMAC(K, m) = H((K'⊕opad) || H((K'⊕ipad) || m)) with K' the "
        "key padded to the block size (or hashed if longer). It turns "
        "SHA-256 into a keyed PRF with a security proof reducible to "
        "the compression function's PRF-ness.")
    F.h2("6.2  Role in GW1: key confirmation")
    F.p("After deriving the root key, each side computes "
        "`confirm_mac(role) = HMAC(HKDF(root, 'GW1|confirm'), role)` "
        "and exchanges them before any traffic. This converts the "
        "implicit key authentication of ECDH into explicit entity-"
        "binding: an active attacker who cannot compute the MAC cannot "
        "finish the handshake, and a reflection is impossible because "
        "the role string differs per direction. Comparison uses "
        "`hmac.compare_digest` for constant time.")
    F.h2("6.3  Constant-time discipline")
    F.p("All equality tests over authenticators (confirmation MACs, "
        "and by extension GCM tags inside the AEAD library) go "
        "through constant-time comparison. The maintenance guide "
        "forbids `==` on any value whose equality leaks key material "
        "timing.")

    # ---------------------------------------------------------- ch 7
    F.chapter("Chapter 7 — HKDF and Domain Separation")
    F.h2("7.1  RFC 5869 structure")
    F.p("HKDF = Extract(salt, IKM) → PRK, then Expand(PRK, info, L). "
        "With SHA-256, Extract is HMAC(salt, IKM) and Expand iterates "
        "HMAC(PRK, prev || info || i). GHOSTWIRE uses the PyCryptodome "
        "implementation: `HKDF(ikm, length, salt, SHA256, 1, "
        "context=info)`.")
    F.h2("7.2  Why the salt is the session id")
    F.p("Salting the root derivation with the full transcript hash "
        "binds the key to the exact pair of hellos that were signed. "
        "Two sessions that ever differed in one byte of hello produce "
        "disjoint key material even under identical ECDH output — a "
        "belt-and-braces binding on top of including the transcript "
        "in the signed payloads.")
    F.h2("7.3  The info strings (domain separation table)")
    F.table([
        ["info string", "output", "purpose"],
        ["GW1|root", "root key", "session root from ECDH"],
        ["GW1|chain|c2s", "client chain", "client→server ratchet seed"],
        ["GW1|chain|s2c", "server chain", "server→client ratchet seed"],
        ["GW1|message-key", "32B", "per-frame AES-256 key"],
        ["GW1|ratchet-step", "32B", "next chain state (erases old)"],
        ["GW1|confirm", "32B", "confirmation MAC key"],
    ], widths=[120, 90, 240])
    F.p("Distinct info strings make every derived key an independent "
        "random oracle output; reusing one string for two purposes is "
        "the single most common HKDF deployment bug and is structurally "
        "impossible here because the table is enforced in code "
        "(Chapter 20).")

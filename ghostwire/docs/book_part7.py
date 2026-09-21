"""Part VII — Maintenance & Operations (Chapters 23-25)."""


def build(F):
    F.part("PART VII — MAINTENANCE &amp; OPERATIONS")

    F.chapter("Chapter 23 — Maintenance and Upgrade Guide")
    F.h2("23.1  Dependency matrix")
    F.table([
        ["Component", "Pinned", "Role", "Upgrade trigger"],
        ["python3 (p4a)", "3.14.x", "runtime", "security release"],
        ["kivy", "2.3.1", "UI/window", "API need / CVE"],
        ["kivymd", "1.2.0", "widgets", "kivy compat"],
        ["pycryptodome", "3.23.0", "AES/HKDF", "CVE in AES/GCM/KDF"],
        ["NDK", "r28c", "cross-compile", "p4a support"],
        ["android.api", "34", "target SDK", "Play policy / yearly"],
    ], widths=[92, 66, 92, 200])
    F.h2("23.2  Standard upgrade procedure")
    F.bullets([
        "1. Bump the pin in buildozer.spec on a branch; read the "
        "upstream changelog for ABI breaks.",
        "2. `buildozer android clean` only when the recipe chain "
        "changed; otherwise incremental dist rebuild.",
        "3. Run the host validation suite (Appendix B) — it must pass "
        "100% before any device test.",
        "4. Build, then verify the bundle: aarch64 .so set, no "
        "forbidden artifacts (§22.3), manifest invariants.",
        "5. On-device: cold boot (presplash→splash→home), deploy "
        "node, sweep, connect, chat, burn, keyboard open/close.",
        "6. Tag release; regenerate this book (its vectors are "
        "produced by the same validator).",
    ])
    F.h2("23.3  What must NEVER change without a protocol review")
    F.bullets([
        "Any info string, AAD, or payload grammar (domain separation).",
        "Counter/nonce layout in CipherState (framing compat).",
        "The fail-closed desync behaviour (§10.2).",
        "Introduction of any native extension (Chapter 14).",
    ])

    F.chapter("Chapter 24 — Validation and Testing")
    F.h2("24.1  The three-tier suite")
    F.bullets([
        "Tier 1 — published vectors: RFC 7748/8032, RFC 5869, NIST "
        "GCM; run at import of the validator.",
        "Tier 2 — generated corpus (Appendix A): 2,000+ derived "
        "vectors tying this exact code to reproducible outputs.",
        "Tier 3 — property tests: handshake symmetry, tamper "
        "detection, replay/desync death, TTL burn bilateral.",
    ])
    F.h2("24.2  On-device acceptance checklist")
    F.bullets([
        "logcat shows 'SECURE LINK ESTABLISHED' on both ends with "
        "matching peer fingerprints.",
        "A third laptop running the probe sees only GW1PONG + "
        "fingerprint (or silence in stealth).",
        "Killing one peer mid-chat produces LinkClosed, never "
        "plaintext or hang.",
        "Burn timer deletes on both devices; process memory scan "
        "after burn finds no message string.",
    ])

    F.chapter("Chapter 25 — Incident Response and Operational "
              "Discipline")
    F.h2("25.1  Fingerprint verification SOP")
    F.p("Before classified traffic, operators read the 16-hex "
        "fingerprint aloud or via a second channel and compare both "
        "directions. A mismatch means an active MITM right now; "
        "abort, do not ‘retry’.")
    F.h2("25.2  Compromised-device playbook")
    F.bullets([
        "Assume all identities on that device are burned; generate a "
        "new identity (restart) and re-verify fingerprints.",
        "Old sessions retain per-message forward secrecy, but "
        "transience is the real control: everything was burned "
        "already.",
        "Rotate nothing else — keys are ephemeral by design.",
    ])
    F.h2("25.3  Honest threat notes (operator-facing)")
    F.p("No anonymity; no post-quantum KEM; a rooted endpoint reads "
        "plaintext. The app states this on its own Security screen; "
        "this chapter is the long form of that banner. GHOSTWIRE "
        "protects the channel, not the endpoints.")
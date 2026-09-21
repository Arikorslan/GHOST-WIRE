"""Part V — The GW1 Protocol (Chapters 15-18)."""


def build(F):
    F.part("PART V — THE GW1 PROTOCOL")

    # ---------------------------------------------------------- ch 15
    F.chapter("Chapter 15 — Protocol Overview and Session Lifecycle")
    F.h2("15.1  Roles and states")
    F.p("Every node owns one long-term identity. A session has a "
        "client and a server; either may initiate the TCP connection "
        "(roles refer to the handshake, not to who dialed). The "
        "lifecycle is: probe (optional) → hellos → derive → confirm → "
        "traffic → burn/close.")
    F.code("""
    CLIENT                          SERVER
      |-- hello(role=client) -------->|   signed(e_c, id_c)
      |<-- hello(role=server,         |   signed(e_s, id_s,
      |        bind=sig_c)            |          bind=sig_c)
      |    derive() on both sides     |
      |-- confirm_mac('client') ----->|
      |<-- confirm_mac('server') -----|
      |======= ratcheted frames =====>|
    """)
    F.h2("15.2  Session identity")
    F.p("session_id = SHA-256 over the running transcript initialised "
        "with 'GW1|session|v1' and updated with both hello payloads. "
        "It is displayed to operators and used as the HKDF salt, so a "
        "session is cryptographically bound to what both screens show.")

    # ---------------------------------------------------------- ch 16
    F.chapter("Chapter 16 — The Handshake, Annotated")
    F.h2("16.1  Hello payload")
    F.code("""
    payload = f"{PROTOCOL}|{role}|{e_b64}|{i_b64}|{bind}"
    sig     = Ed25519.sign(identity_secret, payload)
    msg     = {"t":"hello","role":role,"e":e_b64,
               "i":i_b64,"s":b64(sig),"v":"GW1"}
    """)
    F.p("Signing the base64 forms (not the raw bytes) makes the "
        "signed string exactly the transmitted string — no canonical-"
        "isation gap for an attacker to exploit.")
    F.h2("16.2  Verification steps (consume_hello)")
    F.bullets([
        "role ≠ own role and ∈ {client, server} — else SecurityError.",
        "v == 'GW1' — version pin.",
        "Ed25519.verify(peer_id, sig, rebuilt payload) — EUF-CMA.",
        "transcript.update(payload) — order fixed by role.",
    ])
    F.h2("16.3  Derivation and confirmation")
    F.p("derive() performs the ladder, hashes the transcript to the "
        "session id, and HKDFs the root. confirm_mac binds role "
        "strings; check_confirm uses compare_digest. Only after both "
        "confirmations does the link construct its two CipherStates — "
        "traffic before confirmation is impossible by construction.")
    F.h2("16.4  Attack walkthroughs")
    F.table([
        ["Attack", "Defeated by"],
        ["passive read of hellos", "ECDH secrecy + signatures add "
         "nothing usable"],
        ["hello replay", "fresh ephemerals; transcript-bound sigs"],
        ["relay/MITM", "signatures over both ids and ephs; bind"],
        ["unknown-key-share", "id included in signed payload"],
        ["reflection", "role string inside payload and MAC"],
    ], widths=[140, 310])

    # ---------------------------------------------------------- ch 17
    F.chapter("Chapter 17 — Transport Cipher, Framing and Transience")
    F.h2("17.1  Frame production")
    F.p("send: step the tx chain → AES-256-GCM(msg key, nonce, "
        "AAD='GW1') → frame = n || nonce || ct||tag. receive: parse, "
        "check counter, step the rx chain, verify+decrypt. Any "
        "exception → SecurityError → link death.")
    F.h2("17.2  TTL and burn-after-read")
    F.p("Every chat frame carries a TTL chosen from the operator "
        "presets (60 s default, then 90 s / 120 s / 180 s / 300 s — "
        "shown on the fire button as 60s, 1.5m, 2m, 3m, 5m). On "
        "display the receiver sends a `seen` control frame; both "
        "peers count down and delete at zero; a `burned` frame "
        "confirms bilateral deletion. `delete-forever` burns "
        "immediately. Messages are never written to disk — the UI "
        "holds them only in widget state and removes them from "
        "memory on burn.")
    F.h2("17.3  Control frames")
    F.bullets([
        "seen / burned / delete-forever — transience protocol.",
        "All control frames use the same ratchet; they are ciphertext "
        "like everything else.",
    ])

    # ---------------------------------------------------------- ch 18
    F.chapter("Chapter 18 — Discovery, Transports and Failure "
              "Handling")
    F.h2("18.1  Discovery")
    F.p("A sweep connects to candidate addresses and sends GW1PROBE; "
        "a node answers GW1PONG + hex fingerprint unless stealth mode "
        "is armed (then silence). The probe reveals nothing secret; "
        "the fingerprint is public by design (it is what operators "
        "compare out-of-band).")
    F.h2("18.2  Transports")
    F.p("TCP (Wi-Fi/LAN) and Bluetooth RFCOMM share the byte-identical "
        "protocol; SecureLink wraps any bidirectional byte pipe. "
        "Android requires BLUETOOTH_CONNECT/SCAN at runtime; the "
        "manifest requests them (Chapter 22).")
    F.h2("18.3  Failure taxonomy")
    F.table([
        ["Condition", "Class", "Action"],
        ["bad signature", "SecurityError", "close link"],
        ["version/role mismatch", "SecurityError", "close link"],
        ["MAC mismatch", "SecurityError", "close link"],
        ["GCM tag fail", "SecurityError", "close link"],
        ["counter desync", "SecurityError", "close link"],
        ["socket error", "LinkClosed", "UI reports peer lost"],
    ], widths=[140, 110, 200])

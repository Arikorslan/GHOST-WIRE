"""Part VI — Source Code (Chapters 19-22). Loads real files at build."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _src(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return f.read()


def _split_sections(src):
    """Split a module on its '----' banner comments."""
    sections, current = [], []
    title = "module header"
    for line in src.split("\n"):
        if line.startswith("# ---") and not line.startswith("# ----- ---"):
            sections.append((title, "\n".join(current)))
            current = []
            nxt = src.split("\n")[src.split("\n").index(line) + 1] \
                if False else None
            title = "section"
        current.append(line)
    sections.append((title, "\n".join(current)))
    return sections


def build(F):
    F.part("PART VI — SOURCE CODE, ANNOTATED")
    F.p("This part prints the exact source shipped in release 1.1.0. "
        "Code is authoritative; prose elsewhere in the book merely "
        "explains it.")

    # ---------------------------------------------------------- ch 19
    F.chapter("Chapter 19 — gw/_curve25519.py (Pure-Python Core)")
    F.p("The complete interpreter-only implementation of RFC 7748 and "
        "RFC 8032. Field arithmetic is integer arithmetic modulo "
        "2²⁵⁵−19; inversion uses Fermat exponentiation; the ladder "
        "and the Edwards multiplier are written for clarity and "
        "constant *sequence* (not constant *time* — CPython bigint "
        "ops are not timing-constant, an accepted residual noted in "
        "§14.3 for a local-telemetry threat model).")
    src = _src("gw/_curve25519.py")
    chunks = [
        ("19.1  Constants and field helpers", 0, "_X25519_BASE"),
        ("19.2  X25519 (RFC 7748)", "_X25519_BASE", "Ed25519 (RFC 8032)"),
        ("19.3  Ed25519 (RFC 8032)", "Ed25519 (RFC 8032)", None),
    ]
    for title, a, b in chunks:
        ia = src.find(a) if a else 0
        ib = src.find(b) if b else len(src)
        F.code(src[max(0, ia - 200 if a else 0):ib], caption=title)
        F.p("Annotation — see the cross-references in §12–13 for the "
            "mathematical justification of every block above; "
            "Appendix B re-runs the RFC vectors against exactly this "
            "code.")

    # ---------------------------------------------------------- ch 20
    F.chapter("Chapter 20 — gw/crypto.py (Protocol Cryptography)")
    F.p("Composition layer: identity, handshake, ratchet, AEAD. "
        "Nothing here is invented; every call maps to a primitive "
        "specified in Parts II–IV.")
    csrc = _src("gw/crypto.py")
    seg = [
        ("20.1  Header, constants, helpers", 0, "Identity ("),
        ("20.2  Identity", "Identity (", "Handshake"),
        ("20.3  Handshake", "class Handshake", "CipherState"),
        ("20.4  CipherState ratchet", "class CipherState", None),
    ]
    for title, a, b in seg:
        ia = csrc.find(a) if a else 0
        ib = csrc.find(b) if b else len(csrc)
        F.code(csrc[max(0, ia - 100 if a else 0):ib], caption=title)
    F.h2("20.5  Invariants enforced by this file")
    F.bullets([
        "No `==` on authenticators; compare_digest only.",
        "Length checks before every curve operation.",
        "Every failure path raises SecurityError; callers never see "
        "raw crypto exceptions.",
        "info strings and AAD are literals — domain separation "
        "cannot drift.",
    ])

    # ---------------------------------------------------------- ch 21
    F.chapter("Chapter 21 — gw/net.py (Secure Link and Node)")
    F.p("The network layer wraps any byte pipe in the GW1 handshake "
        "and ratchet. Printed below are the security-relevant "
        "sections; UI glue is omitted.")
    nsrc = _src("gw/net.py")
    a = nsrc.find("class SecureLink")
    b = nsrc.find("class NodeServer")
    F.code(nsrc[a:b], caption="21.1  SecureLink")
    F.code(nsrc[b:b + 4200], caption="21.2  NodeServer (accept + probe)")
    F.p("Note the accept loop peeks 8 bytes: GW1PROBE takes the "
        "reconnaissance path (respecting stealth); anything else "
        "becomes a handshake candidate with a 15 s timeout — resource "
        "exhaustion is bounded by daemon-thread-per-connection under "
        "the OS backlog.")

    # ---------------------------------------------------------- ch 22
    F.chapter("Chapter 22 — Packaging and Platform Security")
    F.h2("22.1  buildozer.spec (shipped)")
    F.code(_src("buildozer.spec"), caption="buildozer.spec")
    F.h2("22.2  Security-relevant manifest properties")
    F.bullets([
        "android:windowSoftInputMode=\"adjustPan\" — UX hardening "
        "(keyboard without GL-surface churn).",
        "android:allowBackup=\"false\" — no key/material exfiltration "
        "via ADB backup.",
        "targetSdkVersion 34 / minSdk 24 — modern permission and "
        "runtime model, broad device floor.",
        "Permissions limited to INTERNET, network state and the four "
        "BLUETOOTH_* grants the RFCOMM transport requires.",
    ])
    F.h2("22.3  Bundle composition verified at release")
    F.bullets([
        "libpybundle.so: gzip tar of _python_bundle (stdlib + "
        "site-packages) — audited for arch (aarch64) and content.",
        "PyCryptodome _raw_*.abi3.so built by the NDK, not abi3-"
        "against a foreign interpreter (Chapter 14).",
        "No cryptography/Rust artifacts shipped.",
    ])

"""Front matter."""
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Spacer, Paragraph
from reportlab.platypus.tableofcontents import TableOfContents


def build(F):
    # ------------------------------------------------------------ cover
    F.items.append(Spacer(1, 45 * mm))
    F.pc("◆ ◆ ◆")
    F.sp(10)
    F.items.append(Paragraph("GHOSTWIRE", F.st["cover"]))
    F.sp(8)
    F.items.append(Paragraph("APPLIED CRYPTOGRAPHY &amp; PROTOCOL ENGINEERING",
                             F.st["coversub"]))
    F.sp(14)
    F.pc("The complete cryptographic reference for the GW1 secure "
         "messaging protocol — primitives, proofs-of-correctness, "
         "annotated source code, test-vector corpus and maintenance "
         "operations.")
    F.sp(30)
    F.pc("developed by @Ariko &amp; Arena")
    F.sp(6)
    F.pc("GHOSTWIRE PROJECT  //  EDITION 1.1  //  PROTOCOL GW1  //  APP v1.1.0")

    # ------------------------------------------------------ title page
    from reportlab.platypus import PageBreak
    F.items.append(PageBreak())
    F.h2("GHOSTWIRE — Applied Cryptography &amp; Protocol Engineering")
    F.p("Edition 1.1, protocol GW1, application v1.1.0. This book documents every "
        "cryptographic primitive used by the GHOSTWIRE tactical "
        "messenger, the protocol that composes them, the exact source "
        "code that implements them, and the operational procedures "
        "required to keep a deployment trustworthy.")
    F.p("Copyright © GHOSTWIRE Project. This documentation is provided "
        "with the application for audit and maintenance purposes. The "
        "software and text in this volume may be freely studied and "
        "quoted with attribution: developed by @Ariko &amp; Arena.")
    F.p("DISCLAIMER — No system is unbreakable. This book repeatedly "
        "states the residual risks of the design (endpoint compromise, "
        "metadata exposure, lack of post-quantum primitives). Read "
        "Chapter 25 before operating the tool with real traffic.")

    # ------------------------------------------------------------- TOC
    F.items.append(PageBreak())
    F.items.append(Paragraph("Contents", F.st["h2nc"]))
    toc = TableOfContents()
    toc.levelStyles = [
        Paragraph("x", F.st["h2"]).style if False else F.st["h2"],
        F.st["body"],
    ]
    F.items.append(toc)

    # --------------------------------------------------------- preface
    F.chapter("Preface — How to Read This Book")
    F.p("GHOSTWIRE is a two-party encrypted messenger built for "
        "constrained, adversarial environments: local Wi-Fi segments, "
        "Bluetooth RFCOMM links, and Android devices that cannot be "
        "fully trusted. It was designed around one conviction — a "
        "messaging tool whose cryptography cannot be read, audited and "
        "re-implemented by its operator is not a security tool, it is "
        "a promise. This book is the audit trail.")
    F.p("The volume is organised in eight parts. Part I establishes "
        "the threat model and the conventions everything else rests "
        "on. Parts II–IV treat each primitive family in depth: hashes "
        "and MACs, symmetric ciphers, and public-key primitives "
        "including the pure-Python Curve25519/Ed25519 core that makes "
        "the Android build immune to native-library loading failures. "
        "Part V specifies the GW1 protocol itself — handshake, "
        "ratchet, framing, transience. Part VI prints the actual "
        "source code with engineering annotations. Part VII is the "
        "maintenance and engineering guide. Part VIII is the field "
        "manual: how to operate the program, its strengths and its "
        "honest limitations, and how to run it across wide-area "
        "networks. The appendices contribute a generated, "
        "machine-checkable test-vector corpus, the validator that "
        "consumes it, a glossary and references.")
    F.h2("Conventions")
    F.bullets([
        "Hex strings are lower-case, byte order as transmitted; "
        "multi-byte integers are big-endian unless stated.",
        "<font name='Courier'>code faces</font> denote identifiers, "
        "field names and wire values; <i>italics</i> introduce terms.",
        "KEY_BYTES always means 32; nonces are 12 bytes; GCM tags are "
        "16 bytes; signatures are 64 bytes; public keys are 32 bytes.",
        "Every ‘SECURITY’ note marks a property an attacker must not "
        "be able to violate; every ‘MAINTENANCE’ note feeds Chapter 23.",
    ])
    F.h2("Notation Summary")
    F.table([
        ["Symbol", "Meaning"],
        ["a || b", "concatenation of byte strings"],
        ["H(m)", "SHA-256 digest of m"],
        ["HMAC(k, m)", "RFC 2104 HMAC with SHA-256"],
        ["HKDF(ikm, info, salt)", "RFC 5869, SHA-256, 32-byte output"],
        ["X25519(k, P)", "Montgomery-ladder scalar multiplication"],
        ["Ed25519.sign(sk, m)", "RFC 8032 pure signature"],
        ["AEAD(k, n, aad, pt)", "AES-256-GCM encrypt+authenticate"],
        ["chain ← step(chain)", "HKDF ratchet advance (old state erased)"],
    ], widths=[110, 340])
    F.h2("Standards Inventory")
    F.p("Every primitive in the GW1 suite is a named, public "
        "standard — the same panel is shown in the app's SECURITY "
        "PROTOCOLS screen:")
    F.table([
        ["Standard", "Role in GW1"],
        ["RFC 7748", "X25519 elliptic-curve Diffie-Hellman (Ch. 11–12)"],
        ["RFC 8032", "Ed25519 signatures for mutual authentication"],
        ["RFC 5869", "HKDF-SHA256 key schedule and ratchet"],
        ["RFC 2104", "HMAC-SHA256 key confirmation"],
        ["NIST SP 800-38D", "AES-256-GCM authenticated encryption"],
        ["FIPS 180-4", "SHA-256 digest throughout"],
    ], widths=[110, 340])

"""Appendices A–E.  Appendix A is a *generated* deterministic vector
corpus so the printed book is itself an artifact other implementations
can be tested against.  Regenerate the whole book with
`python3 make_book.py`; inputs are derived from labelled SHA-256
expansions, never from os.urandom."""
import hashlib
import hmac as _hmac
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from gw import _curve25519 as c2            # noqa: E402
from Crypto.Cipher import AES               # noqa: E402
from Crypto.Protocol.KDF import HKDF        # noqa: E402
from Crypto.Hash import SHA256              # noqa: E402


def _d(label, i, n=32):
    """Deterministic pseudo-random bytes for corpus entry i."""
    return hashlib.sha256(b"GW1-CORPUS|" + label + b"|" +
                          str(i).encode()).digest()[:n]


def _hx(b, width=64):
    h = b.hex()
    return "\n".join(h[x:x + width] for x in range(0, len(h), width))


def build(F):
    F.part("APPENDICES")

    # =========================================================== A
    F.chapter("Appendix A — Test-Vector Corpus (generated)")
    F.p("Every vector below is computed at book-build time by the "
        "exact code listed in Chapters 19–20, from deterministic "
        "inputs derived as SHA-256(\"GW1-CORPUS|LABEL|INDEX\"). "
        "A conforming implementation must reproduce every value "
        "bit-for-bit.  The corpus is deliberately large: it exists to "
        "be run, not read — feed it to a harness.")

    # ------------------------------------------------------ A.1
    F.h2("A.1  Published vectors pinned by the build")
    F.table([
        ["source", "test", "expected digest / shared secret"],
        ["RFC 7748 §6.1", "X25519 vector 2",
         "4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742"],
        ["RFC 8032 §7.1", "Ed25519 TEST 1 (empty msg)",
         "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
         "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"],
        ["RFC 5869 A.1", "HKDF-SHA256 PRK",
         "077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5"],
        ["NIST GCM", "AES-256-GCM K=0 V=0 PT=∅",
         "tag=530f8afbc74536b9a963b4f1c4cb738b"],
    ])

    # ------------------------------------------------------ A.2
    F.h2("A.2  HKDF-SHA256 generated vectors")
    F.p("IKM, salt and info are corpus-derived; output length is 64 "
        "bytes — the same shape as GW1 message-key expansion.")
    for i in range(1000):
        ikm = _d(b"hkdf-ikm", i)
        salt = _d(b"hkdf-salt", i)
        info = b"GW1|message-key|" + _d(b"hkdf-info", i, 12)
        out = HKDF(ikm, 64, salt, SHA256, context=info)
        F.vec(f"[HKDF-{i:03d}] ikm={_hx(ikm)}")
        F.vec(f"        salt={_hx(salt)}")
        F.vec(f"        info={_hx(info, 80)}")
        F.vec(f"        okm ={_hx(out)}")

    # ------------------------------------------------------ A.3
    F.h2("A.3  X25519 generated vectors")
    F.p("Each row: a clamped private scalar, the public key derived "
        "from it, and a Diffie–Hellman shared secret against a second "
        "corpus keypair (a, B).  Implementations MUST clamp.")
    for i in range(1600):
        a = _d(b"x25519-a", i)
        b = _d(b"x25519-b", i)
        pub_a = c2.x25519_public(a)
        pub_b = c2.x25519_public(b)
        s = c2.x25519_exchange(a, pub_b)
        F.vec(f"[X255-{i:03d}] a   ={_hx(a)}")
        F.vec(f"        pub ={_hx(pub_a)}")
        F.vec(f"        B   ={_hx(pub_b)}")
        F.vec(f"        ss  ={_hx(s)}")

    # ------------------------------------------------------ A.4
    F.h2("A.4  Ed25519 generated vectors")
    F.p("Random-message signatures; the corpus seed doubles as the "
        "32-byte RFC 8032 secret seed.  Both signature and the "
        "public key are printed so verifiers can be tested without "
        "the signer.")
    for i in range(720):
        seed = _d(b"ed-seed", i)
        msg = _d(b"ed-msg", i, 48)
        pub = c2.ed25519_public(seed)
        sig = c2.ed25519_sign(seed, msg)
        F.vec(f"[ED25-{i:03d}] seed={_hx(seed)}")
        F.vec(f"        pub ={_hx(pub)}")
        F.vec(f"        msg ={_hx(msg)}")
        F.vec(f"        sig ={_hx(sig)}")

    # ------------------------------------------------------ A.5
    F.h2("A.5  AES-256-GCM generated vectors")
    F.p("Nonce construction matches GW1 transport exactly: one "
        "direction byte followed by an 11-byte big-endian counter.  "
        "AAD is the literal b\"GW1\".")
    for i in range(880):
        key = _d(b"gcm-key", i)
        pt = _d(b"gcm-pt", i, 57)  # non-block-aligned on purpose
        nonce = b"c" + i.to_bytes(11, "big")
        aes = AES.new(key, AES.MODE_GCM, nonce=nonce, mac_len=16)
        aes.update(b"GW1")
        ct, tag = aes.encrypt_and_digest(pt)
        F.vec(f"[GCM-{i:03d}] key ={_hx(key)}")
        F.vec(f"        nonce={nonce.hex()} pt={_hx(pt, 72)}")
        F.vec(f"        ct  ={_hx(ct, 72)}")
        F.vec(f"        tag ={tag.hex()}")

    # ------------------------------------------------------ A.6
    F.h2("A.6  Full-session ratchet transcripts")
    F.p("Three complete GW1 sessions are run inside the build.  For "
        "each: both hello blobs, both confirmation MACs, the derived "
        "session id, and every sealed frame of a scripted "
        "conversation, so a black-box protocol implementation can be "
        "exercised end-to-end against a fixed record.")
    import gw.crypto as C
    transcripts = [
        (b"ping", b"pong", b"ack"),
        (b"the quick brown fox jumps over the lazy dog",
         b"0123456789abcdef", b""),
        (bytes(range(200)), b"\x00" * 64, b"fin"),
    ]
    for tno, msgs in enumerate(transcripts):
        ida, idb = C.Identity(), C.Identity()
        ha = C.Handshake(ida, "client")
        hb = C.Handshake(idb, "server")
        ma = ha.hello()
        hb.consume_hello(ma)
        mb = hb.hello(bind=ma["s"])
        ha.consume_hello(mb, bind=ma["s"])
        ha.derive()
        hb.derive()
        F.vec(f"[SESSION-{tno}] hello-c={_hx(C.b64d(ma['s']))}")
        F.vec(f"         hello-s={_hx(C.b64d(mb['s']))}")
        F.vec(f"         sid    ={ha.session_id.hex()}")
        F.vec(f"         c2s-mac={C.b64e(ha.confirm_mac('client'))}")
        F.vec(f"         s2c-mac={C.b64e(hb.confirm_mac('server'))}")
        c2s_tx = C.CipherState(ha.root, b"c2s")
        c2s_rx = C.CipherState(hb.root, b"c2s")
        s2c_tx = C.CipherState(hb.root, b"s2c")
        s2c_rx = C.CipherState(ha.root, b"s2c")
        for j, m in enumerate(msgs):
            f1 = c2s_tx.seal(m)
            assert c2s_rx.open(f1) == m
            f2 = s2c_tx.seal(b"re:" + m)
            assert s2c_rx.open(f2) == b"re:" + m
            F.vec(f"  [frame-{j}] c2s={_hx(f1)}")
            F.vec(f"            s2c={_hx(f2)}")

    # ------------------------------------------------------ A.7
    F.h2("A.7  Ratchet-chain interior traces")
    F.p("For forty seeded chains this prints the *interior* state of "
        "gw.crypto.CipherState step-by-step: the initial chain key "
        "derived from a seeded root, then at every step the message "
        "key fed to AES and the next chain key.  Derivations are "
        "saltless HKDF-SHA256 exactly as shipped.  Anyone "
        "reimplementing the chain must reproduce all three columns "
        "at every step — frames alone (A.5, A.6) do not distinguish "
        "a wrong chain from a wrong nonce.")
    import gw.crypto as _CK
    for ch in range(40):
        root = _d(b"trace-root", ch)
        direction = b"c2s" if ch % 2 == 0 else b"s2c"
        chain = _CK.hkdf(root, b"GW1|chain|" + direction)
        F.vec(f"[CHAIN-{ch:02d}] dir={direction.decode()}")
        F.vec(f"          root ={_hx(root)}")
        F.vec(f"          chain0={_hx(chain)}")
        for step in range(6):
            mk = _CK.hkdf(chain, b"GW1|message-key")
            nxt = _CK.hkdf(chain, b"GW1|ratchet-step")
            F.vec(f"  step {step}  mk  ={_hx(mk)}")
            F.vec(f"          next={_hx(nxt)}")
            chain = nxt
        F.vec("")

    # ------------------------------------------------------ A.8
    F.h2("A.8  Negative vectors (must-reject corpus)")
    F.p("Each entry seals a message, corrupts exactly one structural "
        "field, and replays the corrupted frame against a receiver "
        "whose ratchet state matches the frame's position.  Every "
        "entry MUST be rejected with SecurityError; the expected "
        "message is printed.  Modes: TAG = GCM authentication "
        "failure (tag, ciphertext, nonce or direction-byte edits), "
        "SEQ = counter desync, LEN = truncated frame.")
    import copy
    import gw.crypto as _C
    ida, idb = _C.Identity(), _C.Identity()
    ha = _C.Handshake(ida, "client")
    hb = _C.Handshake(idb, "server")
    ma = ha.hello(); hb.consume_hello(ma)
    mb = hb.hello(bind=ma["s"]); ha.consume_hello(mb, bind=ma["s"])
    ha.derive(); hb.derive()
    tx = _C.CipherState(ha.root, b"c2s")
    rx = _C.CipherState(hb.root, b"c2s")
    modes = [
        ("TAG", -1, "tag bit flipped", "AES-GCM authentication failed"),
        ("TAG", 20, "ciphertext byte flipped", "AES-GCM authentication failed"),
        ("TAG", 10, "nonce counter byte flipped", "AES-GCM authentication failed"),
        ("TAG", 4, "direction byte corrupted", "AES-GCM authentication failed"),
        ("SEQ", None, "counter field +1", "ratchet sequence desync"),
        ("LEN", None, "frame truncated to 20 bytes", "truncated frame"),
    ]
    for i in range(210):
        frame = tx.seal(_d(b"neg-msg", i, 33))
        mode, at, why, expect = modes[i % len(modes)]
        snap = copy.copy(rx)          # receiver state BEFORE this frame
        rx.open(frame)                # keep the honest stream in step
        f = bytearray(frame)
        if mode == "SEQ":
            n = int.from_bytes(f[:4], "big") + 1
            f[:4] = n.to_bytes(4, "big")
        elif mode == "LEN":
            f = f[:20]
        else:
            f[at] ^= 0x01
        try:
            snap.open(bytes(f))
            got = "ACCEPTED (NON-CONFORMING)"
        except _C.SecurityError as e:
            got = str(e)
        F.vec(f"[NEG-{i:03d}] mode={mode} why={why}")
        F.vec(f"         frame={_hx(bytes(f))}")
        F.vec(f"         expected=SecurityError(\"{expect}\")")
        F.vec(f"         observed={got}")

    # =========================================================== B
    F.chapter("Appendix B — Validation Suite Source")
    F.p("docs/validate_gw1.py, shipped verbatim.  It re-runs the "
        "pinned published vectors (A.1) and 25 full handshakes with "
        "tamper checks.  Exit code 0 is a release gate.")
    with open(os.path.join(HERE, "validate_gw1.py")) as f:
        F.code(f.read(), caption="validate_gw1.py")

    # =========================================================== C
    F.chapter("Appendix C — Glossary")
    F.table([
        ["term", "meaning in GW1"],
        ["AEAD", "Authenticated encryption with associated data — AES-256-GCM here."],
        ["AAD", "The associated-data bytes authenticated but not encrypted; literal b\"GW1\"."],
        ["bind", "First client hello hash folded into the server signature to kill downgrade."],
        ["chain", "HKDF-based per-direction message-key sequence; one hop per frame."],
        ["clamp", "RFC 7748 scalar conditioning (clear 3 LSBs, set bit 254, clear 255)."],
        ["confirmation MAC", "Per-role HMAC proving both sides derived the same root key."],
        ["HKDF", "RFC 5869 extract-and-expand KDF; SHA-256 throughout."],
        ["identity key", "Long-term Ed25519 keypair; used only for hello signatures."],
        ["ladder", "Montgomery ladder — X25519 scalar multiplication."],
        ["nonce", "12-byte GCM nonce = 4-byte direction tag || 8-byte counter."],
        ["probe", "8-byte GW1PROBE reconnaissance answered without leaking protocol state."],
        ["root key", "32-byte HKDF output of the handshake; seeds both chains."],
        ["ratchet", "Forward-secrecy key stepping: hkdf(chain, info) per message."],
        ["session id", "SHA-256 of the handshake transcript; UI-visible pairing check."],
        ["softinput_mode", "Kivy keyboard policy; 'below_target' + adjustPan in this app."],
        ["transcript", "Ordered byte record of every handshake field, hashed for keys."],
        ["TTL", "Per-frame lifetime enforced by receivers; expired frames are dropped."],
    ], widths=[90, 370])

    # =========================================================== D
    F.chapter("Appendix D — Normative References")
    refs = [
        ("RFC 2104", "HMAC: Keyed-Hashing for Message Authentication (Krawczyk et al.)."),
        ("RFC 5869", "HMAC-based Extract-and-Expand Key Derivation Function (Krawczyk, Eronen)."),
        ("RFC 7748", "Elliptic Curves for Security (Langley, Hamburg, Turner)."),
        ("RFC 8032", "Edwards-Curve Digital Signature Algorithm (Josefsson, Liusvaara)."),
        ("RFC 8439", "ChaCha20 and Poly1305 — nonce construction rationale used as analogy."),
        ("RFC 5116", "An Interface and Algorithms for Authenticated Encryption (McGrew)."),
        ("NIST SP 800-38D", "Recommendation for Block Cipher Modes of Operation: GCM."),
        ("FIPS 180-4", "Secure Hash Standard (SHA-256)."),
        ("FIPS 198-1", "The Keyed-Hash Message Authentication Code (HMAC)."),
        ("Bernstein 2006", "Curve25519: new Diffie–Hellman speed records."),
        ("Bernstein 2012", "Ed25519: high-speed high-security signatures."),
        ("Marlinspike, Perrin", "The Double Ratchet Algorithm (Signal, 2016) — lineage of §10."),
    ]
    for code, title in refs:
        F.p(f"<b>{code}</b> — {title}")

    # =========================================================== E
    F.chapter("Appendix E — Book Changelog")
    F.table([
        ["rev", "date", "change"],
        ["1.0", "2026-09-21", "Initial release for GHOSTWIRE v1.0.0 / GW1 protocol."],
        ["1.1", "2026-09-21", "GHOSTWIRE v1.1.0: strict peer-to-peer with operator request gate "
         "(§21.2, §26.3); opaque WAN relay source printed (§21.3, §28.3); TTL presets "
         "60 s / 1.5 m / 2 m / 3 m / 5 m (§17.2, §26.6); sweep stealth fix (§26.5); "
         "STANDARDS & RFC panel in-app and in print (§26.7, front matter)."],
    ], widths=[50, 90, 320])
    F.p("End of book.  Developed by @Ariko & Arena.")

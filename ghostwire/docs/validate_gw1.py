"""GHOSTWIRE GW1 validation suite (Tier 1 + Tier 3).

Run on any host or CI before releasing a build:

    python3 validate_gw1.py

Exits non-zero on the first failed assertion.  The generated corpus
(Appendix A of the book) is produced deterministically by
book_appendix.py with the same seeded inputs, so this validator and
the printed book always agree.
"""
import hashlib
import hmac as _hmac
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gw import _curve25519 as c2          # noqa: E402
import gw.crypto as C                     # noqa: E402
from Crypto.Cipher import AES             # noqa: E402
from Crypto.Protocol.KDF import HKDF      # noqa: E402
from Crypto.Hash import SHA256            # noqa: E402

FAILS = []


def check(name, ok):
    if not ok:
        FAILS.append(name)
        print("FAIL:", name)


# ------------------------------------------------------------------ 1
# Tier 1: published vectors
check("rfc7748-x25519", c2.x25519_exchange(
    bytes.fromhex("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a"),
    bytes.fromhex("de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f")
).hex() == "4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742")

_sk = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
check("rfc8032-pub", c2.ed25519_public(_sk).hex() ==
      "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
_sig = c2.ed25519_sign(_sk, b"")
check("rfc8032-sig", _sig.hex() ==
      "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555"
      "fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
check("rfc8032-verify", c2.ed25519_verify(c2.ed25519_public(_sk), b"", _sig))
check("rfc8032-reject", not c2.ed25519_verify(c2.ed25519_public(_sk), b"x", _sig))

# RFC 5869 A.1
prk = _hmac.new(bytes.fromhex("000102030405060708090a0b0c"),
                bytes.fromhex("0b" * 22), hashlib.sha256).digest()
check("rfc5869-extract", prk.hex() ==
      "077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5")

# NIST GCM (256, empty pt): key=0^32, IV=0^12, tag=530f8afb...
aes = AES.new(bytes(32), AES.MODE_GCM, nonce=bytes(12), mac_len=16)
ct, tag = aes.encrypt_and_digest(b"")
check("nist-gcm-empty", tag.hex() == "530f8afbc74536b9a963b4f1c4cb738b" and ct == b"")

# ------------------------------------------------------------------ 3
# Tier 3: protocol property tests
for trial in range(25):
    ida, idb = C.Identity(), C.Identity()
    ha, hb = C.Handshake(ida, "client"), C.Handshake(idb, "server")
    ma = ha.hello()
    hb.consume_hello(ma)
    mb = hb.hello(bind=ma["s"])
    ha.consume_hello(mb, bind=ma["s"])
    ha.derive(); hb.derive()
    check(f"hs-{trial}-root", ha.root == hb.root and
          ha.session_id == hb.session_id)
    ha.check_confirm("server", C.b64e(hb.confirm_mac("server")))
    hb.check_confirm("client", C.b64e(ha.confirm_mac("client")))
    tx = C.CipherState(ha.root, b"client->server")
    rx = C.CipherState(hb.root, b"client->server")
    msg = os.urandom(64)
    frame = tx.seal(msg)
    check(f"aead-{trial}", rx.open(frame) == msg)
    bad = bytearray(frame); bad[30] ^= 1
    try:
        C.CipherState(hb.root, b"client->server").open(bytes(bad))
        check(f"tamper-{trial}", False)
    except C.SecurityError:
        check(f"tamper-{trial}", True)

print("VALIDATION", "FAILED:" + ",".join(FAILS) if FAILS else "OK",
      f"({len(FAILS)} failures)")
sys.exit(1 if FAILS else 0)

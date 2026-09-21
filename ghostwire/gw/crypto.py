"""GHOSTWIRE crypto core.

Design (SIGMA-style authenticated ECDH + ratcheted AES-GCM):

1. Each node owns a long-term Ed25519 *identity key* (used only to sign).
2. Per session, both peers generate fresh ephemeral X25519 keypairs.
3. Hellos are signed: the server's signature additionally binds the
   client's hello, so transcripts cannot be relayed or rebound.
4. Shared secret = X25519(eph, peer_eph).  A root key is derived with
   HKDF-SHA256 salted by the full transcript hash (session id).
5. Two independent symmetric ratchet chains (one per direction) derive a
   FRESH AES-256-GCM key for every single message and then delete the
   previous chain state -> forward secrecy at message granularity.
6. Both sides exchange HMAC key-confirmation MACs before any traffic is
   accepted, so an active attacker cannot complete a session with a
   mismatched key.

Implementation notes (Android build):
  * AES-256-GCM + HKDF come from PyCryptodome, which cross-compiles
    cleanly inside the python-for-android SDL2 bundle.
  * X25519 / Ed25519 use the pure-Python implementations in
    ``gw._curve25519`` (RFC 7748 / RFC 8032 designs).  They run a few
    scalar multiplications per session, and being interpreter-only they
    can never fail with a native dlopen error on Android.
"""

from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import os
import struct

from Crypto.Cipher import AES
from Crypto.Hash import SHA256 as _PCD_SHA256
from Crypto.Protocol.KDF import HKDF as _PCD_HKDF

from gw import _curve25519 as _c

PROTOCOL = "GW1"
KEY_BYTES = 32
MAX_FRAME = 1_000_000


class SecurityError(Exception):
    """Raised on any authentication / integrity failure."""


def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def hkdf(ikm: bytes, info: bytes, salt: bytes | None = None,
         length: int = KEY_BYTES) -> bytes:
    return _PCD_HKDF(ikm, length, salt or b"", _PCD_SHA256, 1, context=info)


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


# --------------------------------------------------------------------------
# Identity (long term Ed25519 signing key)
# --------------------------------------------------------------------------

class Identity:
    def __init__(self, secret: bytes | None = None):
        self.secret = secret or os.urandom(32)

    @property
    def public_bytes(self) -> bytes:
        return _c.ed25519_public(self.secret)

    @property
    def public_b64(self) -> str:
        return b64e(self.public_bytes)

    def sign(self, data: bytes) -> bytes:
        return _c.ed25519_sign(self.secret, data)

    @property
    def fingerprint(self) -> str:
        return self.fingerprint_of(self.public_bytes)

    @staticmethod
    def fingerprint_of(public_bytes: bytes) -> str:
        digest = hashlib.sha256(public_bytes).hexdigest().upper()
        return " ".join(digest[i:i + 4] for i in range(0, 16, 4))

    @staticmethod
    def verify(public_bytes: bytes, signature: bytes, data: bytes) -> None:
        if len(public_bytes) != 32:
            raise SecurityError("malformed identity key")
        if not _c.ed25519_verify(public_bytes, data, signature):
            raise SecurityError("identity signature check failed")


# --------------------------------------------------------------------------
# Handshake
# --------------------------------------------------------------------------

class Handshake:
    """SIGMA-style mutually authenticated ephemeral ECDH handshake."""

    def __init__(self, identity: Identity, role: str):
        if role not in ("client", "server"):
            raise ValueError("role must be client or server")
        self.identity = identity
        self.role = role
        self._eph_secret = os.urandom(32)
        self.eph_pub = _c.x25519_public(self._eph_secret)
        # Role-independent initial state so both peers derive the same
        # transcript hash (role separation comes from signed payloads).
        self.transcript = hashlib.sha256(f"{PROTOCOL}|session|v1".encode())
        self.root: bytes | None = None
        self.session_id: bytes | None = None
        self.peer_id: bytes | None = None
        self.peer_eph: bytes | None = None

    # -- outgoing ---------------------------------------------------------
    def hello(self, bind: str = "") -> dict:
        """Build a signed hello.  `bind` lets the responder commit to the
        initiator's hello (transcript binding)."""
        e, i = b64e(self.eph_pub), self.identity.public_b64
        payload = f"{PROTOCOL}|{self.role}|{e}|{i}|{bind}".encode()
        sig = self.identity.sign(payload)
        self.transcript.update(payload)
        return {"t": "hello", "role": self.role, "e": e, "i": i,
                "s": b64e(sig), "v": PROTOCOL}

    # -- incoming ---------------------------------------------------------
    def consume_hello(self, msg: dict, bind: str = "") -> None:
        """Verify and absorb the peer hello.  Call `derive()` only once the
        transcript is complete (after BOTH hellos are in)."""
        role = msg.get("role")
        if role == self.role or role not in ("client", "server"):
            raise SecurityError("handshake role mismatch")
        if msg.get("v") != PROTOCOL:
            raise SecurityError("protocol version mismatch")
        e64, i64, s64 = msg["e"], msg["i"], msg["s"]
        payload = f"{PROTOCOL}|{role}|{e64}|{i64}|{bind}".encode()
        peer_id = b64d(i64)
        Identity.verify(peer_id, b64d(s64), payload)

        self.transcript.update(payload)
        self.peer_id = peer_id
        self.peer_eph = b64d(e64)

    def derive(self) -> None:
        """Derive session id + root key from the completed transcript."""
        if self.peer_eph is None:
            raise SecurityError("derive() before peer hello")
        if len(self.peer_eph) != 32:
            raise SecurityError("malformed ephemeral key")
        shared = _c.x25519_exchange(self._eph_secret, self.peer_eph)
        self.session_id = self.transcript.digest()
        self.root = hkdf(shared, PROTOCOL.encode() + b"|root",
                         salt=self.session_id)

    def confirm_mac(self, role: str) -> bytes:
        key = hkdf(self.root, PROTOCOL.encode() + b"|confirm")
        return _hmac.new(key, role.encode(), hashlib.sha256).digest()

    def check_confirm(self, role: str, mac_b64: str) -> None:
        expect = self.confirm_mac(role)
        if role not in ("client", "server") or \
                not _hmac.compare_digest(expect, b64d(mac_b64)):
            raise SecurityError("key confirmation MAC mismatch")


# --------------------------------------------------------------------------
# Symmetric ratchet -> fresh AES-256-GCM key per message
# --------------------------------------------------------------------------

class CipherState:
    """One-direction chain.  Each seal/open advances the chain and erases
    the previous state, so old ciphertexts stay protected even if the
    process is later compromised (forward secrecy per message)."""

    def __init__(self, root: bytes, direction: bytes):
        self.chain = hkdf(root, PROTOCOL.encode() + b"|chain|" + direction)
        self.dir = direction[:1]
        self.counter = 0

    def _step(self) -> tuple[bytes, int]:
        msg_key = hkdf(self.chain, PROTOCOL.encode() + b"|message-key")
        self.chain = hkdf(self.chain, PROTOCOL.encode() + b"|ratchet-step")
        self.counter += 1
        return msg_key, self.counter

    def seal(self, plaintext: bytes) -> bytes:
        key, n = self._step()
        nonce = self.dir + n.to_bytes(11, "big")
        aes = AES.new(key, AES.MODE_GCM, nonce=nonce, mac_len=16)
        aes.update(PROTOCOL.encode())
        ct, tag = aes.encrypt_and_digest(plaintext)
        return struct.pack(">I", n) + nonce + ct + tag

    def open(self, frame: bytes) -> bytes:
        if len(frame) < 4 + 12 + 16:
            raise SecurityError("truncated frame")
        n = struct.unpack(">I", frame[:4])[0]
        key, expected = self._step()
        if n != expected:
            raise SecurityError("ratchet sequence desync")
        nonce, body = frame[4:16], frame[16:]
        ct, tag = body[:-16], body[-16:]
        try:
            aes = AES.new(key, AES.MODE_GCM, nonce=nonce, mac_len=16)
            aes.update(PROTOCOL.encode())
            return aes.decrypt_and_verify(ct, tag)
        except Exception as exc:  # ValueError from bad tag
            raise SecurityError("AES-GCM authentication failed") from exc

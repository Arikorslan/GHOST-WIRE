"""Pure-Python X25519 / Ed25519 for GHOSTWIRE.

References:
  * X25519: RFC 7748, based on djb's public-domain reference design.
  * Ed25519: RFC 8032 (python "ed25519" reference implementation design,
    public domain, as published on ed25519.cr.yp.to).

Rationale: zero native extension modules -> nothing can fail to dlopen
inside the python-for-android bundle.  The handshake performs only a
handful of scalar multiplications per session, so interpreter speed is
perfectly adequate for a telemetry app.
"""

from __future__ import annotations

import hashlib

_P = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _P - 2, _P)) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _sha512(data: bytes) -> bytes:
    return hashlib.sha512(data).digest()


def _inv(x: int) -> int:
    return pow(x, _P - 2, _P)


# --------------------------------------------------------------------------
# X25519 (RFC 7748)
# --------------------------------------------------------------------------

_X25519_BASE = 9


def _clamp(k: bytes) -> int:
    k = bytearray(k)
    k[0] &= 248
    k[31] &= 127
    k[31] |= 64
    return int.from_bytes(bytes(k), "little")


def _cswap(swap: int, a: int, b: int) -> tuple[int, int]:
    mask = -swap & ((1 << 256) - 1)
    dummy = mask & (a ^ b)
    return a ^ dummy, b ^ dummy


def _x25519_scalar_mult(k: int, u: int) -> int:
    u %= _P
    x1, x2, z2, x3, z3, swap = u, 1, 0, u, 1, 0
    for t in range(254, -1, -1):
        bit = (k >> t) & 1
        swap ^= bit
        x2, x3 = _cswap(swap, x2, x3)
        z2, z3 = _cswap(swap, z2, z3)
        swap = bit
        A = (x2 + z2) % _P
        AA = A * A % _P
        B = (x2 - z2) % _P
        BB = B * B % _P
        E = (AA - BB) % _P
        C = (x3 + z3) % _P
        D = (x3 - z3) % _P
        DA = D * A % _P
        CB = C * B % _P
        x3 = (DA + CB) % _P
        x3 = x3 * x3 % _P
        z3 = (DA - CB) % _P
        z3 = z3 * z3 % _P * u % _P
        x2 = AA * BB % _P
        z2 = E * (AA + 121665 * E) % _P
    x2, x3 = _cswap(swap, x2, x3)
    z2, z3 = _cswap(swap, z2, z3)
    return x2 * _inv(z2) % _P


def x25519_public(private_key: bytes) -> bytes:
    return _x25519_scalar_mult(_clamp(private_key), _X25519_BASE) \
        .to_bytes(32, "little")


def x25519_exchange(private_key: bytes, peer_public: bytes) -> bytes:
    u = int.from_bytes(peer_public, "little")
    return _x25519_scalar_mult(_clamp(private_key), u).to_bytes(32, "little")


# --------------------------------------------------------------------------
# Ed25519 (RFC 8032)
# --------------------------------------------------------------------------

def _recover_x(y: int, sign: int) -> int:
    if y >= _P:
        raise ValueError("invalid point encoding")
    x2 = (y * y - 1) * _inv(_D * y * y + 1) % _P
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _I % _P
    if (x * x - x2) % _P != 0:
        raise ValueError("invalid point encoding")
    if (x & 1) != sign:
        x = _P - x
    return x


_BY = 4 * _inv(5) % _P
_BX = _recover_x(_BY, 0)
_B = (_BX, _BY, 1, _BX * _BY % _P)
_IDENT = (0, 1, 1, 0)


def _edwards_add(P, Q):
    x1, y1, z1, t1 = P
    x2, y2, z2, t2 = Q
    A = (y1 - x1) * (y2 - x2) % _P
    B = (y1 + x1) * (y2 + x2) % _P
    C = 2 * t1 * t2 * _D % _P
    Dp = 2 * z1 * z2 % _P
    E, F, G, H = B - A, Dp - C, Dp + C, B + A
    return (E * F % _P, G * H % _P, F * G % _P, E * H % _P)


def _point_mul(s: int, P):
    Q = _IDENT
    while s > 0:
        if s & 1:
            Q = _edwards_add(Q, P)
        P = _edwards_add(P, P)
        s >>= 1
    return Q


def _point_compress(P) -> bytes:
    x, y, z, _ = P
    zinv = _inv(z)
    x, y = x * zinv % _P, y * zinv % _P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def _point_decompress(s: bytes):
    if len(s) != 32:
        raise ValueError("invalid point encoding length")
    a = int.from_bytes(s, "little")
    sign, y = (a >> 255) & 1, a & ((1 << 255) - 1)
    x = _recover_x(y, sign)
    return (x, y, 1, x * y % _P)


def _secret_expand(secret: bytes) -> tuple[int, bytes]:
    if len(secret) != 32:
        raise ValueError("bad secret key size")
    h = _sha512(secret)
    a = int.from_bytes(h[:32], "little")
    a = (a & ((1 << 254) - 8)) | (1 << 254)
    return a, h[32:]


def ed25519_public(secret: bytes) -> bytes:
    a, _ = _secret_expand(secret)
    return _point_compress(_point_mul(a, _B))


def ed25519_sign(secret: bytes, message: bytes) -> bytes:
    a, prefix = _secret_expand(secret)
    A = _point_compress(_point_mul(a, _B))
    r = int.from_bytes(_sha512(prefix + message), "little") % _L
    R = _point_compress(_point_mul(r, _B))
    h = int.from_bytes(_sha512(R + A + message), "little") % _L
    s = (r + h * a) % _L
    return R + s.to_bytes(32, "little")


def ed25519_verify(public: bytes, message: bytes, signature: bytes) -> bool:
    if len(public) != 32 or len(signature) != 64:
        return False
    try:
        A = _point_decompress(public)
    except ValueError:
        return False
    R = signature[:32]
    try:
        Rp = _point_decompress(R)
    except ValueError:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:
        return False
    h = int.from_bytes(_sha512(R + public + message), "little") % _L
    sB = _point_mul(s, _B)
    hA = _point_mul(h, A)
    return _point_compress(_edwards_add(Rp, hA)) == _point_compress(sB)

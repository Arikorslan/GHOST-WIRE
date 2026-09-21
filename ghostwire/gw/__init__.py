"""GHOSTWIRE — tactical encrypted messenger.

Protocol stack:
 * Identity / auth ......... Ed25519 signatures (mutual authentication)
 * Key agreement ........... X25519 ECDH, ephemeral per session
  * Key derivation .......... HKDF-SHA256 + symmetric per-message ratchet
  * Transport cipher ........ AES-256-GCM (authenticated encryption)
  * Transience .............. burn-after-read with bilateral incineration
"""

__version__ = "1.1.0"
CODENAME = "GHOSTWIRE"

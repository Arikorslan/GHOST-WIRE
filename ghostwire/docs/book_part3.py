"""Part III — Symmetric Encryption (Chapters 8-10)."""


def build(F):
    F.part("PART III — SYMMETRIC ENCRYPTION")

    # ---------------------------------------------------------- ch 8
    F.chapter("Chapter 8 — AES-256")
    F.h2("8.1  The block cipher")
    F.p("AES-256 (FIPS 197) is a 14-round substitution–permutation "
        "network over a 4×4 byte state: AddRoundKey, SubBytes (the "
        "GF(2⁸) inverse S-box), ShiftRows, MixColumns (multiplication "
        "by the polynomial x³+x+1... x³+{01}... c(x)=03x³+01x²+01x+02 "
        "in the standard ordering). The 256-bit key schedule expands "
        "to 15 round keys with an extra SubWord step every fourth "
        "round.")
    F.h2("8.2  Why 256")
    F.p("AES-128 would suffice against classical adversaries, but the "
        "256-bit key lifts Grover-bounded quantum search to ~2¹²⁸ and "
        "buys margin against related-key and future analytic progress "
        "at negligible cost on ARMv8 crypto extensions. The choice is "
        "deliberate conservatism for a tool whose traffic may be "
        "stored for decades.")
    F.h2("8.3  Where it runs")
    F.p("All AES in the shipped builds executes inside PyCryptodome's "
        "C core (`_raw_aes.abi3.so`), cross-compiled by "
        "python-for-android with the NDK and verified ARM64 in the "
        "APK bundle (Chapter 22). The Python layer never touches "
        "rounds; it only passes key/nonce/AAD and checks tags.")

    # ---------------------------------------------------------- ch 9
    F.chapter("Chapter 9 — Galois/Counter Mode")
    F.h2("9.1  Construction")
    F.p("GCM encrypts with CTR (counter block = 96-bit nonce || "
        "32-bit counter starting at 2 for data, 1 reserved for the "
        "tag key H = E_K(0¹²⁸)) and authenticates AAD and ciphertext "
        "with GHASH, a multiplication hash in GF(2¹²⁸) modulo "
        "x¹²⁸+x⁷+x²+x+1. The tag is GHASH ⊕ E_K(nonce||1).")
    F.h2("9.2  Parameters fixed by GW1")
    F.table([
        ["Parameter", "Value", "Rationale"],
        ["key", "32B (AES-256)", "§8.2"],
        ["nonce", "12B = dir || counter(11B)", "uniqueness by construction"],
        ["tag", "16B", "full-width; 2⁻¹²⁸ forgery bound"],
        ["AAD", "b'GW1'", "binds frames to protocol"],
    ], widths=[80, 150, 220])
    F.h2("9.3  The nonce-reuse catastrophe and its structural "
         "prevention")
    F.p("Reusing (key, nonce) in GCM leaks the XOR of plaintexts and "
        "— worse — the authentication subkey H, enabling universal "
        "forgeries. GW1 removes the hazard by construction: keys are "
        "fresh per message from the ratchet, and even within one key "
        "the nonce embeds the monotonic message counter and a "
        "direction byte. Nonce management is therefore not a runtime "
        "responsibility at all — it is a property of the key "
        "derivation.")
    F.h2("9.4  Verification behaviour")
    F.p("`decrypt_and_verify` raises on any tag mismatch; GW1 maps "
        "every such failure to SecurityError('AES-GCM authentication "
        "failed') and kills the link. Truncated frames (&lt; 4+12+16 "
        "bytes) are rejected before any cryptographic operation "
        "(Chapter 20).")

    # ---------------------------------------------------------- ch 10
    F.chapter("Chapter 10 — Symmetric-Hash Ratchets and Per-Message "
              "Forward Secrecy")
    F.h2("10.1  Chain mechanics")
    F.code("""
    chain_0      = HKDF(root, 'GW1|chain|' + direction)
    msg_key_n    = HKDF(chain_n, 'GW1|message-key')
    chain_{n+1}  = HKDF(chain_n, 'GW1|ratchet-step')
    # chain_n is then overwritten: old state deleted
    """)
    F.p("Each direction owns an independent chain. Because chain_{n+1} "
        "is a one-way hash step of chain_n, learning chain at time t "
        "yields no chain state before t, hence no earlier message "
        "keys: per-message forward secrecy without the bookkeeping of "
        "a full Double Ratchet.")
    F.h2("10.2  Synchronisation and fail-closed desync")
    F.p("The receiver expects counter n+1 exactly; any other counter "
        "means a dropped, injected or replayed frame, and the link is "
        "torn down rather than resynchronised. For a telemetry/messenger "
        "tool over reliable streams (TCP/RFCOMM) in-order delivery is "
        "guaranteed, so strict monotonicity is free integrity.")
    F.h2("10.3  Comparison with the Double Ratchet")
    F.p("Signal's Double Ratchet adds out-of-order tolerance and "
        "post-compromise healing via DH ratchet steps. GW1 trades "
        "those for simplicity and deterministic fail-closed behaviour "
        "on transports that already order bytes; post-compromise "
        "healing is approximated by transience (burn-after-read) "
        "instead of ratchet mechanics. The trade-off is documented "
        "here so maintainers do not ‘fix’ the desync behaviour into a "
        "resynchronisation — doing so would create a replay oracle.")
    F.h2("10.4  Erasure guarantees")
    F.p("Python cannot promise RAM zeroisation (the interpreter may "
        "have copied bytes), but re-binding `self.chain` drops the "
        "only reference the program keeps; CPython frees the buffer "
        "promptly under reference counting. The guarantee is "
        "therefore: no *program-visible* old state survives a step, "
        "which is the honest claim the UI makes (‘keys rotated’).")

"""Part VIII — Field Operations: usage guide, strengths & limitations,
and wide-area (WAN) deployment."""


def build(F):
    F.part("PART VIII — FIELD OPERATIONS")
    F.p("Parts I–VII describe what GHOSTWIRE is; this part describes "
        "how it is used, where it is strong, where it is honestly "
        "weak, and under what conditions it can be operated beyond a "
        "local network segment.")

    # ============================================================ 26
    F.chapter("Chapter 26 — Operating GHOSTWIRE")
    F.p("This chapter is the operator's manual. It follows the exact "
        "screen flow of release 1.1.0 on Android 10+. The same "
        "modules run unmodified on desktop Python for testing.")

    F.h2("26.1  Requirements and installation")
    F.bullets([
        "Android 10 or newer (minSdk 24, targetSdk 34); the debug "
        "APK installs without Play-Store warnings.",
        "No permissions beyond INTERNET, network state and the four "
        "BLUETOOTH_* grants needed by the RFCOMM transport.",
        "Desktop testing: CPython 3.10+, PyCryptodome, Kivy/KivyMD; "
        "the crypto core itself has zero GUI dependencies and runs "
        "under bare interpreter.",
        "Two devices are the minimum useful deployment: one deploys a "
        "node, the other initiates the uplink.",
    ])

    F.h2("26.2  First boot and the splash")
    F.p("Boot plays the animated splash (the presplash continues the "
        "same animation so there is no visual seam), shows the "
        "GHOSTWIRE wordmark and the credits line DEVELOPED BY "
        "@Ariko & Arena, then lands on the home screen. Nothing is "
        "transmitted at boot; identities are generated locally and "
        "no network socket is opened until the operator acts.")

    F.h2("26.3  Home screen — NODE CONTROL")
    F.p("The home screen carries the NODE CONTROL card. Fields and "
        "their effects:")
    F.table([
        ["control", "default", "effect"],
        ["BIND ADDR", "0.0.0.0",
         "Interface to listen on. 0.0.0.0 = every interface; pin to "
         "a specific address to expose the node on one NIC only."],
        ["PORT", "9999", "TCP port for the GW1 listener."],
        ["DEPLOY NODE / STOW NODE", "—",
         "Toggles the GW1 listener thread. Status line reads OFFLINE "
         "or reports the bound address while deployed."],
        ["SITREP panel", "—", "Session state: active link, peer, "
         "session id, transport counters."],
        ["shield-lock (top bar)", "—", "Opens the SECURITY PROTOCOLS "
         "screen (Chapter 26.7)."],
    ])
    F.p("Deploying a node does not contact anyone; it binds, listens "
        "(backlog 8) and waits. Incoming connections are triaged by "
        "peeking the first 8 bytes: GW1PROBE traffic takes the "
        "reconnaissance path, anything else enters the 15-second "
        "handshake window. Failed handshakes close the socket and log "
        "the rejection class — the node never reveals why.")
    F.p("A deployed node hosts MULTIPLE simultaneous secure links "
        "(MAX_PEERS = 8 on TCP, 4 on RFCOMM). Every accepted "
        "connection performs its own independent handshake and gets "
        "its own ratchet pair, reader thread and conversation on the "
        "operator's screen; a hard cap bounds resource exposure and "
        "refuses the excess with SESSION LIMIT REACHED. The outbound "
        "side is symmetric: the device may hold several uplinks at "
        "once. Each channel is cryptographically isolated — separate "
        "ephemeral keys, separate roots, separate chains.")

    F.h2("26.4  ESTABLISH UPLINK — initiating a session")
    F.p("The connect screen collects the target and transport, then "
        "drives the handshake with a live console:")
    F.table([
        ["field / action", "meaning"],
        ["TARGET HOST / IP", "Hostname or IP of the remote node."],
        ["TARGET PORT", "Remote GW1 port (default 9999)."],
        ["WIFI / LAN", "TCP transport over IP — LAN or, with routing "
         "in place, WAN (Chapter 28)."],
        ["BLUETOOTH RFCOMM", "The identical GW1 protocol over an "
         "RFCOMM socket (channel 7); the target becomes a BD_ADDR."],
        ["INITIATE HANDSHAKE", "Runs the client side of §4: hello "
         "exchange, signature verification, ECDH, ratchet online, "
         "key confirmation."],
        ["DROP", "Tears the link down; ratchet state is discarded."],
        ["HANDSHAKE CONSOLE", "Line-by-line status of every handshake "
         "phase, including the exact SecurityError on failure."],
    ])
    F.p("The console also prints the local identity fingerprint at "
        "startup. A successful uplink ends with SECURE LINK "
        "ESTABLISHED and the session id; from that moment every "
        "character typed is sealed with a fresh AES-256-GCM key.")

    F.h2("26.5  Discovery — the SCAN screen")
    F.p("SCAN sweeps a target range with capped breadth (at most 1024 "
        "hosts per sweep, connect timeout 0.35 s, probe timeout 1.0 "
        "s). The results list admits ONLY hosts that answer GW1PROBE "
        "with a valid GW1PONG fingerprint: open ports with no GW1 "
        "answer are silently ignored, since listing them would "
        "expose the very stealth nodes the operator is entitled to "
        "hide. Each reachable GW1 node answers with its identity "
        "fingerprint unless its operator has enabled stealth, in "
        "which case it stays silent and simply does not appear. "
        "Sweeps are stoppable mid-run. Treat sweep results as hints "
        "only: absence of a pong is not proof of absence.")

    F.h2("26.6  CHAT — the secure channel")
    F.p("The chat header shows the endpoint and the peer fingerprint; "
        "the banner reminds of the guarantees in force: AES-256-GCM "
        "E2E, ratcheted keys, burn after read. When the node hosts "
        "several peers, the SESSION strip under the banner lists one "
        "chip per live channel — direction glyph (inbound/outbound), "
        "peer fingerprint, and an unread counter for channels that "
        "received traffic while backgrounded. Tapping a chip swaps "
        "the whole conversation view; every session keeps its own "
        "message list, and the security screen follows the active "
        "session.")
    F.bullets([
        "shield-check — opens the verification dialog: compare the "
        "peer fingerprint (and, verbally, the session id) over an "
        "independent channel. This is the MITM tripwire; do it once "
        "per session.",
        "delete-forever — BURN: bilateral self-destruct of the "
        "active conversation on both devices; message objects carry "
        "TTL and are not persisted between runs by design.",
        "link-variant-off — DROP ALL: terminates every live channel "
        "at once.",
        "power — disconnect the ACTIVE channel only; the others stay "
        "up. Keys die with their link.",
        "Delivery state travels as authenticated ack/del objects per "
        "channel, so both screens agree on what was actually "
        "received.",
    ])

    F.h2("26.7  SECURITY PROTOCOLS screen")
    F.p("Read-only transparency panel: the full cipher suite in force "
        "(X25519 ephemeral KEX, Ed25519 mutual signatures, HKDF + "
        "symmetric ratchet, AES-256-GCM, HMAC key confirmation, "
        "bilateral burn), the live session id and the peer "
        "fingerprint. If any line does not match this book, stop and "
        "investigate — the code is the spec.")

    F.h2("26.8  Typical session, start to finish")
    F.p("1. Operator A deploys a node (home → DEPLOY NODE). "
        "2. Operator B scans the segment or is told the address, "
        "opens ESTABLISH UPLINK and initiates the handshake. "
        "3. A's screen raises the INBOUND REQUEST dialog; A taps "
        "ACKNOWLEDGE and the handshake proceeds. "
        "4. Both consoles report SECURE LINK ESTABLISHED with the "
        "same session id. 5. Both compare fingerprints via the "
        "verify dialog. 6. Chat; the selected TTL bounds each "
        "message's lifetime. 7. Either party burns or disconnects; "
        "nothing useful remains in memory afterwards.")

    F.h2("26.9  Troubleshooting")
    F.table([
        ["symptom", "likely cause", "remedy"],
        ["HANDSHAKE REJECTED (SecurityError)", "tampered or replayed "
         "hello, version mismatch, role confusion", "do not retry "
         "blindly; verify addresses and fingerprints out-of-band"],
        ["identity signature check failed", "wrong/stale peer key or "
         "MITM substitution", "compare fingerprints; abort if they "
         "differ"],
        ["key confirmation MAC mismatch", "peers derived different "
         "roots — active interference or bug", "abort; treat as "
         "attack"],
        ["no pong in SCAN", "stealth node, firewall, wrong port",
         "connect directly by address"],
        ["connection refused on WAN host", "NAT without port forward",
         "Chapter 28.3"],
        ["ratchet sequence desync", "byte-pipe corruption or a "
         "middlebox replaying frames", "re-key by reconnecting"],
    ])

    # ============================================================ 27
    F.chapter("Chapter 27 — Strengths and Limitations")
    F.p("An honest ledger. Marketing copy is elsewhere; this chapter "
        "is what a reviewer should hold the design against.")

    F.h2("27.1  Strengths")
    F.bullets([
        "Mutual authentication by construction: both hellos signed, "
        "server hello transcript-bound; no password, no PKI, no "
        "trust-on-first-use leap of faith.",
        "Explicit key confirmation before the first byte of traffic "
        "— a mismatched key can never silently carry messages.",
        "Forward secrecy at message granularity: compromising the "
        "process mid-session exposes only future frames.",
        "Strict sequencing rejects replay, reordering and "
        "injection outright rather than buffering them.",
        "Fail-closed everywhere: every parse and verification failure "
        "is a SecurityError with a precise message — no warning-only "
        "paths, no crypto silently skipped.",
        "Fully auditable on the target platform: the public-key core "
        "is 195 lines of pure Python printed in Chapter 19; there is "
        "no opaque native code on the trust path.",
        "Stealth discipline: probes leak no protocol state, and a "
        "stealth node leaks nothing at all.",
        "Bilateral burn plus no-at-rest storage: conversation state "
        "is deliberately ephemeral.",
    ])

    F.h2("27.2  Limitations — by design")
    F.bullets([
        "Endpoint trust: a seized unlocked device ends every "
        "guarantee. GW1 protects the wire, not the endpoints.",
        "Strictly two-party: one node, one live link, no group "
        "ratchet. The request gate (Chapter 26.3) enforces this "
        "socially as well as technically — every connection is an "
        "acknowledged decision.",
        "Synchronous by design: no store-and-forward, no offline "
        "delivery, no message history. Both parties must be online "
        "simultaneously.",
        "Strict counters mean no multipath and no lossy-pipe "
        "tolerance: GW1 assumes TCP (or RFCOMM) ordering and treats "
        "gaps as attacks.",
        "Identity keys are generated per install and not exported. "
        "Reinstall means a new fingerprint — expected, but operators "
        "must re-verify peers afterwards.",
        "Pure-Python curve arithmetic is not constant-time; remote "
        "sub-microsecond timing attacks are out of the threat model, "
        "and the book says so wherever it matters (§14.3).",
    ])

    F.h2("27.3  Limitations — of the medium")
    F.bullets([
        "Metadata is exposed: who connects to whom, when, and how "
        "much. Frame lengths are padded only by the JSON payload "
        "shape, not to fixed sizes.",
        "An open GW1 port is detectable by port scanning even when "
        "stealth hides the protocol banner.",
        "No post-quantum component: a harvest-now-decrypt-later "
        "adversary with a future CRQC could recover recorded "
        "sessions (transcripts contain no long-term secrets, so the "
        "window is the recording window — but it is not zero).",
        "Throughput is messenger-scale, not file-transfer-scale: "
        "the per-message HKDF step and pure-Python signing bound "
        "handshake rate, not message rate, but bulk transfer was "
        "never the intent.",
    ])

    F.h2("27.4  Positioning")
    F.p("GW1 is strongest exactly where it was aimed: short-lived, "
        "high-value conversations between two operators who can "
        "compare fingerprints, on networks they do not control. It "
        "is deliberately not a general-purpose chat platform, and "
        "its gaps (groups, offline, history, PQ) are the price of "
        "being fully auditable in under 900 lines of protocol code.")

    # ============================================================ 28
    F.chapter("Chapter 28 — Wide-Area (WAN) Operation")
    F.p("Question operators ask first: can this cross the internet, "
        "not just the room? Answer: yes — the cryptographic layer is "
        "WAN-transparent — with three caveats about reachability, "
        "discovery and metadata.")

    F.h2("28.1  Why the protocol itself is WAN-ready")
    F.bullets([
        "GW1 needs only an ordered, reliable byte pipe. TCP gives "
        "that across any number of hops; the strict counter "
        "discipline (§7.2) is satisfied by TCP ordering guarantees.",
        "The handshake is four short messages (hello, hello, "
        "confirm, confirm). Latency adds delay, not fragility: a "
        "300 ms round trip costs ~1.2 s of setup, once.",
        "Mutual authentication matters more on WAN, not less — and "
        "GW1 already performs it. There is no TLS underneath and "
        "none is needed: identity signatures plus key confirmation "
        "provide the equivalent guarantees end-to-end.",
        "The RFCOMM transport is the same code over Bluetooth; WAN "
        "operation changes nothing in gw/crypto.py.",
    ])

    F.h2("28.2  LAN versus WAN, honestly compared")
    F.table([
        ["concern", "LAN", "WAN"],
        ["reachability", "direct IP on the segment",
         "needs routable address (public IP, port forward, tunnel)"],
        ["discovery", "SCAN sweep finds nodes",
         "sweeps are meaningless — address must be arranged "
         "out-of-band"],
        ["handshake cost", "milliseconds", "four round trips of WAN "
         "latency"],
        ["fingerprint check", "can be visual/verbal in person",
         "must use an independent trusted channel"],
        ["observer", "segment-local", "global passive observer; "
         "metadata exposure grows"],
        ["stealth value", "hides banner from sweeps",
         "open port still visible to scanners"],
    ])

    F.h2("28.3  Making a node reachable")
    F.p("Choose one, in order of preference:")
    F.bullets([
        "Opaque relay (relay_server.py, shipped) — run "
        "'python3 relay_server.py --host 0.0.0.0 --port 9999' on "
        "any host both devices can reach, then dial that host with "
        "the WAN RELAY transport on both phones. The relay pairs "
        "dialers two at a time, tells the first 'you are the "
        "server seat' and the second 'you are the client seat', "
        "and pipes bytes until either side hangs up. It is blind "
        "by construction: no GW1 parsing, no keys — handshakes "
        "and messages cross as opaque ciphertext — so it can "
        "neither read nor forge traffic. Only addresses, pairing "
        "times and byte counts are visible to it.",
        "Direct public address — the node binds 0.0.0.0:9999 and is "
        "reached at its public IP. Simplest; expose only the one "
        "port.",
        "Port forwarding — behind NAT, forward external TCP port to "
        "the device's LAN address. The GW1 listener is indifferent "
        "to being behind NAT; only the initiator needs the mapped "
        "address.",
        "Reverse tunnel — when neither side controls the edge (both "
        "behind NAT), run the node behind an outbound tunnel to a "
        "rendezvous host both operators can reach. GW1 rides the "
        "tunnel unmodified; the tunnel is a pipe, not a trust "
        "dependency — it cannot read the traffic.",
    ])
    F.p("Not provided by design: NAT hole-punching and rendezvous "
        "infrastructure. Adding third parties to a protocol whose "
        "central promise is that there are none is not done "
        "lightly — which is exactly why the shipped relay is "
        "blind by construction and operator-controlled. A tunnel "
        "or relay the operators run themselves keeps that promise; "
        "a vendor relay would break it.")

    F.h2("28.4  WAN deployment patterns")
    F.bullets([
        "Fixed node + roaming operator: one device with stable "
        "reachability (home server, VPS tunnel endpoint) holds the "
        "node; the second device initiates from anywhere.",
        "Scheduled windows: because sessions are synchronous, "
        "operators agree on times; the node can be deployed only "
        "during the window and stowed afterwards, shrinking the "
        "exposure interval.",
        "Bluetooth fallback: if WAN reachability fails or is "
        "suspected compromised, the RFCOMM transport gives a "
        "zero-infrastructure path within radio range.",
    ])

    F.h2("28.5  WAN-specific threats and responses")
    F.table([
        ["threat", "status"],
        ["active MITM on the path", "defeated — hello signatures + "
         "key confirmation (§4, §6); fingerprint comparison is the "
         "human backstop"],
        ["passive content recovery", "defeated — AEAD + per-message "
         "forward secrecy (§5, §8)"],
        ["malicious or seized relay host", "content still defeated — "
         "the relay holds no keys (§28.3); metadata (who, when, how "
         "much) and denial-of-service remain exposed — run your "
         "own host and keep contact windows short"],
        ["harvest-now-decrypt-later", "residual (§8, §27.3): "
         "recorded sessions only, bounded by the recording window"],
        ["traffic analysis / metadata", "residual and amplified on "
         "WAN (§27.3): volume, timing and endpoints visible; "
         "mitigate with short windows and steady, unremarkable "
         "scheduling"],
        ["port discovery by scanners", "partial: stealth silences "
         "probes but not the open port itself; move ports, restrict "
         "by firewall where possible"],
        ["SYN floods / resource exhaustion", "bounded by the OS "
         "backlog and daemon threads; handshake work per attacker "
         "connection is capped by the 15 s window and fails cheap"],
    ])

    F.h2("28.6  WAN pre-flight checklist")
    F.bullets([
        "Reachability proven with plain connectivity before relying "
        "on it in the field.",
        "Fingerprints exchanged over an independent channel and "
        "verified at the first session — mandatory at distance.",
        "Session id read back verbally once; both ends must match.",
        "Agreed burn discipline: who burns, and when.",
        "Clock sanity: message TTLs are enforced per-message; wildly "
        "skewed clocks are an operator-error source, not a crypto "
        "one.",
        "Stow policy: node down outside contact windows.",
    ])
    F.p("Summary: LAN is GW1's native terrain; WAN is fully supported "
        "by the cryptography and the transport, and is limited only "
        "by ordinary IP reachability and the metadata cost of being "
        "on the public internet.")

# GHOSTWIRE — Tactical Encrypted Messenger

A KivyMD "military-grade" secure chat application. Encrypted peer-to-peer
messaging over **WiFi/LAN (TCP)** and **Bluetooth RFCOMM**, with network
reconnaissance to discover other GHOSTWIRE nodes, and **burn-after-read**
transmissions that self-destruct on both devices once read.

## Screenshots (`shots/`)

| File | Shows |
|---|---|
| `01_home.png` | Launch screen: node control, SITREP, ops buttons |
| `01_node_deployed.png` | Node listening on `127.0.0.1:9999` |
| `02_network_sweep.png` | LAN sweep discovers a live GHOSTWIRE node + its fingerprint |
| `03_handshake.png` | Handshake console: signature check, ECDH, ratchet, key confirmation |
| `04_chat.png` | Client view: encrypted chat with `T-x s` burn countdowns |
| `04b_chat_server.png` | Same conversation from the server's perspective |
| `05_security.png` | Cipher suite, live session id, peer fingerprint, stealth toggle |

Run `./demo.sh` to reproduce: it boots **two real app instances under Xvfb**,
the client sweeps the network, finds the server, completes the GW1 handshake
over loopback and exchanges traffic while screenshots are captured.

## Run it

```bash
pip install "kivy[base]==2.3.1" "kivymd==1.2.0" pycryptodome
python3 main.py                      # interactive (400x720 window)
GW_DEMO=server python3 main.py       # scripted demo node
GW_DEMO=client python3 main.py       # scripted demo operative
```

Headless boxes need `xvfb-run -a python3 main.py`.

## Android APK

The project ships APK-ready (`buildozer.spec`, `icon.png`, portrait
fullscreen layout, scrollable screens, Android permissions for LAN +
Bluetooth). Build with:

```bash
pip install buildozer
sudo apt install openjdk-17-jdk zip unzip autoconf libtool pkg-config zlib1g-dev
yes | sdkmanager --licenses        # accept Android SDK licenses
buildozer android debug            # -> bin/ghostwire-1.0.0-arm64-v8a-debug.apk
```

The spec targets `arm64-v8a`, API 34 (min 24, so Android 7.0+ including
Android 10–15), and requests INTERNET,
ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE plus the BLUETOOTH_* permissions
for the RFCOMM transport. `android.allow_backup = False` so nothing the app
holds survives device backup. The activity manifest sets
`windowSoftInputMode="adjustResize"` and the app additionally calls
`setSoftInputMode(SOFT_INPUT_ADJUST_RESIZE)` at startup, so the window
shrinks when the soft keyboard opens and text fields (chat composer,
host/port inputs) stay visible. On launch the app plays an animated
boot splash (radar sweep, cipher scramble, progress readout) before the
home screen. The native Android presplash is animated too:
`android.presplash_lottie = ./presplash.json` ships a Lottie radar-sweep
animation (plus a matching static frame as fallback) that hands over
seamlessly to the in-app splash. Credits ("developed by @Ariko & Arena")
appear on the splash footer and in a CREDITS card on the home screen.

## The GW1 protocol (`gw/crypto.py`, `gw/net.py`)

| Stage | Primitive |
|---|---|
| Long-term identity | Ed25519 signing keys (RFC 8032, pure-Python `gw/_curve25519.py`), SHA-256 fingerprints shown for out-of-band verification |
| Key agreement | Ephemeral **X25519** ECDH (RFC 7748, pure-Python) per session — SIGMA-style signed hellos; responder's signature binds the initiator's hello |
| Key derivation | HKDF-SHA256 salted with the full transcript hash (= session id) |
| Key confirmation | HMAC-SHA256 MAC exchange before any traffic is accepted |
| Transport cipher | **AES-256-GCM** (PyCryptodome) with a fresh key for *every* message via a symmetric ratchet (HKDF chain step, chain state deleted after use → forward secrecy per message) |
| Framing | 4-byte length-prefixed frames; TCP and Bluetooth RFCOMM carry the identical protocol |
| Discovery | TCP connect scan + `GW1PROBE`/`GW1PONG` probe that returns the node fingerprint (silent when *stealth mode* is on) |

Unit-verified behaviours: mutual authentication, tamper detection
(`InvalidTag`), replay rejection (ratchet desync = fail-closed link death).

## Burn-after-read

Every transmission carries a TTL (5/10/30/60 s, selector in the composer).
On display the receiver sends a `seen` ACK ("READ BY PEER // KEY ROTATED")
and both peers run the countdown; at zero the message is **incinerated on
both devices** (`burned` ACK, bilateral deletion). `delete-forever` in the
chat bar burns everything immediately. Nothing is ever written to disk.

## Transports

* **WiFi/LAN** — connect by IP:port, or deploy a node and be discovered.
* **Bluetooth** — identical secure link over RFCOMM
  (`gw.net.BluetoothNode` / `bluetooth_connect`). The sandbox has no BT
  adapter; on Android/Linux with a real adapter the same handshake applies
  (Android additionally needs BLUETOOTH_CONNECT/SCAN permissions in a
  packaging wrapper such as Buildozer).

## Honest threat notes

No system is "unbreakable" — the app says so on its own security screen.
GW1 gives you confidentiality, integrity, mutual authentication, per-message
forward secrecy and transience. It does **not** (yet) provide anonymity /
metadata hiding, post-quantum KEMs (none of the in-bundle primitives ship
ML-KEM), or protection against a compromised endpoint. Verify
fingerprints out-of-band before classified traffic; your device remains the
weakest link.

## Layout

```
ghostwire/
  main.py        entry point + demo automation (GW_DEMO=server|client)
  demo.sh        two-instance Xvfb demo + screenshot capture
  gw/crypto.py   identity, handshake, ratcheted AES-256-GCM cipher
  gw/net.py      SecureLink, NodeServer, sweep scanner, Bluetooth RFCOMM
  gw/ui.py       KivyMD screens: home / connect / scan / chat / security
  shots/         captured UI screenshots
```

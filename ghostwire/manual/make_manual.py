#!/usr/bin/env python3
"""Build the GHOSTWIRE v1.1.0 Operator's Manual (illustrated user guide).

Usage:  python3 manual/make_manual.py
Output: manual/GHOSTWIRE_Operators_Manual_v1.1.0.pdf  (hard cap: 50 pages)
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
OUT = os.path.join(HERE, "GHOSTWIRE_Operators_Manual_v1.1.0.pdf")
MAX_PAGES = 50

from reportlab.lib.pagesizes import A4                       # noqa: E402
from reportlab.lib.units import mm                            # noqa: E402
from reportlab.lib.colors import HexColor                     # noqa: E402
from reportlab.lib.styles import ParagraphStyle               # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_LEFT            # noqa: E402
from reportlab.platypus import (                              # noqa: E402
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Image, Table, TableStyle, PageBreak, KeepTogether,
    NextPageTemplate,
)
from reportlab.platypus.tableofcontents import TableOfContents  # noqa: E402
from reportlab.pdfbase import pdfmetrics                      # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont                  # noqa: E402

# ---------------------------------------------------------------- palette
GREEN = HexColor("#1B7A3D")
DARK = HexColor("#0B0E0B")
MUTED = HexColor("#5A6B5D")
LIGHT_BG = HexColor("#EDF5EE")
HAIR = HexColor("#BFD8C2")
WHITE = HexColor("#FFFFFF")
AMBER = HexColor("#9A6B12")
RED = HexColor("#A4262C")

# ------------------------------------------------------------- typefaces
try:
    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVuMono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
    BODY_FONT, BOLD_FONT, MONO_FONT = "DejaVu", "DejaVu-B", "DejaVuMono"
except Exception:
    BODY_FONT, BOLD_FONT, MONO_FONT = "Helvetica", "Helvetica-Bold", "Courier"

# ---------------------------------------------------------------- styles
S = {}
S["h1"] = ParagraphStyle("h1", fontName=BOLD_FONT, fontSize=17,
                         leading=21, textColor=GREEN, spaceBefore=6,
                         spaceAfter=8, keepWithNext=True)
S["h2"] = ParagraphStyle("h2", fontName=BOLD_FONT, fontSize=12.5,
                         leading=16, textColor=DARK, spaceBefore=10,
                         spaceAfter=5, keepWithNext=True)
S["body"] = ParagraphStyle("body", fontName=BODY_FONT, fontSize=9.5,
                           leading=14.5, alignment=TA_LEFT, spaceAfter=5)
S["bullet"] = ParagraphStyle("bullet", parent=S["body"], leftIndent=14,
                             bulletIndent=4, spaceAfter=3.5)
S["mono"] = ParagraphStyle("mono", fontName=MONO_FONT, fontSize=8.6,
                           leading=12.5, textColor=DARK, spaceAfter=5)
S["caption"] = ParagraphStyle("caption", fontName=BOLD_FONT, fontSize=8.5,
                              leading=11.5, textColor=MUTED,
                              alignment=TA_CENTER, spaceBefore=4, spaceAfter=8)
S["cover1"] = ParagraphStyle("cover1", fontName=BOLD_FONT, fontSize=30,
                             leading=34, textColor=GREEN, alignment=TA_CENTER)
S["cover2"] = ParagraphStyle("cover2", fontName=BODY_FONT, fontSize=13,
                             leading=17, textColor=MUTED, alignment=TA_CENTER)
S["toc_h"] = ParagraphStyle("toc_h", fontName=BOLD_FONT, fontSize=17,
                            leading=21, textColor=GREEN, spaceAfter=10)

PAGE_W, PAGE_H = A4


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(BODY_FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(PAGE_W / 2, 14 * mm,
                             f"GHOSTWIRE v1.1.0 — Operator's Manual    ·    "
                             f"page {doc.page}")
    canvas.setStrokeColor(HAIR)
    canvas.line(18 * mm, 16.5 * mm, PAGE_W - 18 * mm, 16.5 * mm)
    canvas.restoreState()


def cover_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(BODY_FONT, 8)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(PAGE_W / 2, 18 * mm,
                             "developed by @Ariko & Arena")
    canvas.restoreState()


story = []
_fig_no = [0]


def h1(t):
    story.append(Paragraph(t, S["h1"]))


def h2(t):
    story.append(Paragraph(t, S["h2"]))


def p(t):
    story.append(Paragraph(t, S["body"]))


def bullets(items):
    for it in items:
        story.append(Paragraph(it, S["bullet"], bulletText="•"))


def mono_block(lines):
    for ln in lines:
        story.append(Paragraph(ln.replace(" ", "&nbsp;"), S["mono"]))


def note(title, text):
    inner = [[Paragraph(f"<b>{title}</b> — {text}", S["body"])]]
    t = Table(inner, colWidths=[PAGE_W - 36 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))


def fig(name, caption, width_mm=58):
    _fig_no[0] += 1
    img = Image(os.path.join(FIG, name + ".png"))
    img.drawWidth = width_mm * mm
    img.drawHeight = width_mm * mm * 720 / 400
    story.append(KeepTogether([
        img, Paragraph(f"Figure {_fig_no[0]} — {caption}", S["caption"]),
    ]))


def table(header, rows, widths_mm):
    data = [[Paragraph(f"<b>{c}</b>", S["body"]) for c in header]]
    for r in rows:
        data.append([Paragraph(c, S["body"]) for c in r])
    t = Table(data, colWidths=[w * mm for w in widths_mm],
              repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, HAIR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))


# ================================================================= COVER
story.append(NextPageTemplate("cover"))
story.append(Spacer(1, 26 * mm))
story.append(Paragraph("GHOSTWIRE", S["cover1"]))
story.append(Spacer(1, 4 * mm))
story.append(Paragraph("Operator's Manual · v1.1.0", S["cover2"]))
story.append(Paragraph("Tactical encrypted messenger // GW1 protocol", S["cover2"]))
story.append(Spacer(1, 8 * mm))
_cover_img = Image(os.path.join(FIG, "m_splash.png"))
_cover_img.drawWidth = 62 * mm
_cover_img.drawHeight = 62 * mm * 720 / 400
story.append(_cover_img)
story.append(Spacer(1, 8 * mm))
story.append(Paragraph("Install it. Deploy a node. Verify your peer. Chat.<br/>"
                       "Everything in this book is illustrated with real "
                       "screenshots from the app.", S["cover2"]))
story.append(NextPageTemplate("main"))
story.append(PageBreak())

# ==================================================================== TOC
story.append(Paragraph("Contents", S["toc_h"]))
_toc = TableOfContents()
_toc.levelStyles = [
    ParagraphStyle("toc1", fontName=BOLD_FONT, fontSize=10, leading=14.5,
                   textColor=DARK, spaceBefore=1, spaceAfter=0),
    ParagraphStyle("toc2", fontName=BODY_FONT, fontSize=9, leading=12.5,
                   leftIndent=10, textColor=MUTED, spaceBefore=0,
                   spaceAfter=0),
]
story.append(_toc)
story.append(PageBreak())

CHAPTERS = []


def chapter(no, title):
    CHAPTERS.append((no, title))
    h1(f"{no}&nbsp;&nbsp;{title}")


# ============================================================ 1 · WELCOME
chapter("1", "Welcome, operative")
p("GHOSTWIRE is a tactical encrypted messenger for two people who need "
  "to talk privately on a network they do not control. There are no "
  "accounts, no servers holding your messages, and no chat history: two "
  "devices form a <b>one-to-one encrypted channel</b>, exchange messages "
  "that self-destruct on timers you choose, and leave nothing behind.")
h2("1.1&nbsp;&nbsp;What you get in v1.1.0")
bullets([
    "<b>Strictly peer-to-peer.</b> One node, one live link, two parties. "
    "Every incoming connection waits at a request gate until you "
    "personally ACKNOWLEDGE or REJECT it — nobody can silently join or "
    "knock your peer off.",
    "<b>Military-grade encryption, automatic.</b> X25519 key exchange, "
    "Ed25519 mutual signatures and AES-256-GCM message encryption with "
    "keys that rotate on every single message. You never touch a key.",
    "<b>Burn-after-reading timers.</b> Each message carries a fuse: "
    "60 seconds by default, or 1.5, 2, 3 and 5 minutes. Both sides "
    "delete the message when the fuse hits zero.",
    "<b>Three transports.</b> Wi-Fi/LAN, Bluetooth (RFCOMM), and a WAN "
    "relay for chatting across the internet through a relay that is "
    "blind by design — it can neither read nor forge your traffic.",
    "<b>Stealth mode.</b> Your node can go silent to network sweeps "
    "while still accepting connections from peers who know your address.",
    "<b>Radical transparency.</b> A built-in SECURITY PROTOCOLS screen "
    "names every cipher and standard in force, so anyone can audit what "
    "the app claims.",
])
h2("1.2&nbsp;&nbsp;What you need")
bullets([
    "Two Android devices running <b>Android 10 or newer</b>, or one "
    "Android device plus a desktop for testing.",
    "The install file <b>ghostwire-1.1.0-arm64-v8a-debug.apk</b>.",
    "A shared network (both on the same Wi-Fi), Bluetooth range — or "
    "the relay script on any computer both devices can reach (Chapter 9).",
    "A second channel for one short job: comparing fingerprint codes "
    "by voice or in person (Chapter 7).",
])
note("No accounts, no cloud",
     "GHOSTWIRE has no login, no contacts server and no message store. "
     "Your identity is a key created on first launch and kept only on "
     "your device. If you uninstall, that identity is gone — which is "
     "exactly the point.")

# ================================================== 2 · INSTALL & LAUNCH
chapter("2", "Installing and first launch")
h2("2.1&nbsp;&nbsp;Install the APK")
bullets([
    "Copy <b>ghostwire-1.1.0-arm64-v8a-debug.apk</b> to the phone "
    "(USB, Bluetooth file share, SD card, or a download link).",
    "Tap the file. If Android asks, allow <i>Install unknown apps</i> "
    "for the Files/Chrome app you are installing from — this is the "
    "normal sideload prompt, not a warning about GHOSTWIRE.",
    "Confirm <b>Install</b>. Because the app targets a modern Android "
    "release, you will <b>not</b> see the “built for an older version "
    "of Android” warning.",
    "Open GHOSTWIRE. Grant nothing yet — the app asks for permissions "
    "only when a feature needs them (network state always; Bluetooth "
    "only for the Bluetooth transport and only on Android 12+).",
])
h2("2.2&nbsp;&nbsp;First boot")
p("The app opens on an animated splash — radar sweep, live key-status "
  "line and the credits footer. Nothing is transmitted at boot: your "
  "identity keys are generated locally in those seconds and no network "
  "socket opens until you act. Tap anywhere to skip, or let it finish "
  "into the home screen.")
fig("m_splash", "First boot. Keys are generated locally; the network "
    "stays silent until you deploy a node or dial out.")

# ======================================================== 3 · HOME & ID
chapter("3", "Home screen and your identity")
p("Home is mission control. The top card is <b>NODE CONTROL</b> (your "
  "listening post — Chapter 4). Below it the <b>SITREP</b> panel reports "
  "live state, and three buttons lead to the uplink, sweep and security "
  "screens.")
fig("m_home", "Home screen with the node offline. SITREP shows link "
    "state, Bluetooth availability and your identity fingerprint.")
h2("3.1&nbsp;&nbsp;Reading the SITREP panel")
table(["Row", "Meaning"],
      [["LINK", "NO ACTIVE CHANNEL, or the live link plus the peer's "
        "fingerprint prefix."],
       ["BLUETOOTH RFCOMM", "Adapter state on this device — needed only "
        "for the Bluetooth transport."],
       ["IDENTITY", "Your permanent-on-this-install fingerprint. Peers "
        "use it to confirm they reached the real you (Chapter 7)."]],
      [42, 132])
h2("3.2&nbsp;&nbsp;Your identity")
p("The fingerprint (four groups, e.g. 5083 5101 7293 …) is the public "
  "face of a key created on first launch. It never leaves your device "
  "except inside encrypted handshakes and probe replies — and never "
  "while stealth is on. Reinstalling the app creates a fresh identity; "
  "tell your peer so they expect a new fingerprint.")
note("Write it down",
     "Before your first real conversation, read your fingerprint to "
     "your peer over a different channel (a call, in person). When the "
     "same code later appears on their verification screen, the "
     "man-in-the-middle is defeated.")

# ============================================================ 4 · NODE
chapter("4", "Deploying your node (receiving side)")
p("One of the two devices must listen before the other can call. That "
  "listener is your <b>node</b>. Fill in the two fields and tap "
  "<b>DEPLOY NODE</b>:")
bullets([
    "<b>BIND ADDR</b> — which network interface to listen on. "
    "0.0.0.0 means every interface (Wi-Fi and mobile data alike); use "
    "your Wi-Fi address (e.g. 192.168.1.20) to expose the node on one "
    "network only.",
    "<b>PORT</b> — the TCP port, 9999 unless you have a reason to move "
    "it. Your peer must dial the same port.",
])
p("The status line turns green — LISTENING — and the button becomes "
  "<b>STAND DOWN NODE</b>. Your node now answers reconnaissance probes "
  "with its fingerprint (unless stealth is on) and parks every real "
  "caller at your request gate (Chapter 6). It never calls anyone by "
  "itself.")
fig("m_node", "Node deployed and listening. The SITREP still shows no "
    "active channel — listening alone creates no connection.")
h2("4.1&nbsp;&nbsp;Standing down")
p("Tap <b>STAND DOWN NODE</b> to close the listener. Any live call is "
  "dropped and its keys discarded. Good fieldcraft: deploy only for "
  "the contact window, then stow — a silent phone cannot be probed.")
note("Two phones, two roles",
     "Only one side deploys a node per conversation. If both deploy, "
     "each can still dial the other — the first completed call wins. "
     "Over Bluetooth there is no node step at all: pairing happens "
     "entirely from the uplink screen.")

# ============================================================ 5 · SWEEP
chapter("5", "Finding peers — network sweep")
p("If both devices share a Wi-Fi network but you do not know your "
  "peer's address, sweep for it. Open <b>NETWORK SWEEP</b>, enter the "
  "range and port, and tap <b>INITIATE SWEEP</b>:")
bullets([
    "<b>TARGET RANGE</b> accepts CIDR (192.168.1.0/24) or a plain list "
    "(192.168.1.7, 192.168.1.20). Sweeps are capped at 1,024 hosts.",
    "<b>PORT</b> must match the node you are hunting (9999 default).",
    "<b>ABORT</b> stops a running sweep at any time.",
])
p("Each confirmed GHOSTWIRE node answers the probe with its identity "
  "fingerprint, and the sweep lists it as a tappable contact showing "
  "address + fingerprint. Tap the contact and the app carries the "
  "address straight into the uplink screen, ready to dial.")
fig("m_scan", "A finished sweep: one contact found. Tap it to designate "
    "it as your call target.")
h2("5.1&nbsp;&nbsp;What sweeps do — and do not — show")
bullets([
    "Only hosts that answer with a <b>valid GW1 fingerprint</b> are "
    "listed. Bare open ports are ignored, so stealth nodes (Chapter 8) "
    "stay invisible — by design, not by accident.",
    "Absence of a result proves nothing: the peer may be stealthed, "
    "firewalled, on another port, or simply not deployed yet. When in "
    "doubt, type the address directly.",
    "Sweeps are meaningless across the internet — for that, exchange "
    "the relay address out-of-band instead (Chapter 9).",
])

# =========================================================== 6 · UPLINK
chapter("6", "Calling out — establish uplink")
p("Open <b>ESTABLISH UPLINK</b>, check the target (or tap a sweep "
  "contact to fill it in), pick a transport, and tap <b>INITIATE "
  "HANDSHAKE</b>. The console narrates every phase of the cryptographic "
  "handshake; success ends in SECURE LINK ESTABLISHED with a session id "
  "and your peer's fingerprint, and the app jumps to the chat screen.")
fig("m_connect_wifi", "Uplink screen on the Wi-Fi/LAN transport, ready "
    "to dial.")
h2("6.1&nbsp;&nbsp;The three transports")
table(["Transport", "Target field means", "When to use it"],
      [["WIFI / LAN", "Hostname/IP + TCP port of the peer's node.",
        "Same network, or any routable address (VPN, public IP, port "
        "forward)."],
       ["BLUETOOTH", "Peer's Bluetooth address + RFCOMM channel (7).",
        "No network at all — same-room, zero infrastructure."],
       ["WAN RELAY", "Relay host + port both sides dial.",
        "Different networks / across the internet (Chapter 9)."]],
      [30, 62, 82])
h2("6.2&nbsp;&nbsp;Reading the handshake console")
p("The console is your flight recorder. A healthy call reads top to "
  "bottom like this: channel opening, ephemeral key generation, hello "
  "exchange, signature verification, key derivation, key confirmation "
  "— then SECURE LINK ESTABLISHED. If anything fails you get the exact "
  "reason (e.g. identity signature check failed) instead of a vague "
  "spinner — treat crypto errors as stop signs, never as retry hints.")
fig("m_handshake", "A completed handshake: every phase logged, session "
    "id issued, peer fingerprint shown.")
h2("6.3&nbsp;&nbsp;The DROP button")
p("DROP tears the link down and discards its keys. While a link is up, "
  "the app refuses a second call (“ALREADY LINKED // DROP FIRST”) — "
  "v1.1.0 is one conversation at a time, enforced in both directions.")

# ============================================================== 7 · GATE
chapter("7", "The request gate — acknowledge or reject")
p("Here is the heart of v1.1.0. When your node is deployed and someone "
  "dials you, <b>no encryption happens yet</b>. The caller is parked and "
  "your screen raises an <b>INBOUND REQUEST</b> naming them:")
fig("m_request", "The request gate. Nothing cryptographic has happened "
    "— the decision is entirely yours.")
bullets([
    "<b>ACKNOWLEDGE</b> — begin the GW1 handshake with this caller. If "
    "you already have a peer connected, they are dropped first, "
    "explicitly and visibly — never silently.",
    "<b>REJECT</b> — close the socket immediately. The caller learns "
    "nothing except that the call did not complete.",
    "<b>Ignore it</b> — the request expires on its own after 60 "
    "seconds and the socket closes.",
])
h2("7.1&nbsp;&nbsp;Why the gate exists")
p("Without it, any third device that found your address could dial in "
  "and knock your real peer off the node. With it, every connection is "
  "a conscious human decision. Coordinate contact windows with your "
  "peer in advance (“dial me at 2100”) so a request arriving at the "
  "right moment is expected — and one at 0300 gets REJECT.")
note("Bluetooth callers wait here too",
     "The Bluetooth node applies the identical gate with the caller's "
     "Bluetooth address shown. One policy everywhere: no anonymous "
     "hall passes.")

# ============================================================== 8 · CHAT
chapter("8", "Chatting on the secure channel")
p("The chat header names the endpoint and your peer's fingerprint; the "
  "green banner states the guarantees in force: AES-256-GCM "
  "end-to-end, ratcheted keys, burn after read. Type in "
  "<b>ENCRYPTED TRANSMISSION…</b> and hit send — every message is "
  "sealed with a fresh key before it leaves the phone.")
fig("m_chat", "A live conversation. Each bubble carries its own "
    "countdown and delivery state.")
h2("8.1&nbsp;&nbsp;Reading a bubble")
bullets([
    "<b>T-58s</b> — the fuse: seconds until this message deletes "
    "itself on <i>both</i> phones. It turns red under 3 seconds.",
    "<b>SENT // KEY ROTATED</b> — your message left and the next one "
    "will use new key material.",
    "<b>DECRYPTED // READING</b> — an incoming message, verified and "
    "displayed; its fuse is already running.",
    "<b>READ BY PEER // KEY ROTATED</b> — your peer's app confirmed "
    "display. <b>INCINERATED // PEER CONFIRMED</b> — both sides "
    "deleted it.",
])
h2("8.2&nbsp;&nbsp;Message-expiry timers")
p("The fire button at the left of the composer sets the fuse every new "
  "message carries. Tap it to cycle: <b>60s → 1.5m → 2m → 3m → 5m → "
  "back to 60s</b>. Sixty seconds is the default — short enough that a "
  "seized phone yields almost nothing, long enough to actually read. "
  "Raise it for coordinates and long texts, never out of habit.")
fig("m_chat_ttl", "Fuse set to 1.5 minutes. Every new message from here "
    "lives 90 seconds on both devices.")
h2("8.3&nbsp;&nbsp;Header buttons")
table(["Button", "Does"],
      [["shield-check", "Open fingerprint verification (Chapter 7's "
        "companion — do it once per session)."],
       ["delete-forever", "BURN: delete the whole conversation on both "
        "phones immediately."],
       ["power", "Disconnect this channel. Keys die with the link."]],
      [34, 140])
note("Messages live in memory only",
     "Nothing is written to storage — no database, no cache, no "
     "notification log to scrub. Leaving the chat, dropping the link, "
     "or killing the app all destroy the conversation.")

# =========================================================== 9 · VERIFY
chapter("9", "Verifying fingerprints (do this once per session)")
p("Encryption without authentication is just expensive whispering. The "
  "verification dialog shows your peer's full fingerprint — compare it "
  "against the code you exchanged <b>over a different channel</b> "
  "before trusting the conversation.")
fig("m_verify", "Identity verification. If these groups match the code "
    "your peer read to you, no one stands between you.")
bullets([
    "Open it any time from the chat header (shield-check).",
    "Read the groups aloud to each other by voice or video call — "
    "never inside the chat you are trying to verify.",
    "A mismatch means <b>stop</b>: wrong peer, stale identity after a "
    "reinstall, or active interference. Do not “retry and see”.",
    "Matching once per session is enough; the ratchet then vouches "
    "for every following message.",
])

# ============================================================ 10 · BURN
chapter("10", "Burning and disconnecting")
p("When the conversation is over — or at the first whiff of trouble — "
  "destroy it:")
bullets([
    "<b>delete-forever (BURN)</b> — incinerates every message on both "
    "devices and tells your peer's app to do the same. Bubbles flash "
    "INCINERATED // PEER CONFIRMED as each deletion is acknowledged.",
    "<b>power (disconnect)</b> — drops the encrypted link. The "
    "conversation widgets are cleared and the ratchet keys are thrown "
    "away; even a memory dump taken later cannot resurrect them.",
    "<b>DROP on the uplink screen</b> — same as power, available "
    "without opening the chat.",
])
p("After a disconnect the header reads LINK LOST and SITREP returns to "
  "NO ACTIVE CHANNEL. Reconnecting always runs a fresh handshake with "
  "fresh ephemeral keys — there is no “resume” that could replay an "
  "old session.")
note("Burn is a courtesy, not a proof",
     "BURN asks the peer's app to delete too, and an honest app always "
     "does. But no software can stop a determined peer photographing "
     "their screen. Send accordingly: timers bound exposure, they do "
     "not bound cameras.")

# ========================================================== 11 · SECURE
chapter("11", "Security Protocols screen")
p("The shield button on the home bar opens the transparency panel: "
  "everything the app claims about its own cryptography, on one "
  "scrollable screen. If any line ever disagrees with this manual, "
  "stop and investigate — the code is the spec.")
fig("m_security_top", "Cipher suite in force, live session id and peer "
    "fingerprint.")
h2("11.1&nbsp;&nbsp;GW1 cipher suite")
table(["Primitive", "Role"],
      [["X25519 ECDH (ephemeral)", "Each handshake derives fresh shared "
        "secrets; nothing long-term ever encrypts traffic."],
       ["Ed25519 mutual signatures", "Both hellos are signed — "
        "authentication runs both directions, no passwords, no PKI."],
       ["HKDF-SHA256 + symmetric ratchet", "Fresh message keys stepped "
        "per message; old state is erased (forward secrecy)."],
       ["AES-256-GCM (AEAD)", "Every frame encrypted and authenticated; "
        "tampering fails closed."],
       ["HMAC-SHA256 key confirm", "Both sides prove identical keys "
        "before the first message may flow."],
       ["Bilateral burn", "Coordinated deletion across both devices."]],
      [52, 122])
h2("11.2&nbsp;&nbsp;Standards & RFC references")
p("Scroll down for the panel that pins each primitive to its public "
  "standard — the same inventory auditors check against:")
fig("m_security_std", "Standards panel, active session card and stealth "
    "switch.")
table(["Standard", "Covers"],
      [["RFC 7748", "X25519 Diffie-Hellman."],
       ["RFC 8032", "Ed25519 signatures."],
       ["RFC 5869", "HKDF key derivation."],
       ["RFC 2104", "HMAC key confirmation."],
       ["NIST SP 800-38D", "AES-GCM authenticated encryption."],
       ["FIPS 180-4", "SHA-256 digest."]],
      [42, 132])
h2("11.3&nbsp;&nbsp;Active session & local node cards")
p("ACTIVE SESSION shows the live session id and peer fingerprint for "
  "read-back comparison; LOCAL NODE repeats your own fingerprint and "
  "holds the <b>stealth switch</b>. The green FIELD NOTE at the bottom "
  "is the developers' honesty box: confidentiality, integrity, mutual "
  "authentication, forward secrecy, transience — and the reminder that "
  "your device remains the weakest link.")

# ========================================================== 12 · STEALTH
chapter("12", "Stealth mode")
p("Flip the stealth switch (Security Protocols → LOCAL NODE) and your "
  "deployed node goes silent to sweeps: reconnaissance probes are "
  "swallowed without a reply, so the node never appears in anyone's "
  "contact list — including the sweep screen in this very app, which "
  "deliberately lists only confirmed GW1 answers.")
bullets([
    "<b>What stealth hides:</b> your fingerprint, your presence as a "
    "GHOSTWIRE node, and any protocol banner.",
    "<b>What stealth does not hide:</b> the bare fact that <i>something</i> "
    "listens on that TCP port. A raw port scanner still sees an open "
    "port; move off 9999 and firewall-restrict where you can.",
    "<b>What keeps working:</b> everything else. Peers who know your "
    "address connect normally, the request gate still guards every "
    "call, and handshakes are unaffected.",
])
note("Stealth pairs with pre-arranged addresses",
     "A stealthed node cannot be discovered — only dialled. That is "
     "the intended combination: swap addresses and fingerprints over "
     "your out-of-band channel, then run silent.")

# ============================================================ 13 · RELAY
chapter("13", "Chatting across the internet — the WAN relay")
p("Two devices on different networks cannot dial each other directly. "
  "For that, v1.1.0 ships <b>relay_server.py</b>: a tiny script you run "
  "on any computer both phones can reach (a VPS, a home server, a "
  "laptop on a public address). Both sides dial the relay with the "
  "<b>WAN RELAY</b> transport — and the relay introduces them without "
  "ever being able to read a word.")
fig("m_connect_relay", "Uplink screen on the WAN RELAY transport, "
    "pointed at the operator's relay.")
h2("13.1&nbsp;&nbsp;Running the relay (5 minutes, once)")
bullets([
    "Copy <b>relay_server.py</b> to the server machine. It needs only "
    "Python 3 — no packages, no root, no configuration files.",
    "Start it: <b>python3 relay_server.py --host 0.0.0.0 --port "
    "9999</b>. Open that TCP port in the machine's firewall.",
    "Tell both operators the relay's address and port over your "
    "out-of-band channel, exactly like a fingerprint.",
    "Both phones: uplink screen → <b>WAN RELAY</b> → enter relay host "
    "and port → <b>INITIATE HANDSHAKE</b>.",
])
h2("13.2&nbsp;&nbsp;What happens on dial")
bullets([
    "The first phone to arrive is <i>parked</i>; the console says it "
    "is waiting for a peer (up to 2 minutes).",
    "When the second phone dials, the relay pairs them: first arrival "
    "takes the GW1 server seat, second the client seat.",
    "From there the ordinary GW1 handshake runs <i>through</i> the "
    "pipe — keys are derived end-to-end by the two phones. The relay "
    "shuttles bytes it cannot decrypt, then tears the pairing down "
    "when either side hangs up.",
])
h2("13.3&nbsp;&nbsp;Why the relay cannot spy on you")
bullets([
    "It performs <b>no GW1 parsing and holds no keys</b> — hellos, "
    "confirmations and every message cross it as opaque ciphertext.",
    "It sees only metadata: who dialled, when, and how many bytes "
    "moved. Run your own relay and even that stays in your hands.",
    "Reconnaissance probes sent to it are closed silently — it has no "
    "identity to reveal, because it has none.",
])
mono_block(["$ python3 relay_server.py --host 0.0.0.0 --port 9999",
            "[relay] listening on 0.0.0.0:9999 (max 16 concurrent pairs)",
            "[relay] 197.232.61.9:51244 parked, waiting for peer",
            "[relay] pairing 41.90.63.200:38810 with established peer",
            "[relay] pair 41.90.63.200:38810 closed after 18411 bytes one-way"])
note("One relay, many pairs",
     "A single relay hosts up to 16 simultaneous pairs by default "
     "(--max-pairs). Each pair is isolated: bytes from one conversation "
     "can never leak into another.")

# ===================================================== 14 · TROUBLESHOOT
chapter("14", "Troubleshooting")
p("The handshake console always prints the precise failure class. Find "
  "yours below:")
table(["Symptom", "Likely cause", "What to do"],
      [["REQUEST EXPIRED / call times out at the gate", "Peer never "
        "tapped ACKNOWLEDGE within 60 s.",
        "Coordinate the window first; then re-dial. Never loop redial."],
       ["CONNECTION REJECTED", "Peer tapped REJECT — or a stranger "
        "probed you and you rejected them.",
        "Expected behaviour. Arrange the call out-of-band."],
       ["HANDSHAKE REJECTED (SecurityError)", "Tampered/replayed hello, "
        "version mismatch, role confusion.",
        "Do not retry blindly. Verify addresses and fingerprints."],
       ["identity signature check failed", "Wrong/stale peer key or "
        "substitution on the path.",
        "Compare fingerprints; abort if they differ."],
       ["key confirmation MAC mismatch", "Ends derived different keys.",
        "Abort and treat as an attack until proven otherwise."],
       ["Nothing found in SWEEP", "Stealth node, firewall, wrong port, "
        "or node not deployed.",
        "Dial the address directly; confirm port and deploy state."],
       ["ALREADY LINKED // DROP FIRST", "A link is already up.",
        "Finish or DROP the current call first — one at a time."],
       ["Relay dial waits forever", "Partner never dialled, or wrong "
        "relay address/port.",
        "Confirm both sides use the same relay; check the relay log."],
       ["Bluetooth failure", "No adapter, out of range, wrong address.",
        "Check SITREP adapter line, range (<10 m), re-enter BD_ADDR."]],
      [52, 58, 64])
note("Crypto errors are stop signs",
     "Anything containing SecurityError, signature, MAC or confirm "
     "means the mathematics refused — the app is protecting you. The "
     "correct response is out-of-band verification, never hammering "
     "INITIATE HANDSHAKE.")

# ==================================================== 15 · FIELD HABITS
chapter("15", "Field habits — the one-page doctrine")
h2("15.1&nbsp;&nbsp;Before every real conversation")
bullets([
    "☐ &nbsp;Fingerprints exchanged over an independent channel.",
    "☐ &nbsp;Contact window agreed (“dial me at 2100, port 9999”).",
    "☐ &nbsp;Node deployed only for the window (or relay confirmed up).",
    "☐ &nbsp;Stealth ON if discovery must fail.",
])
h2("15.2&nbsp;&nbsp;During")
bullets([
    "☐ &nbsp;ACKNOWLEDGE only the expected caller; REJECT the rest.",
    "☐ &nbsp;Verify fingerprints in-app against the exchanged codes.",
    "☐ &nbsp;Keep the fuse short (60 s default); raise it per message, "
    "not per habit.",
    "☐ &nbsp;Read the session id back verbally once; both ends match.",
])
h2("15.3&nbsp;&nbsp;After")
bullets([
    "☐ &nbsp;BURN the conversation on both ends.",
    "☐ &nbsp;Disconnect, then STAND DOWN the node.",
    "☐ &nbsp;New install anywhere → new identity → re-verify next time.",
])
h2("15.4&nbsp;&nbsp;Never")
bullets([
    "Never verify a fingerprint inside the chat being verified.",
    "Never retry a crypto error without an out-of-band check.",
    "Never trust a relay you do not control with your metadata — run "
    "your own; it is one file.",
    "Never assume a timer defeats a camera. Send accordingly.",
])
story.append(Spacer(1, 10 * mm))
p("End of manual. Stay silent, stay verified — <b>developed by @Ariko "
  "& Arena</b>.")

# ================================================================= BUILD
doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm,
                      rightMargin=18 * mm, topMargin=18 * mm,
                      bottomMargin=20 * mm, title="GHOSTWIRE Operator's Manual v1.1.0",
                      author="@Ariko & Arena")
_main_frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width,
                    doc.height, id="main")
_cover_frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width,
                     doc.height, id="cover")
doc.addPageTemplates([
    PageTemplate(id="cover", frames=[_cover_frame], onPage=cover_footer),
    PageTemplate(id="main", frames=[_main_frame], onPage=footer),
])


def _after_flowable(flowable):
    # Chapter-level TOC only: subsection rows would force a split page.
    if isinstance(flowable, Paragraph):
        if flowable.style.name == "h1":
            doc.notify("TOCEntry", (0, flowable.getPlainText(), doc.page))


doc.afterFlowable = _after_flowable
doc.multiBuild(story)

from pypdf import PdfReader  # noqa: E402
pages = len(PdfReader(OUT).pages)
print(f"MANUAL BUILT: {OUT} pages: {pages}")
if pages > MAX_PAGES:
    raise SystemExit(f"PAGE BUDGET EXCEEDED: {pages} > {MAX_PAGES}")

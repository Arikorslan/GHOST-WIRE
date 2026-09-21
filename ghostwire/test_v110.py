"""GHOSTWIRE v1.1.0 integration test.

Covers the full v1.1.0 revision set:
  1. peer-to-peer single-link model (no multi-session registry)
  2. operator request gate  (<ip:port> REQUESTS A CHAT, ACK/REJECT,
     60 s expiry window, ack-while-busy displaces the old peer only
     with an explicit decision)
  3. TTL presets: default 60 s, cycle 1.5m / 2m / 3m / 5m
  4. stealth mode: sweeps list only confirmed GW1 nodes
  5. WAN relay round-trip through the opaque relay_server.Relay
  6. version string

Pure-network checks run first; then the real GhostwireApp boots under
Xvfb (GW_DEMO skips the splash and auto-acknowledges gate dialogs).

Run:  xvfb-run -a -s "-screen 0 460x780x24" python3 test_v110.py
"""
import os
import socket
import sys
import threading
import time

os.environ["GW_DEMO"] = "1"
os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_WINDOW"] = "x11"
os.environ["KIVY_METRICS_DENSITY"] = "1"

from kivy.config import Config           # noqa: E402
Config.set("graphics", "width", "460")
Config.set("graphics", "height", "780")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kivy.clock import Clock                          # noqa: E402
import gw as gw_pkg                                   # noqa: E402
from gw.ui import GhostwireApp                        # noqa: E402
from gw.crypto import Identity                        # noqa: E402
from gw.net import SecureLink, NodeServer, relay_connect  # noqa: E402
from relay_server import Relay                        # noqa: E402

FAILS = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        FAILS.append(name)


class Remote:
    """An external GW1 device dialing a node."""

    def __init__(self, host, port, timeout=10):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.link = SecureLink(self.sock, Identity(), "client")
        self.link.handshake_client()
        self.received = []
        self.link.on_message = lambda o: self.received.append(o)
        self.link.start()

    def wait_close(self, seconds=3.0):
        deadline = time.time() + seconds
        while time.time() < deadline:
            if not self.link.alive:
                return True
            time.sleep(0.05)
        return not self.link.alive


def gate_responder(delay, ok):
    def cb(label, gate_id):
        def decide():
            time.sleep(delay)
            srv_done[gate_id] = ok
        threading.Thread(target=decide, daemon=True).start()
    return cb


srv_done = {}

# ----------------------------------------------------------------------
print("== [1] request gate: expiry ==")
srv1 = NodeServer(Identity())
srv1.REQUEST_TIMEOUT = 0.7          # instance attr shrinks the window
reqs1 = []
srv1.on_request = lambda label, gid: reqs1.append((label, gid))
srv1.start("127.0.0.1", 41001)
s = socket.create_connection(("127.0.0.1", 41001), timeout=5)
s.settimeout(5)
s.sendall(b"\x00\x01")              # non-probe byte reaches the gate
t0 = time.time()
try:
    data = s.recv(16)
except (ConnectionResetError, OSError):
    data = b""                      # reset == server cut the socket
elapsed = time.time() - t0
check("gate fires on_request", len(reqs1) == 1 and ":" in reqs1[0][0])
check("unanswered request expires and closes socket",
      data == b"" and elapsed >= 0.5)
srv1.stop()

print("== [2] request gate: explicit REJECT ==")
srv2 = NodeServer(Identity())
requests2 = []


def rejecter(label, gid):
    requests2.append((label, gid))
    threading.Thread(
        target=lambda: (time.sleep(0.15), srv2.respond(gid, False)),
        daemon=True).start()


srv2.on_request = rejecter
srv2.start("127.0.0.1", 41002)
s = socket.create_connection(("127.0.0.1", 41002), timeout=5)
s.settimeout(5)
s.sendall(b"\x00\x01")
try:
    data = s.recv(16)
except (ConnectionResetError, OSError):
    data = b""
check("rejected request closes before handshake", data == b"")
check("reject dialog fired", len(requests2) == 1)
srv2.stop()

print("== [3] request gate: ACKNOWLEDGE completes handshake ==")
srv3 = NodeServer(Identity())
srv3_handshakes = []
srv3.on_link = lambda link, addr: srv3_handshakes.append((link, addr))
srv3.on_request = lambda label, gid: threading.Thread(
    target=lambda: (time.sleep(0.1), srv3.respond(gid, True)),
    daemon=True).start()
srv3.start("127.0.0.1", 41003)
ra = Remote("127.0.0.1", 41003)
time.sleep(0.5)
check("acknowledged request completes GW1 handshake",
      len(srv3_handshakes) == 1)
srv3_link = srv3_handshakes[0][0]
got = []
srv3_link.on_message = lambda o: got.append(o)
ra.link.send_chat("ping through gate", 60)
time.sleep(0.7)
check("traffic flows after acknowledge",
      any(o.get("text") == "ping through gate" for o in got))

print("== [4] single peer: ack-while-busy displaces old client ==")
check("old peer still alive before second request", ra.link.alive)
rb = Remote("127.0.0.1", 41003)
time.sleep(0.8)
check("acknowledging a new client drops the previous one",
      ra.wait_close())
check("new client holds the only live link", rb.link.alive)
check("exactly one link hosted",
      srv3.link is not None and srv3.link.session_id ==
      rb.link.session_id)
srv3.stop()
rb.link.close()

print("== [5] stealth mode ==")
st = NodeServer(Identity())
st.start("127.0.0.1", 41004)
time.sleep(0.2)
res_loud = None
for _ in range(20):
    from gw.net import probe_host
    res_loud = probe_host("127.0.0.1", 41004)
    if res_loud:
        break
    time.sleep(0.1)
check("visible node answers probes with identity",
      res_loud is not None and res_loud[0] == "node" and res_loud[1])
st.stealth = True
res_stealth = probe_host("127.0.0.1", 41004)
check("stealth node swallows probes (no identity)",
      res_stealth is not None and res_stealth[0] == "open")
# stealth must not break real handshakes
st.on_request = lambda label, gid: threading.Thread(
    target=lambda: (time.sleep(0.05), st.respond(gid, True)),
    daemon=True).start()
rc = Remote("127.0.0.1", 41004)
check("stealth node still accepts acknowledged handshakes", rc.link.alive)
st.stop()
rc.link.close()

print("== [6] WAN relay round-trip ==")
relay = Relay("127.0.0.1", 0, quiet=True)
relay.start_background()
time.sleep(0.3)
rp = relay.port
id_a, id_b = Identity(), Identity()
links = {}
errs = []


def dial(name, ident):
    try:
        links[name] = relay_connect(ident, "127.0.0.1", rp,
                                    status=lambda m: None)
    except Exception as e:  # noqa: BLE001
        errs.append((name, repr(e)))


ta = threading.Thread(target=dial, args=("A", id_a), daemon=True)
tb = threading.Thread(target=dial, args=("B", id_b), daemon=True)
ta.start()
time.sleep(0.6)            # A parks at the relay first
tb.start()
ta.join(20)
tb.join(20)
check("relay handshake completes for both seats",
      not errs and len(links) == 2,
      )
if errs:
    print("   relay errors:", errs)
if len(links) == 2:
    la, lb = links["A"], links["B"]
    check("relay assigns server/client seats",
          la.role != lb.role)
    got_b = []
    lb.on_message = lambda o: got_b.append(o)
    lb.start()
    la.send_chat("across the wan", 120)
    time.sleep(0.8)
    check("message crosses relay end-to-end",
          any(o.get("text") == "across the wan" for o in got_b))
    check("relay never alters ciphertext identity",
          la.peer_fingerprint == id_b.fingerprint and
          lb.peer_fingerprint == id_a.fingerprint)
    la.close()
    lb.close()
# probes to the relay get silence
sp = socket.create_connection(("127.0.0.1", rp), timeout=4)
sp.settimeout(4)
sp.sendall(b"GW1PROBE")
try:
    d = sp.recv(16)
except OSError:
    d = b""
check("relay closes reconnaissance probes silently", d == b"")
relay.stop()

# ----------------------------------------------------------------------
print("== [7] UI boot: ttl, sweep filter, gate, single link ==")
app = GhostwireApp()
STATE = {}


def drive(dt):
    try:
        a = app
        if dt < 0.5:
            return
        if "ttl" not in STATE:
            STATE["ttl"] = 1
            check("version is 1.1.0", gw_pkg.__version__ == "1.1.0")
            check("ttl presets are 60/90/120/180/300",
                  a.ttl_options == [60, 90, 120, 180, 300])
            check("ttl default is 60 s", a.ttl == 60 and a.ttl_idx == 0)
            check("ttl button shows 60s", a.ttl_btn.text == "60s")
            seq = []
            for _ in range(5):
                a.cycle_ttl()
                seq.append(a.ttl_btn.text)
            check("ttl cycle labels 1.5m/2m/3m/5m/60s",
                  seq == ["1.5m", "2m", "3m", "5m", "60s"])
            check("no multi-session machinery left",
                  not hasattr(a, "sessions") and
                  not hasattr(a, "active_sid"))
            a.bind_host_field.text = "127.0.0.1"
            a.bind_port_field.text = "41010"
            a.deploy_node()
            Clock.schedule_once(drive, 0.8)
        elif "remote" not in STATE:
            STATE["remote"] = Remote("127.0.0.1", 41010)
            Clock.schedule_once(drive, 2.2)
        elif "gate" not in STATE:
            STATE["gate"] = 1
            check("GW_DEMO auto-ack links the inbound client",
                  a.link is not None and a.link.alive)
            check("chat header shows inbound endpoint",
                  "INBOUND" in a.chat_endpoint.text)
            STATE["remote"].link.send_chat("operator sees this", 60)
            Clock.schedule_once(drive, 1.2)
        elif "chat" not in STATE:
            STATE["chat"] = 1
            check("inbound message rendered in chat",
                  len(a.rows) == 1)
            a.msg_field.text = "ack channel test"
            a.send_msg()
            Clock.schedule_once(drive, 1.0)
        elif "chat2" not in STATE:
            STATE["chat2"] = 1
            check("outbound message reached the peer",
                  any(o.get("text") == "ack channel test"
                      for o in STATE["remote"].received))
            # single-link guard: a second uplink while linked is refused
            a.host_field.text = "127.0.0.1"
            a.port_field.text = "41010"
            a.do_connect()          # guard is synchronous -> no job spawns
            check("single link rejects a second uplink",
                  a.connect_btn.disabled is False and a.link is not None
                  and a.link.alive)
            # stealth: sweep must ignore open-port hits
            before = len(a.scan_results.children)
            a._sweep_hit("10.0.0.9", "open", None)
            check("sweep ignores open ports (stealth fix)",
                  len(a.scan_results.children) == before)
            a._sweep_hit("10.0.0.9", "node", "abcd ef01")
            check("sweep lists confirmed GW1 nodes",
                  len(a.scan_results.children) == before + 1)
            Clock.schedule_once(drive, 0.8)   # >= 0.5: drive's early-guard
        elif "replace" not in STATE:
            STATE["replace"] = 1
            STATE["remote2"] = Remote("127.0.0.1", 41010)
            Clock.schedule_once(drive, 2.2)
        elif "replace2" not in STATE:
            STATE["replace2"] = 1
            check("acknowledged newcomer displaces the old peer only",
                  STATE["remote"].wait_close())
            check("app follows the new peer",
                  a.link is not None and a.link.alive and
                  a.link.session_id ==
                  STATE["remote2"].link.session_id)
            a.undeploy_node()
            Clock.schedule_once(lambda dt: a.stop(), 0.3)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        FAILS.append("exception: %r" % e)
        app.stop()


Clock.schedule_once(drive, 0.4)
app.run()

print("RESULT:", "OK" if not FAILS else f"FAILED {FAILS}")
sys.exit(1 if FAILS else 0)

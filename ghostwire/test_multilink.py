"""Headless UI integration test: multi-session hosting.

Runs the real GhostwireApp under Xvfb (GW_DEMO skips the splash),
deploys the in-app node, attaches THREE remote inbound clients, and
opens ONE outbound uplink to a separate headless node.  Asserts the
session registry, chips, SITREP, switching, per-peer routing, unread
badges, and teardown.
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
from gw.ui import GhostwireApp                        # noqa: E402
from gw.crypto import Identity                        # noqa: E402
from gw.net import SecureLink, NodeServer             # noqa: E402

FAILS = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        FAILS.append(name)


class Remote:
    """External GW1 client device connecting to a node."""

    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port), timeout=6)
        self.link = SecureLink(self.sock, Identity(), "client")
        self.link.handshake_client()
        self.received = []
        self.link.on_message = lambda o: self.received.append(o)
        self.link.start()


# A separate headless node the app will dial OUT to (so the outbound
# path is exercised without self-connect double-counting).
ext_node = NodeServer(Identity())
ext_node.start("127.0.0.1", 39999)

app = GhostwireApp()
STATE = {}


def drive(dt):
    try:
        a = app
        if dt < 0.5:
            return
        if "node" not in STATE:
            STATE["node"] = 1
            a.bind_host_field.text = "127.0.0.1"
            a.bind_port_field.text = "29999"
            a.deploy_node()
            Clock.schedule_once(drive, 1.0)
        elif "remotes" not in STATE:
            STATE["remotes"] = [Remote("127.0.0.1", 29999) for _ in range(3)]
            Clock.schedule_once(drive, 1.6)
        elif "uplink" not in STATE:
            STATE["uplink"] = 1
            a.host_field.text = "127.0.0.1"
            a.port_field.text = "39999"
            a.do_connect()
            Clock.schedule_once(drive, 3.0)
        elif "assert1" not in STATE:
            STATE["assert1"] = 1
            check("four sessions registered (3 IN + 1 OUT)",
                  len(a.sessions) == 4)
            check("four chips rendered",
                  len(a.session_strip.children) == 4)
            check("sitrep counts links",
                  a.link_row.lbl.text.startswith("LINKS // 4 ACTIVE"))
            check("active session chosen", a.active_sid in a.sessions)
            # Pick an INBOUND session for remote-0 and force it to be
            # the NON-active one so we can test background delivery.
            r0_sid = STATE["remotes"][0].link.session_id
            check("remote-0 session is hosted", r0_sid in a.sessions)
            if a.active_sid == r0_sid:
                other = [s for s in a.sessions if s != r0_sid][0]
                a.switch_session(other)
            STATE["r0_sid"] = r0_sid
            STATE["remotes"][0].link.send_chat("background ping", 10)
            Clock.schedule_once(drive, 1.0)
        elif "assert2" not in STATE:
            STATE["assert2"] = 1
            r0_sid = STATE["r0_sid"]
            sess0 = a.sessions.get(r0_sid)
            check("background session got the message",
                  sess0 is not None and len(sess0.rows) == 1 and
                  any(r.bubble.body.text == "background ping"
                      for r in sess0.rows.values()))
            check("unread counter incremented",
                  sess0 is not None and sess0.unread == 1)
            check("chip shows unread badge",
                  sess0 is not None and sess0.chip and
                  "+1" in sess0.chip.lbl.text)
            a.switch_session(r0_sid)
            a.msg_field.text = "multi-link test"
            a.send_msg()
            Clock.schedule_once(drive, 1.0)
        elif "assert3" not in STATE:
            STATE["assert3"] = 1
            r0_sid = STATE["r0_sid"]
            sess0 = a.sessions.get(r0_sid)
            check("switch updates active", a.active_sid == r0_sid)
            check("switch updates header",
                  sess0 is not None and
                  a.chat_endpoint.text == sess0.endpoint)
            check("switch updates security panel",
                  sess0 is not None and sess0.sid in a.sec_session_id.text)
            check("unread cleared on switch",
                  sess0 is not None and sess0.unread == 0)
            hits = []
            for r in STATE["remotes"]:
                hits += [o for o in r.received
                         if o.get("text") == "multi-link test"]
            check("message delivered to exactly the right peer",
                  len(hits) == 1)
            check("outbound session still alive alongside hosted ones",
                  any(s.direction == "OUT" for s in a.sessions.values()))
            a.disconnect_all()
            Clock.schedule_once(drive, 1.2)
        else:
            check("disconnect_all clears registry", len(a.sessions) == 0)
            check("chips removed", len(a.session_strip.children) == 0)
            check("sitrep resets",
                  a.link_row.lbl.text == "LINK // NO ACTIVE CHANNEL")
            a.undeploy_node()
            ext_node.stop()
            Clock.schedule_once(lambda dt: a.stop(), 0.2)
    except Exception as e:
        import traceback
        traceback.print_exc()
        FAILS.append("exception: %r" % e)
        app.stop()


Clock.schedule_once(drive, 0.4)
app.run()

print("RESULT:", "OK" if not FAILS else f"FAILED {FAILS}")
sys.exit(1 if FAILS else 0)

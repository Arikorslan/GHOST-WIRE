"""Capture GHOSTWIRE v1.1.0 manual screenshots from the real app.

Run:  xvfb-run -a -s "-screen 0 460x780x24" python3 manual/capture.py
Phase 1 runs with GW_DEMO=1 (skips splash, auto-acks gate); phase 2
re-execs without it for the splash shot.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

PHASE = os.environ.get("CAP_PHASE", "1")

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_WINDOW"] = "sdl2"
os.environ["KIVY_METRICS_DENSITY"] = "1"
if PHASE == "1":
    os.environ["GW_DEMO"] = "1"

from kivy.config import Config           # noqa: E402
Config.set("graphics", "width", "400")
Config.set("graphics", "height", "720")

sys.path.insert(0, os.path.dirname(HERE))

from kivy.clock import Clock                          # noqa: E402
from kivy.core.window import Window                   # noqa: E402
from kivy.uix.modalview import ModalView              # noqa: E402
from kivy.uix.scrollview import ScrollView            # noqa: E402
from gw.ui import GhostwireApp                        # noqa: E402
from gw.crypto import Identity                        # noqa: E402
from gw.net import NodeServer                         # noqa: E402


def shot(app, name, window=False):
    path = os.path.join(OUT, name + ".png")
    if window:
        # Dialogs live on the Window, not in app.root - a widget
        # export would miss them. Window.screenshot captures all.
        Window.screenshot(path)
    else:
        app.root.export_to_png(path)
    print("SHOT", path, flush=True)


def dismiss_dialogs():
    for w in list(Window.children):
        if isinstance(w, ModalView):
            w.dismiss()


if PHASE == "2":
    app = GhostwireApp()
    Clock.schedule_once(lambda dt: shot(app, "m_splash"), 1.6)
    Clock.schedule_once(lambda dt: app.stop(), 2.2)
    app.run()
    sys.exit(0)

# ---------------- phase 1 ----------------
app = GhostwireApp()
helper = {"srv": None, "link": None}


def start_helper():
    srv = NodeServer(Identity())

    def ack(label, gid):
        srv.respond(gid, True)

    def on_link(link, addr):
        helper["link"] = link

        def on_msg(o):
            if o.get("t") == "msg":
                link.send_chat("Solid copy, Overwatch. Channel is hot — "
                               "AES-256-GCM confirmed both ends.", 60)

        link.on_message = on_msg

    srv.on_request = ack
    srv.on_link = on_link
    srv.start("127.0.0.1", 42102)
    helper["srv"] = srv


def find_scroll(screen):
    for w in screen.walk():
        if isinstance(w, ScrollView):
            return w
    return None


def drive(dt):
    at = lambda d, f, *a: Clock.schedule_once(lambda t: f(*a), d)

    at(0.6, shot, app, "m_home")

    def deploy():
        app.bind_host_field.text = "127.0.0.1"
        app.bind_port_field.text = "42101"
        app.deploy_node()
    at(1.0, deploy)
    at(1.8, shot, app, "m_node")

    def sweep():
        app.goto("scan")
        app.target_field.text = "127.0.0.1/30"
        app.scan_port_field.text = "42101"
        app.start_sweep()
    at(2.2, sweep)
    at(6.0, shot, app, "m_scan")

    def connect_wifi():
        app.goto("connect")
    at(6.4, connect_wifi)
    at(7.0, shot, app, "m_connect_wifi")

    def relay_view():
        app._pick_transport("relay")
        app.host_field.text = "relay.example.com"
        app.port_field.text = "9999"
    at(7.4, relay_view)
    at(8.0, shot, app, "m_connect_relay")

    def dial():
        app._pick_transport("wifi")
        app.host_field.text = "127.0.0.1"
        app.port_field.text = "42102"
        start_helper()
        app.do_connect()
    at(8.4, dial)
    # link_up auto-jumps to chat 2.5 s after the handshake lands,
    # so shoot the console early while firmly on connect screen.
    at(10.4, shot, app, "m_handshake")

    def chat():
        app.goto("chat")
        app.msg_field.text = "Spectre-6, Overwatch. Comms check, over."
        app.send_msg()
    at(12.0, chat)

    def chat2():
        app.msg_field.text = "Confirm fingerprint before classified traffic."
        app.send_msg()
    at(13.2, chat2)
    at(15.0, shot, app, "m_chat")

    def ttl():
        app.cycle_ttl()
    at(15.4, ttl)
    at(16.0, shot, app, "m_chat_ttl")

    def verify():
        app.verify_dialog()
    at(16.4, verify)
    at(17.0, shot, app, "m_verify", True)
    at(17.4, dismiss_dialogs)

    def security():
        app.goto("security")
    at(17.8, security)
    at(18.6, shot, app, "m_security_top")

    def scroll_std():
        sv = find_scroll(app.sm.get_screen("security"))
        if sv:
            sv.scroll_y = 0.42
    at(19.0, scroll_std)
    at(19.6, shot, app, "m_security_std")

    def request_dialog():
        app.goto("home")
        had = os.environ.pop("GW_DEMO", None)
        app.on_inbound_request("192.168.1.42:51820", 424242)
        if had is not None:
            os.environ["GW_DEMO"] = had
    at(20.0, request_dialog)
    at(20.8, shot, app, "m_request", True)
    at(21.2, dismiss_dialogs)

    def done():
        try:
            app.undeploy_node()
        except Exception:
            pass
        if helper["srv"]:
            helper["srv"].stop()
        app.stop()
    at(21.8, done)


Clock.schedule_once(drive, 0.3)
app.run()
print("PHASE1 DONE", flush=True)

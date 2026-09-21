"""GHOSTWIRE — tactical encrypted messenger.

Run normally:           python3 main.py
Demo automation:        GW_DEMO=server|client python3 main.py
"""

import os

os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "400")
Config.set("graphics", "height", "720")
Config.set("kivy", "log_level", "warning")

from kivy.clock import Clock  # noqa: E402

from gw.ui import GhostwireApp  # noqa: E402

SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")


def shot(app, name):
    os.makedirs(SHOTS, exist_ok=True)
    path = os.path.join(SHOTS, f"{name}.png")
    app.root.export_to_png(path)
    print(f"[DEMO] screenshot -> {path}", flush=True)


# ------------------------------------------------------------------ demo
CANNED_REPLIES = [
    "Overwatch, Spectre-6 reads you five by five. Link is hot - "
    "AES-256-GCM confirmed on both ends. Over.",
    "Copy. Fingerprint cross-checked on secondary channel. Identity "
    "verified. Channel trusted. Over.",
    "Package inbound. Grid coordinates encrypted end to end. "
    "Burn after reading. Over.",
    "Spectre-6 going dark after this packet. Keys are rotating. Over.",
]

CANNED_SENDS = [
    "Spectre-6, this is Overwatch. Comms check on the secure channel. Over.",
    "Confirm key fingerprint before we move classified traffic. Over.",
    "Clock is live on every packet. Self-destruct in ten seconds.",
]


def script_client(app):
    at = lambda d, f, *a: Clock.schedule_once(lambda dt: f(*a), d)

    at(1.0, shot, app, "01_home")

    def open_sweep():
        app.goto("scan")
        app.target_field.text = "127.0.0.1/29"
        app.scan_port_field.text = "9999"
        app.start_sweep()
    at(1.7, open_sweep)
    at(4.8, shot, app, "02_network_sweep")

    def open_connect():
        app.goto("connect")
        app.host_field.text = "127.0.0.1"
        app.port_field.text = "9999"
    at(5.6, open_connect)
    at(6.3, app.do_connect)
    at(8.1, shot, app, "03_handshake")

    def send(i):
        app.msg_field.text = CANNED_SENDS[i]
        app.send_msg()
    at(9.3, send, 0)
    at(10.4, send, 1)
    at(11.5, send, 2)

    at(14.2, shot, app, "04_chat")

    at(15.2, lambda: app.goto("security"))
    at(16.0, shot, app, "05_security")
    at(18.0, app.stop)


def script_server(app):
    at = lambda d, f, *a: Clock.schedule_once(lambda dt: f(*a), d)

    def deploy():
        app.bind_host_field.text = "127.0.0.1"
        app.bind_port_field.text = "9999"
        app.deploy_node()
    at(0.5, deploy)
    at(2.4, shot, app, "01_node_deployed")

    replies = iter(CANNED_REPLIES)

    def auto_reply(text):
        try:
            reply = next(replies)
        except StopIteration:
            return

        def fire():
            app.msg_field.text = reply
            app.send_msg()
        Clock.schedule_once(lambda dt: fire(), 0.8)
    app.demo_hook_chat = auto_reply

    at(20.5, shot, app, "04b_chat_server")
    at(28, app.stop)


def _android_soft_input_resize():
    """Shrink the app window while the soft keyboard is visible so text
    fields (chat composer, host/port inputs) are never covered by it.
    No-op on desktop."""
    from kivy.utils import platform
    if platform != "android":
        return
    try:
        from jnius import autoclass
        WindowManager = autoclass("android.view.WindowManager$LayoutParams")
        ColorDrawable = autoclass("android.graphics.drawable.ColorDrawable")
        AColor = autoclass("android.graphics.Color")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        win = activity.getWindow()
        # adjustPan (not adjustResize): panning translates the window
        # instead of resizing the GL surface, so no frame flash/flicker
        # when the keyboard opens. Kivy reports the focused field's
        # position (Window.softinput_mode = 'below_target') so Android
        # pans exactly enough to keep it visible.
        win.setSoftInputMode(WindowManager.SOFT_INPUT_ADJUST_PAN)
        # Dark window background: while the soft keyboard resizes the
        # window the GL surface lags a frame or two; without this the
        # exposed area flashes the default (white) window background.
        win.setBackgroundDrawable(
            ColorDrawable(AColor.parseColor("#0B0E0B")))
    except Exception as exc:  # never let this break startup
        print(f"[WARN] soft input mode not applied: {exc}", flush=True)


def main():
    _android_soft_input_resize()
    app = GhostwireApp()
    app.bind(on_start=lambda *_: _android_soft_input_resize())
    demo = os.environ.get("GW_DEMO", "")
    if demo == "client":
        Clock.schedule_once(lambda dt: script_client(app), 0)
    elif demo == "server":
        Clock.schedule_once(lambda dt: script_server(app), 0)
    app.run()


if __name__ == "__main__":
    main()

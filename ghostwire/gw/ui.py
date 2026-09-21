"""GHOSTWIRE user interface (KivyMD).

Layout system: fixed 20dp page gutters, hairline section headers, unified
card padding, single-line status rows and a consistent mono type scale.
"""

from __future__ import annotations

import math
import os
import random
import socket
import threading
import time

import kivy as _kivy_module
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.text import Label as _CoreLabel
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label as _KLabel
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

import kivymd
from kivymd.app import MDApp
from kivymd.icon_definitions import md_icons
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import (
    MDFillRoundFlatIconButton,
    MDIconButton,
    MDRoundFlatIconButton,
)
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.list import IconLeftWidget, MDList, TwoLineIconListItem
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

from . import net
from .crypto import Identity
from .net import NodeServer, SecureLink

MONO = os.path.join(os.path.dirname(_kivy_module.__file__),
                    "data", "fonts", "RobotoMono-Regular.ttf")
MDI_TTF = os.path.join(os.path.dirname(kivymd.__file__),
                       "fonts", "materialdesignicons-webfont.ttf")

# ---------------------------------------------------------------- palette
BG       = (0.043, 0.058, 0.043, 1)
PANEL    = (0.070, 0.094, 0.073, 1)
PANEL2   = (0.105, 0.140, 0.108, 1)
HAIRLINE = (0.16, 0.22, 0.17, 1)
GREEN    = (0.20, 0.95, 0.55, 1)
DGREEN   = (0.05, 0.32, 0.20, 1)
AMBER    = (1.00, 0.72, 0.20, 1)
RED      = (1.00, 0.35, 0.35, 1)
TXT      = (0.87, 0.94, 0.87, 1)
MUTED    = (0.46, 0.58, 0.48, 1)
ME_BUB   = (0.02, 0.28, 0.18, 1)
PEER_BUB = (0.115, 0.150, 0.115, 1)

GUTTER = 20          # page side gutter (dp)
CARD_PAD = [14, 12]  # unified card padding


class SizedLabel(MDLabel):
    """MDLabel clobbers font_size/font_name from the theme font_style inside
    __init__; this subclass pins the values the caller requested."""

    _fs = None
    _fn = None

    def __init__(self, **kw):
        if "font_size" in kw:
            self._fs = kw["font_size"]
        if "font_name" in kw:
            self._fn = kw["font_name"]
        super().__init__(**kw)
        self._pin()

    def update_font_style(self, *a):
        super().update_font_style(*a)
        self._pin()

    def _pin(self):
        if self._fn:
            self.font_name = self._fn
        if self._fs:
            self.font_size = self._fs


def L(text, **kw) -> SizedLabel:
    kw.setdefault("theme_text_color", "Custom")
    kw.setdefault("text_color", TXT)
    return SizedLabel(text=text, **kw)


def mono(text, size=9.5, color=None, **kw) -> SizedLabel:
    return SizedLabel(text=text, font_name=MONO, font_size=sp(size),
                      theme_text_color="Custom", text_color=color or TXT,
                      **kw)


def text_w(text: str, size: float) -> float:
    """Exact single-line width of `text` in the mono face (px)."""
    cl = _CoreLabel(text=text, font_size=size, font_name=MONO)
    cl.refresh()
    return cl.width


def hairline() -> MDBoxLayout:
    """A horizontal 1dp rule that fills available width."""
    d = MDBoxLayout(size_hint_y=None, height=dp(1))
    with d.canvas.before:
        Color(*HAIRLINE)
        r = Rectangle()
    d.bind(size=lambda i, v: setattr(r, "size", v),
           pos=lambda i, v: setattr(r, "pos", v))
    return d


def section_header(text: str) -> MDBoxLayout:
    """Overline label + trailing hairline rule."""
    row = MDBoxLayout(size_hint_y=None, height=dp(14), spacing=dp(10))
    t = mono(text, 8.5, GREEN, size_hint_y=None, height=dp(14))
    t.size_hint_x = None
    t.width = text_w(text, sp(8.5)) + dp(2)
    row.add_widget(t)
    row.add_widget(hairline())
    return row


class SegOption(ButtonBehavior, MDBoxLayout):
    """One half of the transport segmented control."""

    def __init__(self, text: str, selected: bool = False, **kw):
        super().__init__(**kw)
        self.selected = selected
        self.seg_text = text
        with self.canvas.before:
            Color(*HAIRLINE)
            self._line = Line(rounded_rectangle=[0, 0, 0, 0, dp(22)], width=1)
            self._col = Color(*(PANEL2 if selected else (0, 0, 0, 0)))
            self._rr = RoundedRectangle(radius=[dp(22)])
        self.bind(pos=self._upd, size=self._upd)
        lbl = mono(text, 9, GREEN if selected else MUTED, halign="center")
        lbl.valign = "middle"
        self._lbl = lbl
        self.add_widget(lbl)

    def set_selected(self, on: bool):
        self.selected = on
        self._col.rgba = PANEL2 if on else (0, 0, 0, 0)
        self._lbl.text_color = GREEN if on else MUTED

    def _upd(self, *a):
        self._rr.pos = self.pos
        self._rr.size = self.size


def panel(bg=PANEL, radius=None, padding=None) -> MDCard:
    return MDCard(orientation="vertical", md_bg_color=bg,
                  radius=radius or [dp(14)],
                  padding=padding or CARD_PAD, size_hint_y=None)


def kv_row(icon: str, text: str, color=MUTED, h=dp(20)) -> MDBoxLayout:
    row = MDBoxLayout(size_hint_y=None, height=h, spacing=dp(10))
    ic = MDIcon(icon=icon, font_size=sp(13), theme_text_color="Custom",
                text_color=color, size_hint_x=None, width=dp(16))
    lbl = mono(text, 9, color)
    lbl.valign = "middle"
    row.add_widget(ic)
    row.add_widget(lbl)
    row.lbl = lbl
    row.ic = ic
    return row


# ---------------------------------------------------------------- bubbles
class Bubble(MDBoxLayout):
    def __init__(self, app, mine: bool, text: str, ttl: int, mid: str):
        super().__init__(orientation="vertical", size_hint=(None, None),
                         padding=[dp(12), dp(8), dp(12), dp(6)],
                         spacing=dp(3))
        self.app = app
        self.mine = mine
        self.mid = mid
        self.ttl = ttl
        self.deadline = time.time() + ttl
        self.burned = False
        max_w = Window.width * 0.82
        with self.canvas.before:
            Color(*(ME_BUB if mine else PEER_BUB))
            rad = dp(12)
            self._rr = RoundedRectangle(
                radius=[rad, rad, dp(3) if mine else rad,
                        rad if mine else dp(3)])
        self.bind(pos=self._upd, size=self._upd)

        # header: [icon who] [time] ... [countdown]
        hdr = MDBoxLayout(size_hint_y=None, height=dp(14), spacing=dp(6))
        hdr.add_widget(MDIcon(icon="send" if mine else "account-circle",
                              font_size=sp(10), theme_text_color="Custom",
                              text_color=GREEN if mine else AMBER,
                              size_hint_x=None, width=dp(13)))
        who = mono("YOU" if mine else "REMOTE", 8, MUTED)
        who.size_hint_x = None
        who.width = text_w(who.text, sp(8)) + dp(2)
        hdr.add_widget(who)
        stamp = mono(time.strftime("%H:%M:%S"), 8, MUTED)
        stamp.size_hint_x = None
        stamp.width = text_w(stamp.text, sp(8)) + dp(2)
        hdr.add_widget(stamp)
        hdr.add_widget(Widget())          # push countdown to the edge
        self.count = mono(f"T-{ttl}s", 8.5, AMBER, halign="right")
        self.count.size_hint_x = None
        self.count.width = dp(40)
        hdr.add_widget(self.count)
        self.add_widget(hdr)

        self.body = SizedLabel(text=text, halign="left", valign="top",
                               font_size=sp(13.5), theme_text_color="Custom",
                               text_color=TXT, size_hint_y=None)
        self.body.text_size = (int(max_w - dp(28)), None)
        self.body.texture_update()
        tw = self.body.texture_size[0]
        self.width = int(min(max_w, tw + dp(30)))
        self.body.text_size = (int(self.width - dp(28)), None)
        self.body.texture_update()
        self.body.height = self.body.texture_size[1]
        self.add_widget(self.body)

        self.stat = mono("SENT // KEY ROTATED" if mine else "DECRYPTED // READING",
                         7.5, MUTED)
        self.stat.size_hint_y = None
        self.stat.height = dp(11)
        self.add_widget(self.stat)

        self.height = dp(14) + self.body.height + dp(11) + dp(18)

    def _upd(self, *a):
        self._rr.pos = self.pos
        self._rr.size = self.size


class Row(AnchorLayout):
    def __init__(self, bubble: Bubble):
        super().__init__(anchor_x="right" if bubble.mine else "left",
                         anchor_y="top", size_hint_y=None,
                         height=bubble.height + dp(6))
        self.bubble = bubble
        self.add_widget(bubble)





# ---------------------------------------------------------------- app
class GhostwireApp(MDApp):
    demo_hook_chat = None  # demo automation hook

    def build(self):
        self.title = "GHOSTWIRE"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Green"
        # Match the GL clear color to the app background so any blank
        # frame during window resizes (soft keyboard) is invisible.
        Window.clearcolor = (0.012, 0.02, 0.012, 1)
        # Tell Android where the focused field really is so adjustPan
        # slides it into view above the keyboard (the default reports a
        # dummy 10x1 rect at the top-left and panning never engages).
        Window.softinput_mode = "below_target"

        self.identity = Identity()
        self.server: NodeServer | None = None
        self.link: SecureLink | None = None
        self.peer_fp = ""
        self.session_id = ""
        self.transport = "wifi"
        # Message-expiry presets: default 60 s, then 1.5 / 2 / 3 / 5 min.
        self.ttl_options = [60, 90, 120, 180, 300]
        self.ttl_idx = 0
        self.ttl = self.ttl_options[self.ttl_idx]
        self.rows: dict[str, Row] = {}
        self.found = 0
        self.stealth = False
        self.scanning = False
        self.scan_stop = threading.Event()
        self._tick = None

        self.sm = MDScreenManager()
        if not os.environ.get("GW_DEMO"):
            self.sm.add_widget(self._build_splash())
        self.sm.add_widget(self._build_home())
        self.sm.add_widget(self._build_connect())
        self.sm.add_widget(self._build_scan())
        self.sm.add_widget(self._build_chat())
        self.sm.add_widget(self._build_security())
        return self.sm

    def on_start(self):
        if os.environ.get("GW_DEMO"):
            self.goto("home")
        else:
            self.splash_start()

    # ------------------------------------------------------------ utils
    def ui(self, fn, *args):
        Clock.schedule_once(lambda dt: fn(*args), 0)

    def threadlog(self, msg: str):
        self.ui(self.log, msg)

    def goto(self, name: str):
        self.sm.current = name

    # --------------------------------------------------------- splash
    SPLASH_DURATION = 3.2
    SPLASH_STATUS = [
        "BOOTSTRAPPING SECURE RUNTIME",
        "LOADING KEY MATERIAL // X25519 + ED25519",
        "PRIMING AES-256-GCM RATCHET",
        "CHANNEL INTEGRITY VERIFIED",
    ]

    def _build_splash(self):
        scr = MDScreen(name="splash", md_bg_color=(0.012, 0.02, 0.012, 1))

        hud = Widget()
        scr.add_widget(hud)

        def _draw_hud(*a):
            hud.canvas.clear()
            w, h = scr.size
            if w < 40 or h < 40:
                return
            with hud.canvas:
                Color(*GREEN)
                m, seg, lw = dp(18), dp(34), dp(1.6)
                Line(points=[m, h - m - seg, m, h - m, m + seg, h - m],
                     width=lw)
                Line(points=[w - m - seg, h - m, w - m, h - m,
                             w - m, h - m - seg], width=lw)
                Line(points=[w - m, m + seg, w - m, m, w - m - seg, m],
                     width=lw)
                Line(points=[m + seg, m, m, m, m, m + seg], width=lw)
                Color(*DGREEN)
                Line(points=[m + seg + dp(8), h - m,
                             w - m - seg - dp(8), h - m], width=dp(1))
                Line(points=[m + seg + dp(8), m,
                             w - m - seg - dp(8), m], width=dp(1))
        scr.bind(size=_draw_hud)

        body = FloatLayout()
        scr.add_widget(body)

        # rotating radar reticle
        radar = Widget(size_hint=(None, None), size=(dp(190), dp(190)),
                       pos_hint={"center_x": 0.5, "center_y": 0.635})
        body.add_widget(radar)

        def _radar(*a):
            radar.canvas.clear()
            cx, cy = radar.center
            r = radar.width / 2
            with radar.canvas:
                Color(*DGREEN)
                for frac in (1.0, 0.66, 0.33):
                    Line(circle=(cx, cy, r * frac), width=dp(1.1))
                Line(points=[cx - r, cy, cx + r, cy], width=dp(1))
                Line(points=[cx, cy - r, cx, cy + r], width=dp(1))
                Color(*GREEN)
                ang = self._splash_ang
                Line(points=[cx, cy,
                             cx + r * math.cos(ang),
                             cy + r * math.sin(ang)], width=dp(1.4))
                for i in range(18):
                    a2 = ang - i * 0.055
                    fade = max(0.05, 0.5 - i * 0.028)
                    Color(*GREEN[:3], fade)
                    Line(points=[cx, cy,
                                 cx + r * math.cos(a2),
                                 cy + r * math.sin(a2)], width=dp(1))
        self._splash_ang = math.pi / 2
        radar.bind(size=_radar)
        self._splash_radar_draw = _radar

        # shield + lock
        self.splash_icon = MDIcon(icon="shield-lock", font_size=sp(52),
                                  theme_text_color="Custom",
                                  text_color=GREEN,
                                  pos_hint={"center_x": 0.5,
                                            "center_y": 0.635})
        body.add_widget(self.splash_icon)

        # title
        self.splash_title = L("GHOSTWIRE", font_name=MONO, font_size=sp(30),
                              text_color=GREEN, halign="center", opacity=0)
        self.splash_title.pos_hint = {"center_x": 0.5, "center_y": 0.40}
        self.splash_title.size_hint = (1, None)
        self.splash_title.height = dp(40)
        body.add_widget(self.splash_title)
        self.splash_title.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))

        # scramble line
        self.splash_cipher = L("", font_name=MONO, font_size=sp(9),
                               text_color=MUTED, halign="center", opacity=0)
        self.splash_cipher.pos_hint = {"center_x": 0.5, "center_y": 0.345}
        self.splash_cipher.size_hint = (1, None)
        self.splash_cipher.height = dp(16)
        body.add_widget(self.splash_cipher)
        self.splash_cipher.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))

        # status line
        self.splash_status = L("BOOTSTRAPPING SECURE RUNTIME",
                               font_name=MONO, font_size=sp(10),
                               text_color=AMBER, halign="center", opacity=0)
        self.splash_status.pos_hint = {"center_x": 0.5, "center_y": 0.22}
        self.splash_status.size_hint = (1, None)
        self.splash_status.height = dp(18)
        body.add_widget(self.splash_status)
        self.splash_status.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))

        # progress bar
        barwrap = MDBoxLayout(size_hint=(0.72, None), height=dp(4),
                              pos_hint={"center_x": 0.5, "center_y": 0.17})
        self.splash_bar = MDProgressBar(value=0, color=GREEN)
        self.splash_bar.size_hint_y = 1
        barwrap.add_widget(self.splash_bar)
        body.add_widget(barwrap)

        # footer
        cred_l = L("DEVELOPED BY @ARIKO & ARENA", font_name=MONO,
                   font_size=sp(9), text_color=GREEN, halign="center",
                   opacity=0)
        cred_l.pos_hint = {"center_x": 0.5, "center_y": 0.10}
        cred_l.size_hint = (1, None)
        cred_l.height = dp(14)
        cred_l.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self.splash_cred = cred_l
        body.add_widget(cred_l)
        foot = L("TACTICAL MESH MESSENGER // E2E // BURN AFTER READ",
                 font_name=MONO, font_size=sp(8), text_color=MUTED,
                 halign="center", opacity=0)
        foot.pos_hint = {"center_x": 0.5, "center_y": 0.07}
        foot.size_hint = (1, None)
        foot.height = dp(14)
        body.add_widget(foot)
        foot.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self.splash_foot = foot

        scr.bind(on_touch_down=lambda i, t: self._splash_finish(force=True))
        return scr

    def splash_start(self):
        self._splash_done = False
        self.sm.current = "splash"
        # Hand off from the native presplash (lottie/static) to this
        # animated splash without a blank gap: remove the native layer
        # once our first frames are on screen.
        try:
            from android.loadingscreen import hide_loading_screen
            Clock.schedule_once(lambda dt: hide_loading_screen(), 0.25)
        except Exception:
            pass
        self._splash_events = []
        self._splash_events.append(
            Clock.schedule_interval(self._splash_tick, 1 / 45))
        self._splash_events.append(
            Clock.schedule_once(lambda dt: Animation(opacity=1, duration=0.5)
                                .start(self.splash_title), 0.15))
        self._splash_events.append(
            Clock.schedule_once(lambda dt: Animation(opacity=1, duration=0.4)
                                .start(self.splash_cipher), 0.3))
        self._splash_events.append(
            Clock.schedule_once(lambda dt: Animation(opacity=1, duration=0.4)
                                .start(self.splash_status), 0.4))
        self._splash_events.append(
            Clock.schedule_once(lambda dt: Animation(opacity=1, duration=0.6)
                                .start(self.splash_foot), 0.6))
        self._splash_events.append(
            Clock.schedule_once(lambda dt: Animation(opacity=1, duration=0.6)
                                .start(self.splash_cred), 0.8))
        self._splash_events.append(
            Clock.schedule_once(lambda dt: Animation(value=100,
                                                     duration=self.SPLASH_DURATION)
                                .start(self.splash_bar), 0.1))
        for i, msg in enumerate(self.SPLASH_STATUS[1:], start=1):
            self._splash_events.append(
                Clock.schedule_once(
                    lambda dt, m=msg: self._splash_set_status(m),
                    i * (self.SPLASH_DURATION / len(self.SPLASH_STATUS))))
        self._splash_events.append(
            Clock.schedule_once(lambda dt: self._splash_finish(),
                                self.SPLASH_DURATION))

    def _splash_set_status(self, msg):
        if getattr(self, "_splash_done", False):
            return
        self.splash_status.text = msg
        self.splash_status.color = AMBER

    _CIPHER_ALPHABET = "ABCDEF0123456789#$%&/\\<>*+=-"

    def _splash_tick(self, dt):
        if getattr(self, "_splash_done", False):
            return False
        self._splash_ang -= 0.12
        self._splash_radar_draw()
        n = 26
        self.splash_cipher.text = "".join(
            random.choice(self._CIPHER_ALPHABET) for _ in range(n))
        # pulse the shield
        s = 1 + 0.06 * math.sin(Clock.get_boottime() * 3.2)
        self.splash_icon.font_size = sp(52) * s
        return True

    def _splash_finish(self, force=False):
        if getattr(self, "_splash_done", False):
            return
        self._splash_done = True
        for ev in getattr(self, "_splash_events", []):
            ev.cancel()
        scr = self.sm.get_screen("splash")
        fade = Animation(opacity=0, duration=0.35)

        def _after(*a):
            self.sm.remove_widget(scr)
            self.goto("home")
        fade.bind(on_complete=_after)
        fade.start(scr)

    def snack(self, text: str, color=GREEN):
        try:
            MDSnackbar(
                MDLabel(text=text, theme_text_color="Custom",
                        text_color=(0.02, 0.05, 0.02, 1), font_size=sp(12)),
                md_bg_color=color, y=dp(24), duration=2.2,
            ).open()
        except Exception:
            pass

    def log(self, msg: str):
        self.connect_log.text += f"> {msg}\n"
        Clock.schedule_once(lambda dt: setattr(self.connect_log_sv,
                                               "scroll_y", 0), 0.01)

    def _topbar(self, title: str, back: str | None = None) -> MDTopAppBar:
        bar = MDTopAppBar(title=title, md_bg_color=PANEL,
                          specific_text_color=GREEN, elevation=0)
        if back:
            bar.left_action_items = [["arrow-left",
                                      lambda x, b=back: self.goto(b)]]
        return bar

    # ------------------------------------------------------------ HOME
    def _build_home(self):
        scr = MDScreen(name="home", md_bg_color=BG)
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG)
        bar = self._topbar("GHOSTWIRE")
        bar.right_action_items = [["shield-lock",
                                   lambda x: self.goto("security")]]
        root.add_widget(bar)

        sv = ScrollView()
        body = MDBoxLayout(orientation="vertical",
                           padding=[dp(GUTTER), dp(14)], spacing=dp(14),
                           size_hint_y=None)
        body.bind(minimum_height=lambda i, v: setattr(i, "height", v))

        # --- identity block
        hdr = MDBoxLayout(orientation="vertical", size_hint_y=None,
                          height=dp(118), spacing=dp(2))
        hdr.add_widget(_KLabel(text=md_icons["shield-lock"],
                               font_name=MDI_TTF, font_size=sp(46),
                               color=GREEN, halign="center",
                               size_hint_y=None, height=dp(58)))
        hdr.add_widget(L("[b]G H O S T W I R E[/b]", font_size=sp(22),
                         halign="center", markup=True, size_hint_y=None,
                         height=dp(30)))
        hdr.add_widget(mono("TACTICAL ENCRYPTED MESSENGER // GW1", 8, MUTED,
                            halign="center", size_hint_y=None, height=dp(12)))
        hdr.add_widget(hairline())
        body.add_widget(hdr)

        # --- node control
        node_card = panel()
        node_card.adaptive_height = True
        node_card.spacing = dp(10)
        node_card.add_widget(section_header("NODE CONTROL"))
        fields = MDBoxLayout(size_hint_y=None, height=dp(54), spacing=dp(10))
        self.bind_host_field = MDTextField(keyboard_suggestions=False, text="0.0.0.0", mode="rectangle",
                                           hint_text="BIND ADDR",
                                           font_size=sp(13))
        self.bind_port_field = MDTextField(keyboard_suggestions=False, text="9999", mode="rectangle",
                                           hint_text="PORT",
                                           input_filter="int",
                                           font_size=sp(13))
        self.bind_port_field.size_hint_x = 0.30
        fields.add_widget(self.bind_host_field)
        fields.add_widget(self.bind_port_field)
        node_card.add_widget(fields)
        self.node_status = mono("OFFLINE // NO NODE DEPLOYED", 9, MUTED,
                                size_hint_y=None, height=dp(13))
        node_card.add_widget(self.node_status)
        self.node_btn = MDFillRoundFlatIconButton(
            icon="broadcast", text="DEPLOY NODE", on_release=self.toggle_node,
            size_hint_y=None, height=dp(44))
        node_card.add_widget(self.node_btn)
        body.add_widget(node_card)

        # --- sitrep
        st = panel()
        st.adaptive_height = True
        st.spacing = dp(8)
        st.add_widget(section_header("SITREP"))
        self.link_row = kv_row("link-variant-off", "LINK // NO ACTIVE CHANNEL")
        st.add_widget(self.link_row)
        bt_state = "READY" if net.bluetooth_available() else "NO ADAPTER"
        st.add_widget(kv_row("bluetooth", f"BLUETOOTH RFCOMM // {bt_state}"))
        st.add_widget(kv_row("fingerprint",
                             f"IDENTITY // {self.identity.fingerprint[:15]}"))
        body.add_widget(st)

        # --- primary actions
        btns = MDBoxLayout(orientation="vertical", spacing=dp(10),
                           size_hint_y=None, height=dp(158))
        btns.add_widget(MDFillRoundFlatIconButton(
            icon="link-variant", text="ESTABLISH UPLINK",
            on_release=lambda x: self.goto("connect"),
            size_hint_y=None, height=dp(46)))
        btns.add_widget(MDFillRoundFlatIconButton(
            icon="radar", text="NETWORK SWEEP",
            on_release=lambda x: self.goto("scan"),
            size_hint_y=None, height=dp(46)))
        btns.add_widget(MDRoundFlatIconButton(
            icon="shield-check", text="SECURITY PROTOCOLS",
            on_release=lambda x: self.goto("security"),
            size_hint_y=None, height=dp(46)))
        body.add_widget(btns)

        # --- credits
        cred = panel()
        cred.adaptive_height = True
        cred.spacing = dp(4)
        cred.add_widget(section_header("CREDITS"))
        cred.add_widget(mono("DEVELOPED BY @ARIKO & ARENA", 10, GREEN,
                             halign="center", size_hint_y=None, height=dp(15)))
        cred.add_widget(mono("GHOSTWIRE v1.1.0 // GW1 PROTOCOL", 7.5, MUTED,
                             halign="center", size_hint_y=None, height=dp(12)))
        body.add_widget(cred)

        foot = mono("OPSEC DISCIPLINE // NO SYSTEM IS UNBREAKABLE",
                    7.5, MUTED, halign="center", size_hint_y=None,
                    height=dp(12))
        body.add_widget(foot)
        sv.add_widget(body)
        root.add_widget(sv)
        scr.add_widget(root)
        return scr

    def toggle_node(self, *a):
        if self.server:
            self.undeploy_node()
        else:
            self.deploy_node()

    def deploy_node(self):
        host = self.bind_host_field.text.strip() or "0.0.0.0"
        try:
            port = int(self.bind_port_field.text.strip() or 9999)
        except ValueError:
            return self.snack("INVALID PORT", RED)
        try:
            self.server = NodeServer(self.identity,
                                     on_link=self.on_inbound_link,
                                     on_request=self.on_inbound_request,
                                     status=self.threadlog)
            self.server.stealth = self.stealth
            self.server.start(host, port)
        except OSError as e:
            self.server = None
            return self.snack(f"BIND FAILED: {e}", RED)
        self.node_status.text = f"LISTENING {host}:{port} // GW1"
        self.node_status.text_color = GREEN
        self.node_btn.text = "STAND DOWN NODE"
        self.node_btn.icon = "power"
        self.log(f"NODE DEPLOYED ON {host}:{port}")
        self.snack(f"NODE DEPLOYED // LISTENING {host}:{port}")

    def undeploy_node(self):
        if self.server:
            self.server.stop()
            self.server = None
        self.node_status.text = "OFFLINE // NO NODE DEPLOYED"
        self.node_status.text_color = MUTED
        self.node_btn.text = "DEPLOY NODE"
        self.node_btn.icon = "broadcast"
        self.log("NODE STOOD DOWN")

    # ------------------------------------------------------------ CONNECT
    def _build_connect(self):
        scr = MDScreen(name="connect", md_bg_color=BG)
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG)
        root.add_widget(self._topbar("ESTABLISH UPLINK", back="home"))

        body = MDBoxLayout(orientation="vertical",
                           padding=[dp(GUTTER), dp(14)], spacing=dp(12))

        body.add_widget(section_header("TARGET DESIGNATION"))
        self.host_field = MDTextField(keyboard_suggestions=False, hint_text="TARGET HOST / IP",
                                      mode="rectangle", font_size=sp(13),
                                      size_hint_y=None, height=dp(54))
        body.add_widget(self.host_field)
        self.port_field = MDTextField(keyboard_suggestions=False, hint_text="TARGET PORT", text="9999",
                                      mode="rectangle", input_filter="int",
                                      font_size=sp(13), size_hint_y=None,
                                      height=dp(54))
        body.add_widget(self.port_field)

        body.add_widget(section_header("TRANSPORT"))
        seg = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.wifi_seg = SegOption("WIFI / LAN", selected=True)
        self.bt_seg = SegOption("BLUETOOTH")
        self.relay_seg = SegOption("WAN RELAY")
        self.wifi_seg.bind(on_release=lambda x: self._pick_transport("wifi"))
        self.bt_seg.bind(on_release=lambda x: self._pick_transport("bluetooth"))
        self.relay_seg.bind(on_release=lambda x: self._pick_transport("relay"))
        seg.add_widget(self.wifi_seg)
        seg.add_widget(self.bt_seg)
        seg.add_widget(self.relay_seg)
        body.add_widget(seg)

        actions = MDBoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        self.connect_btn = MDFillRoundFlatIconButton(
            icon="lan-connect", text="INITIATE HANDSHAKE",
            on_release=self.do_connect)
        actions.add_widget(self.connect_btn)
        drop = MDRoundFlatIconButton(
            icon="link-variant-off", text="DROP",
            on_release=lambda x: self.disconnect("OPERATOR REQUEST"))
        drop.size_hint_x = 0.34
        actions.add_widget(drop)
        body.add_widget(actions)

        body.add_widget(section_header("HANDSHAKE CONSOLE"))
        log_card = panel(bg=PANEL2, radius=[dp(12)], padding=[dp(12), dp(10)])
        log_card.size_hint_y = 1
        sv = ScrollView()
        self.connect_log = mono("", 9, GREEN)
        self.connect_log.size_hint_y = None
        self.connect_log.bind(texture_size=lambda i, v:
                              setattr(i, "height", v[1]))
        # top-anchored console content
        anchor = AnchorLayout(anchor_y="top", size_hint_y=None, height=dp(1))
        anchor.add_widget(self.connect_log)

        def _fit(*a):
            anchor.height = max(sv.height, self.connect_log.height)
        sv.bind(size=_fit)
        self.connect_log.bind(height=_fit)
        sv.add_widget(anchor)
        log_card.add_widget(sv)
        self.connect_log_sv = sv
        body.add_widget(log_card)

        root.add_widget(body)
        scr.add_widget(root)
        self.log("GW1 CONSOLE READY")
        self.log(f"LOCAL IDENTITY FP: {self.identity.fingerprint}")
        return scr

    def _pick_transport(self, mode: str):
        self.wifi_seg.set_selected(mode == "wifi")
        self.bt_seg.set_selected(mode == "bluetooth")
        self.relay_seg.set_selected(mode == "relay")
        self.set_transport(mode)

    def set_transport(self, mode: str):
        self.transport = mode
        if mode == "wifi":
            self.host_field.hint_text = "TARGET HOST / IP"
            self.port_field.hint_text = "TARGET PORT"
        elif mode == "bluetooth":
            self.host_field.hint_text = "BLUETOOTH BD ADDR (XX:XX:...)"
            self.port_field.hint_text = "RFCOMM CHANNEL"
        else:
            self.host_field.hint_text = "RELAY HOST"
            self.port_field.hint_text = "RELAY PORT"
            self.log("WAN RELAY // OPAKE BYTE PIPE - NEVER SEES PLAINTEXT")
        self.log(f"TRANSPORT SELECTED: {mode.upper()}")

    def do_connect(self, *a):
        host = self.host_field.text.strip()
        if not host:
            return self.snack("NO TARGET DESIGNATED", RED)
        try:
            port = int(self.port_field.text.strip() or 9999)
        except ValueError:
            return self.snack("INVALID PORT", RED)
        if self.link is not None and self.link.alive:
            return self.snack("ALREADY LINKED // DROP FIRST", AMBER)
        self.connect_btn.disabled = True
        self.log(f"OPENING CHANNEL -> {host}:{port} [{self.transport.upper()}]")

        def job():
            try:
                if self.transport == "bluetooth":
                    link = net.bluetooth_connect(self.identity, host, port,
                                                 status=self.threadlog)
                elif self.transport == "relay":
                    link = net.relay_connect(self.identity, host, port,
                                             status=self.threadlog)
                else:
                    sock = socket.create_connection((host, port), timeout=6)
                    # The peer may sit at the operator request gate for up
                    # to 60 s before the handshake even begins.
                    sock.settimeout(95)
                    link = SecureLink(sock, self.identity, "client",
                                      status=self.threadlog)
                    link.handshake_client()
                    sock.settimeout(None)
                link.on_message = lambda obj: self.ui(self.handle_msg, obj)
                link.on_close = lambda: self.ui(self.link_died, "LINK LOST")
                link.start()
                label = f"{host}:{port}"
                if self.transport == "relay":
                    label += " // WAN RELAY"
                self.ui(self.link_up, link, label)
            except Exception as e:
                self.ui(self.link_failed, f"{type(e).__name__}: {e}")

        threading.Thread(target=job, daemon=True).start()

    def link_failed(self, msg: str):
        self.connect_btn.disabled = False
        self.log(f"UPLINK FAILED - {msg}")
        self.snack("UPLINK FAILED", RED)

    # ------------------------------------------- link lifecycle (P2P)
    # GW1 v1.1.0 is strictly peer-to-peer: one live secure link.
    # Inbound connections are parked at the node's request gate until
    # the operator ACKNOWLEDGEs or REJECTs them (60 s window), so no
    # third device can ever silently displace an active peer.

    def on_inbound_request(self, label: str, gate_id: int):
        """Node thread -> UI: show the acknowledge/reject dialog."""
        if os.environ.get("GW_DEMO"):
            self.server.respond(gate_id, True)
            self.ui(self.log, f"GW_DEMO AUTO-ACK // {label}")
            return

        def show():
            dlg = MDDialog(
                title="INBOUND REQUEST",
                text=(f"{label} REQUESTS A CHAT.\n\n"
                      "ACKNOWLEDGE to begin the GW1 handshake. "
                      "REJECT closes the connection. Unanswered "
                      "requests expire after 60 s."),
                buttons=[
                    MDRoundFlatIconButton(
                        icon="check-decagram", text="ACKNOWLEDGE",
                        on_release=lambda x: (
                            dlg.dismiss(),
                            self.server and self.server.respond(gate_id,
                                                                True))),
                    MDRoundFlatIconButton(
                        icon="close-circle", text="REJECT",
                        on_release=lambda x: (
                            dlg.dismiss(),
                            self.server and self.server.respond(gate_id,
                                                                False))),
                ],
            )
            dlg.open()
            self.log(f"REQUEST // {label} AWAITING DECISION")
        self.ui(show)

    def link_up(self, link: SecureLink, endpoint: str):
        self.link = link
        self.peer_fp = link.peer_fingerprint
        self.session_id = link.session_id
        self.connect_btn.disabled = False
        self.log(f"SESSION {link.session_id[:16]}…")
        self.log(f"PEER FP {link.peer_fingerprint}")
        self._set_link_widgets(endpoint)
        self.snack("SECURE LINK ESTABLISHED")
        self._start_tick()
        Clock.schedule_once(lambda dt: self.goto("chat"), 2.5)

    def _set_link_widgets(self, endpoint: str):
        self.chat_endpoint.text = endpoint
        self.chat_peerfp.text = f"PEER {self.peer_fp}"
        self.sec_session_id.text = f"SESSION ID // {self.session_id}"
        self.sec_peer_fp.text = f"PEER FINGERPRINT // {self.peer_fp}"
        self.link_row.lbl.text = f"LINK // SECURE {self.peer_fp[:11]}…"
        self.link_row.ic.icon = "link-variant"
        self.link_row.lbl.text_color = GREEN

    def disconnect(self, reason="OPERATOR REQUEST"):
        if self.link:
            self.link.close()
            self.link = None
        self.log(f"CHANNEL CLOSED ({reason})")
        self.snack("LINK TERMINATED", AMBER)

    def link_died(self, reason: str):
        if not self.link:
            return
        self.link = None
        self.peer_fp = ""
        self.session_id = ""
        self.chat_endpoint.text = "LINK LOST"
        self.chat_peerfp.text = reason
        self.sec_session_id.text = "SESSION ID // NONE ACTIVE"
        self.sec_peer_fp.text = "PEER FINGERPRINT // -"
        self.link_row.lbl.text = "LINK // NO ACTIVE CHANNEL"
        self.link_row.ic.icon = "link-variant-off"
        self.link_row.lbl.text_color = MUTED
        self.snack(reason, RED)

    def on_inbound_link(self, link: SecureLink, addr):
        # NodeServer completes the handshake and starts the link itself;
        # the UI only owns rendering from here on.
        link.on_message = lambda obj: self.ui(self.handle_msg, obj)
        link.on_close = lambda: self.ui(self.link_died, "LINK LOST")
        self.link = link
        self.peer_fp = link.peer_fingerprint
        self.session_id = link.session_id

        def upd():
            self._set_link_widgets(f"INBOUND {addr[0]}:{addr[1]}")
            self.log(f"INBOUND LINK FROM {addr[0]}:{addr[1]}")
            self.snack(f"INBOUND LINK // {self.peer_fp[:11]}…")
            self.goto("chat")
        self.ui(upd)
        self._start_tick()

    # ------------------------------------------------------------ SCAN
    def _build_scan(self):
        scr = MDScreen(name="scan", md_bg_color=BG)
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG)
        root.add_widget(self._topbar("NETWORK SWEEP", back="home"))

        body = MDBoxLayout(orientation="vertical",
                           padding=[dp(GUTTER), dp(14)], spacing=dp(12))

        body.add_widget(section_header("TARGET PARAMETERS"))
        default_net = ".".join(net.local_ip().split(".")[:3]) + ".0/24"
        row = MDBoxLayout(size_hint_y=None, height=dp(54), spacing=dp(10))
        self.target_field = MDTextField(keyboard_suggestions=False, text=default_net, mode="rectangle",
                                        hint_text="TARGET RANGE (CIDR / LIST)",
                                        font_size=sp(13))
        row.add_widget(self.target_field)
        self.scan_port_field = MDTextField(keyboard_suggestions=False, text="9999", mode="rectangle",
                                           hint_text="PORT",
                                           input_filter="int",
                                           font_size=sp(13))
        self.scan_port_field.size_hint_x = 0.28
        row.add_widget(self.scan_port_field)
        body.add_widget(row)

        actions = MDBoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        self.sweep_btn = MDFillRoundFlatIconButton(
            icon="radar", text="INITIATE SWEEP", on_release=self.start_sweep)
        actions.add_widget(self.sweep_btn)
        self.abort_btn = MDRoundFlatIconButton(
            icon="close-circle", text="ABORT", on_release=self.abort_sweep,
            disabled=True)
        self.abort_btn.size_hint_x = 0.34
        actions.add_widget(self.abort_btn)
        body.add_widget(actions)

        prog = MDBoxLayout(size_hint_y=None, height=dp(22), spacing=dp(10))
        self.sweep_progress = MDProgressBar(value=0)
        prog.add_widget(self.sweep_progress)
        self.sweep_status = mono("STANDBY // AWAITING ORDER", 8.5, MUTED,
                                 halign="right", size_hint_x=None,
                                 width=dp(210))
        prog.add_widget(self.sweep_status)
        body.add_widget(prog)

        body.add_widget(section_header("CONTACTS"))
        res_card = panel(bg=PANEL2, radius=[dp(12)], padding=[dp(4), dp(4)])
        res_card.size_hint_y = 1
        fl = FloatLayout()
        sv = ScrollView(size_hint=(1, 1))
        self.scan_results = MDList()
        sv.add_widget(self.scan_results)
        self.scan_placeholder = mono("NO CONTACTS LOGGED", 8.5, MUTED,
                                     halign="center", size_hint=(None, None),
                                     pos_hint={"center_x": 0.5,
                                               "center_y": 0.5})
        self.scan_placeholder.size = (text_w("NO CONTACTS LOGGED",
                                             sp(8.5)) + dp(4), dp(14))
        fl.add_widget(sv)
        fl.add_widget(self.scan_placeholder)
        res_card.add_widget(fl)
        body.add_widget(res_card)

        root.add_widget(body)
        scr.add_widget(root)
        return scr

    def start_sweep(self, *a):
        if self.scanning:
            return
        try:
            targets = net.expand_targets(self.target_field.text)
            port = int(self.scan_port_field.text.strip() or 9999)
        except (ValueError, TypeError) as e:
            return self.snack(f"INVALID TARGET SPEC: {e}", RED)
        self.scanning = True
        self.scan_stop.clear()
        self.sweep_btn.disabled = True
        self.abort_btn.disabled = False
        self.scan_results.clear_widgets()
        self.scan_placeholder.opacity = 1
        self.found = 0
        self.sweep_status.text = f"SWEEP {len(targets)} SECTORS…"
        self.sweep_status.text_color = AMBER

        def on_progress(done, total):
            self.ui(self._sweep_prog, done, total)

        def on_result(ip, kind, fp):
            self.ui(self._sweep_hit, ip, kind, fp)

        def job():
            net.sweep(targets, port, on_result, on_progress,
                      self.scan_stop.is_set)
            self.ui(self._sweep_done, len(targets))

        threading.Thread(target=job, daemon=True).start()

    def _sweep_prog(self, done, total):
        self.sweep_progress.value = 100.0 * done / max(total, 1)
        self.sweep_status.text = f"{done}/{total}"

    def _sweep_hit(self, ip, kind, fp):
        # STEALTH FIX: sweeps list only hosts that answer with a GW1
        # PONG (confirmed GHOSTWIRE nodes).  A stealth node swallows
        # probes silently, so it never appears here — open ports are
        # ignored instead of being exposed.
        if kind != "node":
            return
        self.found += 1
        self.scan_placeholder.opacity = 0
        item = TwoLineIconListItem(
            text=f"{ip}  [GHOSTWIRE NODE]",
            secondary_text=f"FP {fp}",
            on_release=lambda x, h=ip: self._select_target(h))
        item.add_widget(IconLeftWidget(icon="access-point",
                                       theme_text_color="Custom",
                                       text_color=GREEN))
        self.scan_results.add_widget(item)

    def _select_target(self, host: str):
        self.host_field.text = host
        self.port_field.text = self.scan_port_field.text
        self.goto("connect")
        self.snack(f"TARGET DESIGNATED: {host}")

    def _sweep_done(self, total):
        self.scanning = False
        self.sweep_btn.disabled = False
        self.abort_btn.disabled = True
        self.sweep_progress.value = 100
        self.sweep_status.text = f"COMPLETE // {self.found} CONTACTS"
        self.sweep_status.text_color = GREEN

    def abort_sweep(self, *a):
        self.scan_stop.set()
        self.sweep_status.text = "ABORTED"
        self.sweep_status.text_color = RED

    # ------------------------------------------------------------ CHAT
    def _build_chat(self):
        scr = MDScreen(name="chat", md_bg_color=BG)
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG)

        bar = MDBoxLayout(md_bg_color=PANEL, size_hint_y=None, height=dp(58),
                          padding=[dp(4), dp(8), dp(8), dp(8)],
                          spacing=dp(0))
        back = MDIconButton(icon="arrow-left",
                            on_release=lambda x: self.goto("home"))
        back.size_hint_x = None
        back.width = dp(40)
        bar.add_widget(back)
        col = MDBoxLayout(orientation="vertical", spacing=dp(1))
        self.chat_endpoint = mono("NO ACTIVE CHANNEL", 10.5, GREEN)
        self.chat_peerfp = mono("ESTABLISH UPLINK TO BEGIN", 7.5, MUTED)
        col.add_widget(self.chat_endpoint)
        col.add_widget(self.chat_peerfp)
        bar.add_widget(col)
        for icon, cb in [("shield-check", lambda x: self.verify_dialog()),
                         ("delete-forever", lambda x: self.burn_all()),
                         ("power", lambda x: self.disconnect())]:
            b = MDIconButton(icon=icon, on_release=cb)
            b.size_hint_x = None
            b.width = dp(40)
            bar.add_widget(b)
        root.add_widget(bar)

        banner = MDBoxLayout(md_bg_color=DGREEN, size_hint_y=None,
                             height=dp(18), padding=[dp(14), 0],
                             spacing=dp(8))
        banner.add_widget(MDIcon(icon="lock", font_size=sp(9),
                                 theme_text_color="Custom", text_color=GREEN,
                                 size_hint_x=None, width=dp(12)))
        b = mono("AES-256-GCM E2E // RATCHETED KEYS // BURN AFTER READ",
                 7.5, GREEN)
        b.valign = "middle"
        banner.add_widget(b)
        root.add_widget(banner)

        sv = ScrollView()
        self.chat_box = MDBoxLayout(orientation="vertical",
                                    padding=[dp(10), dp(10)], spacing=dp(2),
                                    size_hint_y=None)
        self.chat_box.bind(minimum_height=lambda i, v:
                           setattr(i, "height", v))
        sv.add_widget(self.chat_box)
        self.chat_scroll = sv
        root.add_widget(sv)

        inp = MDBoxLayout(md_bg_color=PANEL, size_hint_y=None, height=dp(58),
                          padding=[dp(10), dp(9)], spacing=dp(8))
        self.ttl_btn = MDRoundFlatIconButton(icon="fire",
                                             text=self.ttl_label(self.ttl),
                                             on_release=self.cycle_ttl,
                                             size_hint_x=None, width=dp(80))
        inp.add_widget(self.ttl_btn)
        self.msg_field = MDTextField(keyboard_suggestions=False, hint_text="ENCRYPTED TRANSMISSION…",
                                     font_size=sp(13.5), mode="rectangle")
        inp.add_widget(self.msg_field)
        send = MDIconButton(icon="send", theme_text_color="Custom",
                            text_color=GREEN, on_release=self.send_msg)
        send.size_hint_x = None
        send.width = dp(40)
        inp.add_widget(send)
        root.add_widget(inp)

        scr.add_widget(root)
        return scr

    @staticmethod
    def ttl_label(secs: int) -> str:
        # The 60 s default stays in seconds; longer presets read as minutes.
        if secs <= 60:
            return f"{secs}s"
        if secs % 60:
            return f"{secs // 60}.{(secs % 60) * 10 // 60}m"
        return f"{secs // 60}m"

    def cycle_ttl(self, *a):
        self.ttl_idx = (self.ttl_idx + 1) % len(self.ttl_options)
        self.ttl = self.ttl_options[self.ttl_idx]
        self.ttl_btn.text = self.ttl_label(self.ttl)

    def _scroll_bottom(self):
        Clock.schedule_once(lambda dt: setattr(self.chat_scroll,
                                               "scroll_y", 0), 0.05)

    def add_bubble(self, mine: bool, text: str, ttl: int, mid: str):
        bubble = Bubble(self, mine, text, ttl, mid)
        row = Row(bubble)
        self.rows[mid] = row
        self.chat_box.add_widget(row)
        self._scroll_bottom()

    def send_msg(self, *a):
        text = self.msg_field.text.strip()
        if not text:
            return
        if not self.link or not self.link.alive:
            return self.snack("NO SECURE CHANNEL", RED)
        try:
            mid = self.link.send_chat(text, self.ttl)
        except Exception:
            return self.snack("TRANSMISSION FAILED", RED)
        self.msg_field.text = ""
        self.add_bubble(True, text, self.ttl, mid)

    def handle_msg(self, obj: dict):
        """Single-link inbound router (already decrypted by the ratchet)."""
        t = obj.get("t")
        if t == "msg":
            self.recv_msg(obj)
            if self.demo_hook_chat:
                self.demo_hook_chat(obj.get("text", ""))
        elif t == "seen":
            self.mark_seen(obj.get("id"))
        elif t == "burned":
            self.peer_burned(obj.get("id"))

    def recv_msg(self, obj: dict):
        mid = obj.get("id", "")
        self.add_bubble(False, obj.get("text", ""),
                        int(obj.get("ttl", 60)), mid)
        if self.link and self.link.alive:
            try:
                self.link.send_control("seen", mid)
            except Exception:
                pass

    def mark_seen(self, mid: str):
        row = self.rows.get(mid)
        if row:
            row.bubble.stat.text = "READ BY PEER // KEY ROTATED"
            row.bubble.stat.text_color = GREEN

    def peer_burned(self, mid: str):
        row = self.rows.get(mid)
        if not row:
            return
        row.bubble.stat.text = "INCINERATED // PEER CONFIRMED"
        row.bubble.stat.text_color = RED
        Clock.schedule_once(lambda dt: self._remove_row(mid), 0.9)

    def _remove_row(self, mid: str):
        row = self.rows.pop(mid, None)
        if row:
            self.chat_box.remove_widget(row)

    def burn(self, mid: str):
        row = self.rows.get(mid)
        if not row:
            return
        row.bubble.burned = True
        mine = row.bubble.mine
        self._remove_row(mid)
        if self.link and self.link.alive:
            try:
                self.link.send_control("burned", mid)
            except Exception:
                pass
        self.log(f"BURN {'SENT' if mine else 'RECV'} {mid}")

    def burn_all(self, *a):
        if not self.rows:
            return self.snack("NOTHING TO BURN", AMBER)
        for mid in list(self.rows.keys()):
            self.burn(mid)
        self.snack("ALL TRANSMISSIONS INCINERATED", RED)

    def _start_tick(self):
        if self._tick is None:
            self._tick = Clock.schedule_interval(self._tick_burn, 0.5)

    def _tick_burn(self, dt):
        now = time.time()
        for mid, row in list(self.rows.items()):
            b = row.bubble
            if b.burned:
                continue
            rem = b.deadline - now
            if rem <= 0:
                self.burn(mid)
            else:
                secs = math.ceil(rem)
                b.count.text = f"T-{secs}s"
                b.count.text_color = RED if secs <= 3 else AMBER

    def verify_dialog(self):
        if not self.peer_fp:
            return self.snack("NO PEER TO VERIFY", AMBER)
        dlg = MDDialog(
            title="IDENTITY VERIFICATION",
            text=(f"PEER FINGERPRINT:\n{self.peer_fp}\n\n"
                  "VERIFY OUT-OF-BAND (VOICE / VISUAL) BEFORE\n"
                  "TRANSMITTING CLASSIFIED MATERIAL."),
            buttons=[MDRoundFlatIconButton(icon="check-decagram",
                                           text="ACKNOWLEDGED",
                                           on_release=lambda x: dlg.dismiss())],
        )
        dlg.open()

    # ------------------------------------------------------------ SECURITY
    def _suite_row(self, icon: str, name: str, value: str) -> MDBoxLayout:
        row = MDBoxLayout(size_hint_y=None, height=dp(22), spacing=dp(10))
        row.add_widget(MDIcon(icon=icon, font_size=sp(13),
                              theme_text_color="Custom", text_color=GREEN,
                              size_hint_x=None, width=dp(16)))
        n = mono(name, 8.5, MUTED)
        n.size_hint_x = None
        n.width = dp(72)
        n.valign = "middle"
        row.add_widget(n)
        v = mono(value, 8.5, TXT)
        v.valign = "middle"
        row.add_widget(v)
        return row

    def _build_security(self):
        scr = MDScreen(name="security", md_bg_color=BG)
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG)
        root.add_widget(self._topbar("SECURITY PROTOCOLS", back="home"))

        sv = ScrollView()
        body = MDBoxLayout(orientation="vertical",
                           padding=[dp(GUTTER), dp(14)], spacing=dp(12),
                           size_hint_y=None)
        body.bind(minimum_height=lambda i, v: setattr(i, "height", v))

        suite = panel()
        suite.adaptive_height = True
        suite.spacing = dp(6)
        suite.add_widget(section_header("GW1 CIPHER SUITE"))
        for icon, name, value in [
            ("key-variant",    "KEX",     "X25519 ECDH // EPHEMERAL"),
            ("fingerprint",    "AUTH",    "ED25519 MUTUAL SIGNATURES"),
            ("refresh",        "KDF",     "HKDF-SHA256 + SYM RATCHET"),
            ("shield-lock",    "CIPHER",  "AES-256-GCM (AEAD)"),
            ("check-decagram", "CONFIRM", "HMAC-SHA256 KEY CONFIRM"),
            ("fire",           "BURN",    "BILATERAL SELF-DESTRUCT"),
        ]:
            suite.add_widget(self._suite_row(icon, name, value))
        body.add_widget(suite)

        rfc = panel()
        rfc.adaptive_height = True
        rfc.spacing = dp(6)
        rfc.add_widget(section_header("STANDARDS & RFC REFERENCES"))
        for icon, name, value in [
            ("key-variant",    "RFC 7748",     "X25519 DIFFIE-HELLMAN"),
            ("fingerprint",    "RFC 8032",     "ED25519 SIGNATURES"),
            ("refresh",        "RFC 5869",     "HKDF-SHA256 KDF"),
            ("check-decagram", "RFC 2104",     "HMAC KEY CONFIRMATION"),
            ("shield-lock",    "NIST SP 800-38D", "AES-256-GCM AEAD"),
            ("numeric",        "FIPS 180-4",   "SHA-256 DIGEST"),
        ]:
            rfc.add_widget(self._suite_row(icon, name, value))
        body.add_widget(rfc)

        sess = panel()
        sess.adaptive_height = True
        sess.spacing = dp(6)
        sess.add_widget(section_header("ACTIVE SESSION"))
        self.sec_session_id = mono("SESSION ID // NONE ACTIVE", 8.5, MUTED,
                                   size_hint_y=None)
        self.sec_session_id.bind(texture_size=lambda i, v:
                                 setattr(i, "height", v[1] + 2))
        sess.add_widget(self.sec_session_id)
        self.sec_peer_fp = mono("PEER FINGERPRINT // -", 8.5, MUTED,
                                size_hint_y=None)
        self.sec_peer_fp.bind(texture_size=lambda i, v:
                              setattr(i, "height", v[1] + 2))
        sess.add_widget(self.sec_peer_fp)
        sess.add_widget(kv_row("alert", "VERIFY FINGERPRINTS OUT-OF-BAND",
                               AMBER))
        body.add_widget(sess)

        ident = panel()
        ident.adaptive_height = True
        ident.spacing = dp(6)
        ident.add_widget(section_header("LOCAL NODE"))
        fp_lbl = mono(f"IDENTITY FP // {self.identity.fingerprint}", 8.5, TXT,
                      size_hint_y=None)
        fp_lbl.bind(texture_size=lambda i, v: setattr(i, "height", v[1] + 2))
        ident.add_widget(fp_lbl)
        st_row = MDBoxLayout(size_hint_y=None, height=dp(26), spacing=dp(10))
        st_row.add_widget(MDIcon(icon="incognito", font_size=sp(13),
                                 theme_text_color="Custom", text_color=MUTED,
                                 size_hint_x=None, width=dp(16)))
        sw_lbl = mono("STEALTH MODE // NODE INVISIBLE TO SWEEPS", 8.5, TXT)
        sw_lbl.valign = "middle"
        st_row.add_widget(sw_lbl)
        sw = MDSwitch(active=False, on_active=self.on_stealth)
        sw.size_hint_x = None
        sw.width = dp(40)
        st_row.add_widget(sw)
        ident.add_widget(st_row)
        body.add_widget(ident)

        ops = panel(bg=DGREEN)
        ops.adaptive_height = True
        note = mono("FIELD NOTE // NO CRYPTO IS MAGICALLY UNBREAKABLE. "
                    "GW1 PROVIDES CONFIDENTIALITY, INTEGRITY, MUTUAL "
                    "AUTHENTICATION, FORWARD SECRECY AND TRANSIENCE. "
                    "YOUR DEVICE REMAINS THE WEAKEST LINK.", 8, TXT,
                    size_hint_y=None)
        note.bind(texture_size=lambda i, v: setattr(i, "height", v[1] + 4))
        ops.add_widget(note)
        body.add_widget(ops)

        ver = mono("GHOSTWIRE v1.1.0 // GW1 PROTOCOL // DEVELOPED BY "
                   "@ARIKO & ARENA", 7.5, MUTED, halign="center",
                   size_hint_y=None)
        ver.bind(texture_size=lambda i, v: setattr(i, "height", v[1] + 2))
        body.add_widget(ver)

        sv.add_widget(body)
        root.add_widget(sv)
        scr.add_widget(root)
        return scr

    def on_stealth(self, switch, active):
        self.stealth = bool(active)
        if self.server:
            self.server.stealth = self.stealth
        self.snack("STEALTH MODE " + ("ENGAGED" if self.stealth else "OFF"),
                   AMBER if self.stealth else GREEN)

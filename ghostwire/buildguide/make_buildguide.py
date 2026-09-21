#!/usr/bin/env python3
"""Build the GHOSTWIRE APK Compilation Guide (Colab + Ubuntu + Docker).

Usage:  python3 buildguide/make_buildguide.py
Output: buildguide/GHOSTWIRE_APK_Build_Guide_v1.1.0.pdf  (cap: 40 pages)
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
OUT = os.path.join(HERE, "GHOSTWIRE_APK_Build_Guide_v1.1.0.pdf")
MAX_PAGES = 40

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

GREEN = HexColor("#1B7A3D")
DARK = HexColor("#0B0E0B")
MUTED = HexColor("#5A6B5D")
LIGHT_BG = HexColor("#EDF5EE")
HAIR = HexColor("#BFD8C2")
AMBER_BG = HexColor("#FDF5E6")
AMBER = HexColor("#9A6B12")

try:
    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVuMono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
    BODY_FONT, BOLD_FONT, MONO_FONT = "DejaVu", "DejaVu-B", "DejaVuMono"
except Exception:
    BODY_FONT, BOLD_FONT, MONO_FONT = "Helvetica", "Helvetica-Bold", "Courier"

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
S["mono"] = ParagraphStyle("mono", fontName=MONO_FONT, fontSize=8.2,
                           leading=12, textColor=DARK, spaceAfter=1.5)
S["caption"] = ParagraphStyle("caption", fontName=BOLD_FONT, fontSize=8.5,
                              leading=11.5, textColor=MUTED,
                              alignment=TA_CENTER, spaceBefore=4, spaceAfter=8)
S["cover1"] = ParagraphStyle("cover1", fontName=BOLD_FONT, fontSize=28,
                             leading=32, textColor=GREEN, alignment=TA_CENTER)
S["cover2"] = ParagraphStyle("cover2", fontName=BODY_FONT, fontSize=12.5,
                             leading=16.5, textColor=MUTED, alignment=TA_CENTER)
S["toc_h"] = ParagraphStyle("toc_h", fontName=BOLD_FONT, fontSize=17,
                            leading=21, textColor=GREEN, spaceAfter=10)

PAGE_W, PAGE_H = A4
FOOT = "GHOSTWIRE v1.1.0 — APK Build Guide"


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(BODY_FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(PAGE_W / 2, 14 * mm,
                             f"{FOOT}    ·    page {doc.page}")
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


import re as _re


def _mono_line(ln):
    # Escape markup, protect leading indent, but leave inner spaces
    # wrappable so long commands fold instead of running off-page.
    # No "$" prompts anywhere: every block is copy-paste safe.
    esc = ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    esc = _re.sub(r"^ +", lambda m: "&nbsp;" * len(m.group(0)), esc)
    return Paragraph(esc or "<br/>", S["mono"])


def cmd(lines, gap_after=6):
    if isinstance(lines, str):
        lines = [lines]
    for ln in lines:
        story.append(_mono_line(ln))
    story.append(Spacer(1, gap_after))


def out(lines, gap_after=6):
    cmd(lines, gap_after)


def note(title, text, amber=False):
    inner = [[Paragraph(f"<b>{title}</b> — {text}", S["body"])]]
    t = Table(inner, colWidths=[PAGE_W - 36 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AMBER_BG if amber else LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, AMBER if amber else GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))


def fig(name, caption, width_mm=58, aspect=720 / 400):
    _fig_no[0] += 1
    img = Image(os.path.join(FIG, name + ".png"))
    img.drawWidth = width_mm * mm
    img.drawHeight = width_mm * mm * aspect
    story.append(KeepTogether([
        img, Paragraph(f"Figure {_fig_no[0]} — {caption}", S["caption"]),
    ]))


def table(header, rows, widths_mm):
    data = [[Paragraph(f"<b>{c}</b>", S["body"]) for c in header]]
    for r in rows:
        data.append([Paragraph(c, S["body"]) for c in r])
    t = Table(data, colWidths=[w * mm for w in widths_mm], repeatRows=1)
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


def chapter(no, title):
    h1(f"{no}&nbsp;&nbsp;{title}")


# ================================================================= COVER
story.append(NextPageTemplate("cover"))
story.append(Spacer(1, 30 * mm))
story.append(Paragraph("GHOSTWIRE", S["cover1"]))
story.append(Spacer(1, 4 * mm))
story.append(Paragraph("APK Compilation Guide · v1.1.0", S["cover2"]))
story.append(Paragraph("Reproducible builds on Google Colab, Ubuntu "
                       "and Docker", S["cover2"]))
story.append(Spacer(1, 10 * mm))
fig("pipeline", "The whole process on one page. Details inside.",
    width_mm=150, aspect=980 / 1600)
story.append(Spacer(1, 6 * mm))
story.append(Paragraph("Every command in this book ran verbatim to ship "
                       "the release APK.<br/>Nothing is paraphrased from "
                       "memory.", S["cover2"]))
story.append(NextPageTemplate("main"))
story.append(PageBreak())

# ==================================================================== TOC
story.append(Paragraph("Contents", S["toc_h"]))
_toc = TableOfContents()
_toc.levelStyles = [
    ParagraphStyle("toc1", fontName=BOLD_FONT, fontSize=10, leading=14.5,
                   textColor=DARK, spaceBefore=1, spaceAfter=0),
]
story.append(_toc)
story.append(PageBreak())

# ======================================================== 1 · WHAT/STACK
chapter("1", "What you are building")
p("Input: the <b>ghostwire/</b> project folder (Python source + "
  "<b>buildozer.spec</b>). Output: <b>bin/ghostwire-1.1.0-arm64-v8a-debug"
  ".apk</b> (~31 MB), installable on any Android 10+ arm64 phone. The "
  "tool that turns one into the other is <b>buildozer</b>, which drives "
  "<b>python-for-android (p4a)</b>: p4a cross-compiles Python + every "
  "native library for ARM64, wraps them in an SDL2 Android bootstrap, "
  "Gradle assembles the APK.")
h2("1.1&nbsp;&nbsp;Cost of a cold build")
table(["Resource", "Budget", "Notes"],
      [["Time", "45–90 min", "Downloads ~15 min, recipe compiles ~30–60 "
        "min on 2 vCPUs, Gradle ~3 min. Rebuilds take minutes."],
       ["Disk", "15 GB free", "~3 GB SDK/NDK + ~8 GB recipes/dist. "
        "Docker hosts: check before you start (E10)."],
       ["RAM", "4 GB ideal", "2 GB works with a 3 GB swapfile (§5.5). "
        "Colab's 12 GB needs nothing."]],
      [30, 34, 110])
h2("1.2&nbsp;&nbsp;Version manifest — the exact stack that shipped")
p("These are not recommendations. They are the versions the release "
  "APK was compiled with; replicate them first, experiment later.")
table(["Component", "Version", "How it arrives"],
      [["Host OS", "Debian 13 x86_64 (sandbox); Ubuntu 22.04/24.04 "
        "equivalent", "your machine / Colab / image"],
       ["Host Python", "3.13", "system python3"],
       ["buildozer", "1.6.0", "pip"],
       ["Cython", "3.x (pip latest)", "pip; fallback pin in §9 E12"],
       ["JDK", "Temurin 17.0.20.1+1", "tarball (§4–6) or apt (§5.2)"],
       ["python-for-android", "master @ 58d21141", "buildozer clones it"],
       ["Android NDK", "r28c", "buildozer downloads it"],
       ["SDK platform / build-tools", "android-34 / 34.x", "sdkmanager"],
       ["platform-tools", "r37.0.1", "sdkmanager"],
       ["Apache ANT", "1.9.4", "buildozer downloads it"],
       ["Gradle", "8.14.3", "gradlew downloads it"],
       ["Target Python (on Android)", "CPython 3.14.2", "p4a recipe"],
       ["App requirements", "kivy==2.3.1, kivymd==1.2.0, pycryptodome",
        "buildozer.spec"],
       ["APK floor", "minSdk 24 / targetSdk 34 / arm64-v8a",
        "buildozer.spec"]],
      [52, 52, 70])

# ======================================================== 2 · HOW IT RUNS
chapter("2", "How the build works")
h2("2.1&nbsp;&nbsp;The two-run shape")
p("You run buildozer <b>twice</b>. Run #1 clones p4a and downloads the "
  "SDK/NDK, then halts at the license prompt (E2) — that stop is "
  "expected and useful: it gives you a complete p4a tree to patch and "
  "an SDK tree to license. Then you accept licenses, apply the 4 "
  "GHOSTWIRE patches, and run #2 compiles everything and assembles "
  "the APK.")
h2("2.2&nbsp;&nbsp;Directory map — know where things land")
table(["Path", "Owner", "Contents"],
      [["~/.buildozer/android/platform/", "buildozer", "android-sdk, "
        "android-ndk-r28c, apache-ant. Reused by every build."],
       ["ghostwire/.buildozer/", "buildozer+p4a", "p4a clone, compiled "
        "recipes, dist skeleton, staged app. Wiped by "
        "`buildozer android clean`."],
       ["ghostwire/bin/", "buildozer", "The finished APK(s)."],
       ["~/jdk-17*/", "you", "Temurin JDK (tarball path)."]],
      [62, 30, 82])
note("Golden rule",
     "Patches live in ghostwire/.buildozer, which `clean` deletes and "
     "fresh clones lack. Any time that tree is (re)created, re-run "
     "patches/apply_patches.py before the compiling run. The script is "
     "idempotent — when in doubt, just run it again.")
h2("2.3&nbsp;&nbsp;The environment block — used on all three paths")
p("Every shell that runs buildozer needs this (Colab sets it once via "
  "os.environ in §4 step 5):")
cmd(["export JAVA_HOME=$(ls -d $HOME/jdk-17* | head -1)",
     'export PATH="$JAVA_HOME/bin:$HOME/.local/bin:$PATH"',
     'export GRADLE_OPTS="-Xmx1500m -XX:MaxMetaspaceSize=512m"',
     "export KIVY_NO_ARGS=1",
     "javac -version   # must print javac 17...",
     "keytool -help 2>&1 | head -1   # must exist (buildozer needs it)"])
p("Why each line: JAVA_HOME+PATH force <b>Java 17</b> everywhere (E4); "
  "$HOME/.local/bin keeps p4a's pip-installed helpers on PATH; "
  "GRADLE_OPTS caps Gradle's heap so small machines survive; "
  "KIVY_NO_ARGS stops Kivy parsing CLI flags during the build.")

# ======================================================== 3 · CHECKLIST
chapter("3", "Project checklist")
p("The build needs this layout (names matter, the rest of the repo "
  "rides along harmlessly):")
out(["ghostwire/",
     "  main.py  icon.png  presplash.png  presplash.json",
     "  buildozer.spec            # §1.2 floor + requirements",
     "  gw/__init__.py  gw/crypto.py  gw/net.py  gw/ui.py",
     "  gw/_curve25519.py",
     "  patches/apply_patches.py  # the 4 p4a patches",
     "  patches/check_apk.py      # release verification",
     "  docker/Dockerfile  docker/build.sh  # path C only",
     "  colab/GHOSTWIRE_APK_Build.ipynb     # path A only"])
p("Key buildozer.spec lines and what they do:")
table(["Line", "Meaning"],
      [["requirements = python3,kivy==2.3.1,kivymd==1.2.0,pycryptodome",
        "Pinned recipes p4a must compile. Exact pins = reproducible."],
       ["android.api = 34 / android.minapi = 24", "targetSdk 34 "
        "(no old-SDK warning), minSdk 24 (Android 7+ install floor; "
        "supported from 10+)."],
       ["android.archs = arm64-v8a", "Modern phones only; keeps the "
        "APK to one ABI (~31 MB)."],
       ["source.exclude_dirs / exclude_patterns", "Keeps docs/, shots/, "
        "tests and relay_server.py OUT of the APK (verified §8)."],
       ["android.presplash_lottie = ./presplash.json", "Animated splash; "
        "patch 2+4 guarantee a static frame fallback."],
       ["warn_on_root = 0", "Docker builds run as root; silences the "
        "warning without changing behaviour."]],
      [88, 86])

# ============================================================== 4 · COLAB
chapter("4", "Path A — Google Colab")
p("Best when your own machine is slow, full, or Windows/macOS without "
  "Docker. Free CPU runtime is enough (12 GB RAM, no swap needed). "
  "Upload <b>colab/GHOSTWIRE_APK_Build.ipynb</b> (File → Upload "
  "notebook) and <b>Runtime → Run all</b> — or follow the cells below, "
  "which are its exact contents. Keep the tab open; the 12-hour limit "
  "is far beyond the ~1 hour a cold build needs.")
h2("4.1&nbsp;&nbsp;Cell 1 — system packages (~2 min)")
cmd(["!apt-get update -qq && apt-get install -qq -y git zip unzip autoconf libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev python3-pip"])
h2("4.2&nbsp;&nbsp;Cell 2 — JDK 17 Temurin (~1 min)")
p("Colab ships Java 11; Gradle 8 + AGP demand 17 (E4). This is the "
  "same tarball the release used:")
cmd(['!cd /root && curl -sL -o jdk17.tar.gz "https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse"',
     "!tar xzf jdk17.tar.gz && /root/jdk-17*/bin/java -version"])
out(["openjdk version \"17.0.20.1\" ... (any 17.x is fine)"])
h2("4.3&nbsp;&nbsp;Cell 3 — buildozer + cython")
cmd(["!pip3 install -q buildozer cython && buildozer --version && cython --version"])
out(["Buildozer 1.6.0"])
h2("4.4&nbsp;&nbsp;Cell 4 — get the source")
cmd(["!cd /content && ( [ -d ghostwire/.git ] && git -C ghostwire pull || git clone https://github.com/YOU/ghostwire.git ) && ls ghostwire"])
p("Replace the URL with your repo. Zip alternative: upload ghostwire.zip "
  "to /content, then `!cd /content &amp;&amp; rm -rf ghostwire &amp;&amp; unzip -q "
  "ghostwire.zip`.")
h2("4.5&nbsp;&nbsp;Cell 5 — environment (Python cell, NOT shell)")
p("Each `!` shell forgets exports; os.environ persists for the whole "
  "session — that is why this cell is Python:")
cmd(["import os",
     'os.environ["JAVA_HOME"] = "/root/jdk-17.0.20.1+1"',
     'os.environ["PATH"] = "/root/jdk-17.0.20.1+1/bin:" + os.environ["PATH"]',
     'os.environ["GRADLE_OPTS"] = "-Xmx1500m -XX:MaxMetaspaceSize=512m"',
     'os.environ["KIVY_NO_ARGS"] = "1"'])
note("Version drift",
     "If Adoptium has released a newer 17.x, the folder name differs. "
     "List /root/jdk-17* and adjust the two paths — everything else is "
     "identical.", amber=True)
h2("4.6&nbsp;&nbsp;Cell 6 — run #1: fetch platform (stops at licenses)")
cmd(["!cd /content/ghostwire && buildozer android debug > /tmp/b1.log 2>&1 || true",
     "!tail -4 /tmp/b1.log",
     '!grep -q "Aidl not found" /tmp/b1.log && echo "OK: reached license stage (expected stop)"'])
p("The `|| true` is deliberate: run #1 is *supposed* to fail here (E2). "
  "The grep proves it failed at the right place. Downloads take "
  "~15 min on Colab's network.")
h2("4.7&nbsp;&nbsp;Cell 7 — accept SDK licenses (~1 min)")
cmd(["!SM=/root/.buildozer/android/platform/android-sdk/tools/bin/sdkmanager; yes | $SM --sdk_root=/root/.buildozer/android/platform/android-sdk --licenses 2>&1 | tail -2"])
out(["Accept? (y/N): All SDK package licenses accepted"])
p("The `yes |` answers every prompt; `--sdk_root` is mandatory in this "
  "SDK layout (E3). Eight licenses accept; the build-tools that run #1 "
  "missed will now install on run #2.")
h2("4.8&nbsp;&nbsp;Cell 8 — apply the 4 p4a patches")
cmd(["!cd /content/ghostwire && python3 patches/apply_patches.py"])
p("Expect five OK/SKIP lines (§7). Run #1 created the p4a tree; this "
  "is the only window where patching is needed or possible.")
h2("4.9&nbsp;&nbsp;Cell 9 — run #2: the build (30–60 min)")
cmd(["!cd /content/ghostwire && buildozer android debug 2>&1 | tee /tmp/b2.log | grep --line-buffered -E \"Downloading|Recipe |BUILD|available in the bin\" | tail -60",
     "!ls -la /content/ghostwire/bin/"])
p("The grep streams *milestones* live (otherwise the cell looks dead "
  "for an hour) while tee keeps the full log at /tmp/b2.log for "
  "debugging (§9). Success ends with:")
out(["# APK ghostwire-1.1.0-arm64-v8a-debug.apk available in the bin directory",
     "-rw-r--r-- 1 root root 30730061 ... ghostwire-1.1.0-arm64-v8a-debug.apk"])
h2("4.10&nbsp;&nbsp;Cell 10 — verify + download")
cmd(["!cd /content/ghostwire && python3 patches/check_apk.py bin/ghostwire-1.1.0-arm64-v8a-debug.apk",
     "from google.colab import files",
     'files.download("/content/ghostwire/bin/ghostwire-1.1.0-arm64-v8a-debug.apk")'])
p("check_apk prints ~20 PASS lines (§8), then the APK downloads to "
  "your computer. Sideload and go.")
note("Colab amnesia",
     "A recycled runtime loses EVERYTHING (SDK, recipes, patches). "
     "Recovery is just Runtime → Run all again (~1 h). Optionally "
     "mount Drive and copy bin/*.apk there at the end so the artifact "
     "survives even if the download is missed.", amber=True)

# ============================================================= 5 · UBUNTU
chapter("5", "Path B — Ubuntu 22.04 / 24.04 (PC or VM)")
p("The native path. Steps mirror Colab, with sudo and a couple of "
  "Ubuntu conveniences. Assumes an x86_64 machine with 15 GB free disk.")
h2("5.1&nbsp;&nbsp;System packages")
cmd(["sudo apt-get update && sudo apt-get install -y git zip unzip autoconf libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev python3-pip"])
h2("5.2&nbsp;&nbsp;JDK 17 — two good options")
p("Option 1 — distro package (simplest on Ubuntu; it exists here, "
  "unlike some Debian spins):")
cmd(["sudo apt-get install -y openjdk-17-jdk-headless",
     "export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64",
     "$JAVA_HOME/bin/javac -version   # expect javac 17..."])
p("Option 2 — Temurin tarball (byte-identical to the release "
  "environment):")
cmd(['cd ~ && curl -sL -o jdk17.tar.gz "https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse"',
     "tar xzf jdk17.tar.gz && ~/jdk-17*/bin/java -version"])
h2("5.3&nbsp;&nbsp;Python build tools")
cmd(["pip3 install --break-system-packages -q buildozer cython",
     "buildozer --version   # expect 1.6.0"])
p("The --break-system-packages flag is required on Ubuntu 24.04+ "
  "(E11); on 22.04 it is accepted harmlessly. Prefer a venv? Create "
  "one and drop the flag — but then activate it in EVERY shell that "
  "runs buildozer.")
h2("5.4&nbsp;&nbsp;Source + environment + run #1 + licenses + patches")
cmd(["cd ~ && git clone https://github.com/YOU/ghostwire.git && cd ghostwire",
     "export JAVA_HOME=$(ls -d $HOME/jdk-17* /usr/lib/jvm/java-17-openjdk-amd64 2>/dev/null | head -1)",
     'export PATH="$JAVA_HOME/bin:$HOME/.local/bin:$PATH"',
     'export GRADLE_OPTS="-Xmx1500m -XX:MaxMetaspaceSize=512m"',
     "export KIVY_NO_ARGS=1",
     "buildozer android debug 2>&1 | tee /tmp/buildozer.log   # stops at licenses (E2)",
     "SM=$HOME/.buildozer/android/platform/android-sdk/tools/bin/sdkmanager",
     "yes | $SM --sdk_root=$HOME/.buildozer/android/platform/android-sdk --licenses",
     "python3 patches/apply_patches.py"])
p("Consider appending the four exports to ~/.bashrc so every terminal "
  "is build-ready. Then run #2 and verify exactly as in §4.9–4.10 "
  "(without the `!` and files.download).")
h2("5.5&nbsp;&nbsp;Low-RAM machines (2 GB): add swap first")
p("The kivy recipe's -O3 clang lines will OOM-thrash a 2 GB box (E6). "
  "This exact sequence saved the release build:")
cmd(["sudo fallocate -l 3G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile",
     "free -m | head -3   # Swap: ~3071"])
p("Keep the swapfile until the build finishes; remove afterwards with "
  "`sudo swapoff /swapfile &amp;&amp; sudo rm /swapfile` if desired.")

# ============================================================= 6 · DOCKER
chapter("6", "Path C — Docker (any OS that runs Docker)")
p("Fully scripted: the image carries the toolchain, build.sh performs "
  "all five stages, and the APK lands back on your host. Files live in "
  "the repo under docker/ and are printed here verbatim.")
h2("6.1&nbsp;&nbsp;Prerequisites")
bullets([
    "Docker with ≥15 GB free image/container space.",
    "Linux/macOS/Windows host — the container is always Ubuntu 24.04 "
    "x86_64. Apple Silicon: add <b>--platform linux/amd64</b> to every "
    "docker command (SDK/NDK are x86_64-only; emulation is slower but "
    "works).",
])
h2("6.2&nbsp;&nbsp;docker/Dockerfile (as shipped)")
out(["FROM ubuntu:24.04",
     "ENV DEBIAN_FRONTEND=noninteractive \\",
     "    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \\",
     "    GRADLE_OPTS=\"-Xmx1500m -XX:MaxMetaspaceSize=512m\" \\",
     "    KIVY_NO_ARGS=1",
     "ENV PATH=\"$JAVA_HOME/bin:/root/.local/bin:$PATH\"",
     "RUN apt-get update && apt-get install -y --no-install-recommends \\",
     "        git zip unzip autoconf libtool pkg-config \\",
     "        zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev \\",
     "        python3-pip openjdk-17-jdk-headless \\",
     "    && rm -rf /var/lib/apt/lists/* \\",
     "    && pip3 install --break-system-packages --no-cache-dir \\",
     "        buildozer cython \\",
     "    && buildozer --version && javac -version",
     "WORKDIR /src",
     "COPY . /src/",
     "CMD [\"/src/docker/build.sh\"]"])
p("Notes: Ubuntu 24.04 supplies OpenJDK 17 via apt, so no tarball is "
  "needed inside the image; .dockerignore keeps SDK-sized junk and the "
  "300-page PDF out of the build context.")
h2("6.3&nbsp;&nbsp;docker/build.sh — the five stages (as shipped)")
out(["#!/bin/bash",
     "# [1/5] run #1 (license stop expected)",
     "buildozer android debug > /tmp/buildozer1.log 2>&1 || true",
     'grep -qa "Aidl not found" /tmp/buildozer1.log || exit 1',
     "# [2/5] licenses",
     'SM=/root/.buildozer/.../android-sdk/tools/bin/sdkmanager',
     'yes | "$SM" --sdk_root=/root/.buildozer/.../android-sdk --licenses',
     "# [3/5] patches",
     "python3 patches/apply_patches.py /src || exit 1",
     "# [4/5] run #2 (recipes + gradle)",
     "buildozer android debug 2>&1 | tee /tmp/buildozer2.log | tail -3",
     "# [5/5] verify, fail loudly otherwise",
     'python3 patches/check_apk.py "${APK[0]}" || exit 1'])
p("Each stage gates the next: a wrong run-#1 failure, a patch miss, or "
  "a failed audit aborts with the log path — never a silent bad APK.")
h2("6.4&nbsp;&nbsp;Build, run, collect")
cmd(['cd ghostwire && docker build -t ghostwire-builder -f docker/Dockerfile .',
     'docker run --rm -v "$PWD/bin:/src/bin" ghostwire-builder',
     "ls -la bin/   # ghostwire-1.1.0-arm64-v8a-debug.apk (~31 MB)"])
p("The bind mount is what carries the APK out — without it the "
  "artifact dies with the container. First run ≈1 h; for minute-scale "
  "rebuilds, persist the SDK + recipes across runs:")
cmd(['docker volume create gw-android-sdk',
     'docker run --rm -v "$PWD/bin:/src/bin" -v gw-android-sdk:/root/.buildozer -v "$PWD/.buildozer:/src/.buildozer" ghostwire-builder'])
note("Root is fine here",
     "The container runs as root and buildozer.spec sets warn_on_root "
     "= 0, so no prompt or warning interrupts the scripted flow.",
     amber=True)

# ============================================================= 7 · PATCHES
chapter("7", "The 4 p4a patches — what, why, and proof")
p("python-for-android ships a generic bootstrap; GHOSTWIRE needs four "
  "surgical changes. patches/apply_patches.py applies them to the "
  "fresh p4a clone (verified against master @ 58d21141) and skips any "
  "already present.")
table(["#", "File", "Change", "If skipped"],
      [["1", "_sdl_common/.../AndroidManifest.tmpl.xml",
        "android:windowSoftInputMode=\"adjustPan\" on the entrypoint "
        "activity.", "Soft keyboard covers the chat composer."],
       ["2", "common/build/build.py", "Copy the static presplash frame "
        "even in the lottie branch.", "No fallback image (§8 asset "
        "check fails)."],
       ["3", "common/build/templates/kivy-presplash.jpg",
        "Replaced with the project's presplash.png art.", "Generic "
        "Kivy splash art."],
       ["4", "sdl2/.../PythonActivity.java",
        "attachLottieFailureListener + swapToStaticSplash (+ imports): "
        "a broken animation swaps to the static frame via reflection.",
        "Black seconds when lottie fails; risk of the E5 arity bug if "
        "hand-edited."]],
      [10, 52, 62, 50])
h2("7.1&nbsp;&nbsp;Running it + expected output")
cmd(["cd ~/ghostwire && python3 patches/apply_patches.py"])
out(["--- 1/4 manifest adjustPan",
     "    OK",
     "--- 2/4 static presplash in lottie branch",
     "    OK",
     "--- 3/4 presplash art",
     "    OK (copied .../presplash.png)",
     "--- 4a/4 Java imports",
     "    OK",
     "--- 4b/4 Java failure-swap",
     "    OK",
     "",
     "ALL PATCHES APPLIED (or already present)."])
p("Re-running prints SKIP lines — that is the idempotency check, not "
  "an error. ANCHOR NOT FOUND means your p4a is newer than 58d21141 "
  "and moved the surrounding code: inspect the named file by hand "
  "rather than forcing it.")

# ============================================================== 8 · VERIFY
chapter("8", "Verification — prove the APK before you ship it")
p("Run the auditor (it finds aapt inside the SDK buildozer installed):")
cmd(["cd ~/ghostwire && python3 patches/check_apk.py bin/ghostwire-1.1.0-arm64-v8a-debug.apk"])
out(["aapt: .../android-sdk/build-tools/34.0.0/aapt",
     "apk : bin/ghostwire-1.1.0-arm64-v8a-debug.apk (29 MB)",
     "PASS versionName is 1.1.0",
     "PASS minSdk 24 (0x18)",
     "PASS targetSdk 34 (0x22)",
     "PASS allowBackup=false",
     "PASS adjustPan (0x20)",
     "PASS static presplash bundled",
     "PASS lottie splash bundled",
     "PASS ships on_inbound_request",
     "PASS ships REQUESTS A CHAT",
     "PASS ships relay_connect",
     "PASS ships WAN RELAY",
     "PASS ships ttl_label",
     "PASS ships REQUEST_TIMEOUT",
     "PASS ships 1.1.0",
     "PASS no residue: SessionChip ... (x7)",
     "PASS docs/ excluded",
     "PASS tests excluded",
     "PASS relay_server.py excluded (stays server-side)",
     "RESULT: OK"])
h2("8.1&nbsp;&nbsp;The same checks by hand (when you want to see it)")
cmd(["AAPT=$(ls $HOME/.buildozer/android/platform/android-sdk/build-tools/*/aapt | head -1)",
     "$AAPT dump xmltree bin/*.apk AndroidManifest.xml | grep -i \"softInputMode\\|allowBackup\\|targetSdkVersion\\|minSdkVersion\\|versionName\"",
     "unzip -l bin/*.apk | grep -E \"presplash|splashscreen\""])
out(['A: android:versionName(0x0101021c)="1.1.0"',
     "A: android:minSdkVersion(0x0101020c)=(type 0x10)0x18",
     "A: android:targetSdkVersion(0x01010270)=(type 0x10)0x22",
     "A: android:allowBackup(0x01010280)=(type 0x12)0x0",
     "A: android:windowSoftInputMode(0x0101022b)=(type 0x11)0x20",
     "    17519  ...   res/drawable/presplash.jpg",
     "     6916  ...   res/raw/splashscreen.json"])
p("Read it as: right version, Android 7+ installs / modern target "
  "(no stale-SDK warning), no ADB-backup key exfil, keyboard pans, "
  "both splash assets present. The bytecode half (markers in/out) is "
  "what check_apk.py's private.tar audit adds on top.")

# ============================================================== 9 · ERRORS
chapter("9", "Error catalog — every failure I hit, decoded")
p("Rule zero: buildozer prints `gradlew failed!` for everything. The "
  "real cause is always a few dozen lines up:")
cmd(["grep -a \"What went wrong\" -A 12 /tmp/buildozer.log | tail -20"])
table(["ID", "Signature line", "One-line fix"],
      [["E1", "Java compiler (javac) not found", "JDK bin dir on PATH."],
       ["E2", "Aidl not found, please install it.", "Accept SDK licenses."],
       ["E3", "sdkmanager: Could not create settings", "Add --sdk_root."],
       ["E4", "AGP requires Java 17 ... using Java 11", "Build under JDK 17."],
       ["E5", "getIdentifier ... cannot be applied", "Use the patch script."],
       ["E6", "internal compiler error: Killed / thrash", "Add swap / RAM."],
       ["E7", "gradlew failed! (generic)", "Grep “What went wrong”."],
       ["E8", "Permission denied / missing 'server' JVM", "Re-extract JDK."],
       ["E9", "Colab tab died mid-build", "Rerun all; keep tab open."],
       ["E10", "Docker: no space / exec format error", "Free 15 GB / amd64."],
       ["E11", "externally-managed-environment (pip)", "Add the pip flag."],
       ["E12", "Cythonize errors under kivy", "Pin cython==0.29.37."]],
      [12, 78, 84])
h2("9.1&nbsp;&nbsp;E1 — javac / keytool not found")
out(["# Search for Java compiler (javac)",
     "# Java compiler (javac) not found, please install it."])
p("Meaning: buildozer scans PATH and found no JDK. Even with Java "
  "installed, the check fails if its bin/ is not on PATH — this bit "
  "me on every fresh shell. Fix: export the §2.3 block (mind the "
  "order: JDK first) and re-run. Verify with `javac -version` + "
  "`keytool -help` before rebuilding.")
h2("9.2&nbsp;&nbsp;E2 — Aidl not found (the license stop)")
out(["# Check that aidl can be executed",
     "# build-tools folder not found .../android-sdk/build-tools",
     "# Aidl not found, please install it."])
p("Meaning: build-tools never installed because the SDK licenses were "
  "never accepted — buildozer cannot click through the interactive "
  "prompt, so installation silently skipped. It is *not* fixed by apt. "
  "Fix (§4.7/§5.4): `yes | sdkmanager --sdk_root=... --licenses`, "
  "confirm “All SDK package licenses accepted”, re-run buildozer.")
h2("9.3&nbsp;&nbsp;E3 — sdkmanager settings crash")
out(["Warning: Could not create settings",
     "java.lang.IllegalArgumentException",
     "    at ...SdkManagerCliSettings.<init>..."])
p("Meaning: this SDK layout (tools/ instead of cmdline-tools/latest/) "
  "forces you to pass --sdk_root explicitly. Fix: add the flag exactly "
  "as in §4.7. Any sdkmanager invocation in this guide without it will "
  "die the same way.")
h2("9.4&nbsp;&nbsp;E4 — Gradle wants Java 17, found Java 11")
out(["* What went wrong:",
     "Android Gradle plugin requires Java 17 ... currently using Java 11"])
p("Meaning: Gradle/AGP 8 run only on 17+. The system java (often 11 on "
  "Colab/older images) won the PATH race. Fix: the §2.3 block with "
  "JAVA_HOME + JDK-first PATH, exported in the SAME shell/cell that "
  "runs buildozer — and on Colab, via os.environ (§4.5), not `!export`.")
h2("9.5&nbsp;&nbsp;E5 — getIdentifier arity (patch bug class)")
out(["PythonActivity.java:419: error: method getIdentifier in class",
     "ResourceManager cannot be applied to given types;",
     "    required: String,String",
     "    found:    String,String,String"])
p("Meaning: p4a's ResourceManager.getIdentifier takes 2 args; a "
  "3-argument call (this guide's author's own first draft) fails "
  "compileDebugJavaWithJavac. Fix: use patches/apply_patches.py, which "
  "ships the corrected 2-arg call — never hand-edit the Java unless "
  "the script reports anchor drift (§7.1).")
h2("9.6&nbsp;&nbsp;E6 — compiler Killed / box thrashing")
out(["c++: internal compiler error: Killed (program cc1plus)",
     "# kswapd at 40%+, load 10+, everything frozen"])
p("Meaning: the OOM killer shot a clang during kivy's -O3 compile — "
  "2 GB RAM with no swap cannot hold it. Fix: the §5.5 swapfile "
  "(release-proven on a 2 GB box), close browsers, or raise the "
  "Docker/VM memory to 4 GB+. The build resumes where it died: just "
  "re-run buildozer.")
h2("9.7&nbsp;&nbsp;E7 — generic gradlew failure")
p("`ERROR: .../dists/ghostwire/gradlew failed!` alone diagnoses "
  "nothing; twice it sent me hunting the wrong layer. Always pull the "
  "Gradle block first with the rule-zero grep at the top of this "
  "chapter — E4 and E5 both surfaced exactly that way.")
h2("9.8&nbsp;&nbsp;E8 — JDK lost its edge (restores, copies, snapshots)")
out([".../bin/java: Permission denied",
     "Error: missing `server' JVM at `.../lib/server/libjvm.so'"])
p("Meaning: exec bits stripped (first line) or the tree partially "
  "copied (second — a snapshot once kept 95 of ~300 MB). Fix: "
  "`chmod -R +x` the bin/ dir for the first; for the second, delete "
  "and re-extract the tarball — never trust a half JDK.")
h2("9.9&nbsp;&nbsp;E9 — Colab interruptions")
p("A closed laptop, a throttled tab, or the 12-hour cap kills the VM "
  "and with it ~/.buildozer and the p4a tree — there is no resume. "
  "Prevention: keep the tab focused during run #2 (its milestone grep "
  "keeps output alive); recovery: Runtime → Run all from the top "
  "(~1 h). Save finished APKs to Drive, not just downloads (§4.10).")
h2("9.10&nbsp;&nbsp;E10 — Docker space / architecture")
out(["no space left on device",
     "exec /src/docker/build.sh: exec format error"])
p("Meaning 1: image + SDK + recipes exceed free Docker disk — free "
  "15 GB (`docker system prune -a` if desperate) and rebuild. "
  "Meaning 2 (Apple Silicon): the image built for arm64 but the NDK "
  "is x86_64-only — rebuild AND run with `--platform linux/amd64`.")
h2("9.11&nbsp;&nbsp;E11 — pip refuses (externally managed)")
out(["error: externally-managed-environment",
     "This environment is externally managed"])
p("Meaning: Ubuntu 24.04+/Debian 13 PEP 668 guard. Fix: add "
  "`--break-system-packages` (container/Colab/throwaway VM — safe) or "
  "use a venv you activate in every build shell.")
h2("9.12&nbsp;&nbsp;E12 — Cython version skew (fallback pin)")
p("The release compiled clean on Cython 3.x (pip latest). If a future "
  "Cython breaks kivy 2.3.1's cythonize step, pin the legacy line "
  "kivy grew up with, then rebuild:")
cmd(["pip3 install --break-system-packages -q \"cython==0.29.37\"",
     "cython --version   # expect 0.29.37"])

# =========================================================== 10 · REBUILDS
chapter("10", "Rebuilds and iteration")
p("Run #2 is incremental: SDK/NDK (in ~/.buildozer) and compiled "
  "recipes (in ghostwire/.buildozer) are reused, so a code edit "
  "rebuilds in minutes:")
cmd(["cd ~/ghostwire   # env block active (§2.3)",
     "# edit gw/*.py, main.py, presplash.json ...",
     "buildozer android debug 2>&1 | tee /tmp/rebuild.log | tail -3",
     "python3 patches/check_apk.py bin/ghostwire-1.1.0-arm64-v8a-debug.apk"])
table(["You changed", "Do this", "Cost"],
      [["App Python / art / json", "Re-run buildozer.", "Minutes."],
       ["buildozer.spec requirements", "Re-run; new recipes compile.",
        "Minutes–tens of minutes."],
       ["version = line", "Re-run; filename follows it.", "Minutes."],
       ["Need a clean tree", "`buildozer android clean`, then run #1 → "
        "licenses (kept) → patches → run #2.", "Full cold build; "
        "patches MUST be re-applied."]],
      [58, 68, 48])
note("The clean trap",
     "`buildozer android clean` deletes the p4a tree — and your four "
     "patches with it. The very next compiling run without re-patching "
     "ships a keyboard-covering, splash-fragile APK that still "
     "installs fine. check_apk.py exists to catch exactly that.",
     amber=True)

# =========================================================== 11 · GO/FAQ
chapter("11", "Pre-flight checklist and FAQ")
h2("11.1&nbsp;&nbsp;Pre-flight (2 minutes, saves hours)")
bullets([
    "☐ &nbsp;15 GB free disk (E10) · 4 GB RAM or swapfile ready (E6).",
    "☐ &nbsp;Env block exported in THIS shell (E1/E4): javac -version "
    "prints 17, keytool exists.",
    "☐ &nbsp;On a fresh p4a tree: licenses accepted (E2) AND patches "
    "applied (§7) before the compiling run.",
    "☐ &nbsp;Colab: tab stays open, files.download cell kept (§4.10).",
    "☐ &nbsp;Docker: bin/ bind-mounted or the APK dies with the "
    "container (§6.4).",
    "☐ &nbsp;After every build: check_apk.py RESULT: OK (§8).",
])
h2("11.2&nbsp;&nbsp;What worked for me (the whole guide in one box)")
note("Golden path",
     "Debian 13 x86_64, 2 GB RAM + 3 GB swapfile, host Python 3.13, "
     "buildozer 1.6.0 + Cython 3.x from pip, Temurin JDK 17 tarball, "
     "run #1 to the license stop, yes-pipe license accept, the four "
     "patches, run #2 to BUILD SUCCESSFUL, check_apk RESULT: OK. "
     "Elapsed: about an hour cold, minutes warm. The Colab notebook "
     "and the Dockerfile are that exact sequence, automated.")
h2("11.3&nbsp;&nbsp;FAQ")
bullets([
    "<b>Is the APK signed?</b> Yes — debug-signed by Gradle. It "
    "sideloads on any phone. Play-Store release signing (keystore, "
    "zipalign, apksigner) is a separate, well-documented process and "
    "deliberately out of scope here.",
    "<b>Windows / macOS without Docker?</b> Use Colab (Path A) — the "
    "notebook needs only a browser.",
    "<b>Can I bump the NDK / Gradle / AGP?</b> Only if p4a's master "
    "moves first; the recipe toolchain is version-coupled. Pin to §1.2 "
    "unless you enjoy E5-class archaeology.",
    "<b>Where do logs live?</b> Wherever you tee'd them "
    "(/tmp/buildozer.log in this guide). Keep run #2's log with every "
    "release — it is the build's audit trail.",
    "<b>How do I update p4a later?</b> Delete "
    ".buildozer/android/platform/python-for-android, re-run run #1, "
    "re-accept nothing (licenses persist), re-apply patches (watch "
    "for anchor drift), run #2.",
])
story.append(Spacer(1, 10 * mm))
p("End of guide. Ship verified builds — <b>developed by @Ariko &amp; "
  "Arena</b>.")

# ================================================================= BUILD
doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm,
                      rightMargin=18 * mm, topMargin=18 * mm,
                      bottomMargin=20 * mm,
                      title="GHOSTWIRE APK Build Guide v1.1.0",
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
    if isinstance(flowable, Paragraph):
        if flowable.style.name == "h1":
            doc.notify("TOCEntry", (0, flowable.getPlainText(), doc.page))


doc.afterFlowable = _after_flowable
doc.multiBuild(story)

from pypdf import PdfReader  # noqa: E402
pages = len(PdfReader(OUT).pages)
print(f"BUILDGUIDE BUILT: {OUT} pages: {pages}")
if pages > MAX_PAGES:
    raise SystemExit(f"PAGE BUDGET EXCEEDED: {pages} > {MAX_PAGES}")

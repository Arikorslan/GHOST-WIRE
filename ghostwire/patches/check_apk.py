#!/usr/bin/env python3
"""Verify a GHOSTWIRE APK the same way the release was verified.

Checks:
  * manifest  - versionName, min/target SDK, allowBackup=false,
                windowSoftInputMode=adjustPan (0x20)
  * assets    - static presplash + lottie splash bundled
  * bytecode  - v1.1.0 markers present, removed multi-session code
                absent, no docs/tests/relay sources in the bundle

Usage:
    python3 patches/check_apk.py bin/ghostwire-1.1.0-arm64-v8a-debug.apk

Needs `aapt` (ships with the SDK build-tools buildozer installs).
"""
import glob
import io
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name +
          (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def find_aapt():
    roots = [os.environ.get("ANDROID_SDK_ROOT", ""),
             os.path.expanduser("~/.buildozer/android/platform/android-sdk")]
    for r in roots:
        hits = sorted(glob.glob(os.path.join(r, "build-tools", "*", "aapt")))
        if hits:
            return hits[-1]
    return shutil.which("aapt")


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python3 patches/check_apk.py <app.apk>")
    apk_path = sys.argv[1]
    aapt = find_aapt()
    if not aapt:
        sys.exit("aapt not found - run a build first (build-tools install "
                 "with the SDK) or set ANDROID_SDK_ROOT.")
    print("aapt:", aapt)
    print("apk :", apk_path,
          f"({os.path.getsize(apk_path) // 1024 // 1024} MB)")

    xml = subprocess.run([aapt, "dump", "xmltree", apk_path,
                          "AndroidManifest.xml"],
                         capture_output=True, text=True).stdout
    check("versionName is 1.1.0", 'versionName(0x0101021c)="1.1.0"' in xml)
    check("minSdk 24 (0x18)", "minSdkVersion(0x0101020c)=(type 0x10)0x18" in xml)
    check("targetSdk 34 (0x22)",
          "targetSdkVersion(0x01010270)=(type 0x10)0x22" in xml)
    check("allowBackup=false", "allowBackup(0x01010280)=(type 0x12)0x0" in xml)
    check("adjustPan (0x20)",
          "windowSoftInputMode(0x0101022b)=(type 0x11)0x20" in xml)

    names = subprocess.run([aapt, "list", apk_path], capture_output=True,
                           text=True).stdout.splitlines()
    check("static presplash bundled", "res/drawable/presplash.jpg" in names)
    check("lottie splash bundled", "res/raw/splashscreen.json" in names)

    apk = zipfile.ZipFile(apk_path)
    tar = tarfile.open(fileobj=io.BytesIO(apk.read("assets/private.tar")))
    mods, bundle = {}, []
    for m in tar.getmembers():
        bundle.append(m.name)
        if m.name.endswith(("gw/ui.pyc", "gw/net.pyc", "gw/__init__.pyc")):
            mods[m.name] = tar.extractfile(m).read().decode("latin1")
    code = "\n".join(mods.values())
    for marker in ("on_inbound_request", "REQUESTS A CHAT", "relay_connect",
                   "WAN RELAY", "ttl_label", "REQUEST_TIMEOUT", "1.1.0"):
        check(f"ships {marker}", marker in code)
    for gone in ("SessionChip", "session_strip", "MAX_PEERS",
                 "disconnect_all", "switch_session", "active_sid",
                 "SESSION LIMIT"):
        check(f"no residue: {gone}", gone not in code)
    check("docs/ excluded",
          not any(n.startswith("docs/") or "/docs/" in n for n in bundle))
    check("tests excluded",
          not any("test_v110" in n or "test_multilink" in n for n in bundle))
    check("relay_server.py excluded (stays server-side)",
          not any("relay_server" in n for n in bundle))

    print("RESULT:", "OK" if not FAILS else f"FAILED {FAILS}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())

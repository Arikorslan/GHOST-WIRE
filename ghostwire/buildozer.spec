[app]
title = GHOSTWIRE
package.name = ghostwire
package.domain = org.ghostwire
version = 1.1.0

source.dir = .
source.include_exts = py,png
source.exclude_dirs = shots,.buildozer,.git,__pycache__,docs
source.exclude_patterns = test_v110.py,test_multilink.py,relay_server.py

requirements = python3,kivy==2.3.1,kivymd==1.2.0,pycryptodome

orientation = portrait
fullscreen = 0

icon.filename = ./icon.png
android.presplash_color = #0B0E0B
android.presplash_lottie = ./presplash.json
android.allow_backup = False

android.api = 34
android.minapi = 24
android.archs = arm64-v8a

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN

# p4a / build
p4a.bootstrap = sdl2
android.entrypoint = org.kivy.android.PythonActivity

[buildozer]
log_level = 2
warn_on_root = 0

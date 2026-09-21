#!/bin/bash
# Full GHOSTWIRE APK build inside the docker image.
# Run #1 clones p4a + fetches SDK/NDK, then stops at the license
# stage (expected) -> accept licenses -> apply p4a patches ->
# run #2 compiles recipes and assembles the APK.
set -u
cd /src

echo "=== [1/5] buildozer run #1 (platform fetch; license stop expected)"
buildozer android debug > /tmp/buildozer1.log 2>&1 || true
if ! grep -qa "Aidl not found" /tmp/buildozer1.log; then
    echo "UNEXPECTED: run #1 did not reach the license stage. Tail:"
    tail -20 /tmp/buildozer1.log
    exit 1
fi
echo "    reached license stage as expected"

echo "=== [2/5] accepting SDK licenses"
SM=/root/.buildozer/android/platform/android-sdk/tools/bin/sdkmanager
yes | "$SM" --sdk_root=/root/.buildozer/android/platform/android-sdk \
    --licenses > /tmp/licenses.log 2>&1
grep -a "All SDK package licenses accepted" /tmp/licenses.log

echo "=== [3/5] applying GHOSTWIRE p4a patches"
python3 patches/apply_patches.py /src || exit 1

echo "=== [4/5] buildozer run #2 (recipes + gradle, ~30-60 min)"
buildozer android debug 2>&1 | tee /tmp/buildozer2.log | tail -3
APK=(bin/ghostwire-*-arm64-v8a-debug.apk)
[ -f "${APK[0]}" ] || { echo "BUILD FAILED - see /tmp/buildozer2.log"; exit 1; }

echo "=== [5/5] verifying ${APK[0]}"
python3 patches/check_apk.py "${APK[0]}" || exit 1
echo "DONE: ${APK[0]}"

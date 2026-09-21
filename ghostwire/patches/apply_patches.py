#!/usr/bin/env python3
"""Apply the 4 GHOSTWIRE patches to a python-for-android checkout.

When to run: AFTER buildozer has cloned python-for-android (i.e. after
your first `buildozer android debug`, which stops at the SDK-license
stage), and BEFORE the build that compiles recipes / renders the
bootstrap. Safe to re-run: every patch is skipped when already present.

Usage:
    python3 patches/apply_patches.py [PROJECT_ROOT]

PROJECT_ROOT defaults to the directory containing `patches/`.
The p4a tree is expected at
    <PROJECT_ROOT>/.buildozer/android/platform/python-for-android
or in $P4A_DIR.

Verified against p4a master @ 58d21141 (release-2026.05.09). If a
future p4a moves the anchor text, the script aborts with the file and
line to inspect by hand instead of writing a broken patch.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
P4A = os.environ.get(
    "P4A_DIR",
    os.path.join(PROJECT, ".buildozer", "android", "platform",
                 "python-for-android"),
)
BS = os.path.join(P4A, "pythonforandroid", "bootstraps")

FAILURES = []


def patch(name, path, old, new, marker):
    print(f"--- {name}")
    print(f"    {path}")
    if not os.path.isfile(path):
        print("    MISSING FILE - is the p4a clone complete?")
        FAILURES.append(name)
        return
    src = open(path).read()
    if marker in src:
        print("    SKIP (already applied)")
        return
    if old not in src:
        print("    ANCHOR NOT FOUND - p4a source drifted; patch by hand.")
        print("    Expected anchor starts with: %r" % old[:80])
        FAILURES.append(name)
        return
    open(path, "w").write(src.replace(old, new, 1))
    print("    OK")


def main():
    if not os.path.isdir(BS):
        sys.exit(f"p4a bootstraps not found at {BS}\n"
                 "Run `buildozer android debug` once first so buildozer "
                 "clones python-for-android, then re-run this script.")

    # -- Patch 1: keyboard pans the window instead of covering inputs --
    mp = os.path.join(BS, "_sdl_common", "build", "templates",
                      "AndroidManifest.tmpl.xml")
    patch("1/4 manifest adjustPan", mp,
          '        <activity android:name="{{args.android_entrypoint}}"\n'
          '                  android:label="@string/app_name"\n',
          '        <activity android:name="{{args.android_entrypoint}}"\n'
          '                  android:label="@string/app_name"\n'
          '                  android:windowSoftInputMode="adjustPan"\n',
          "adjustPan")

    # -- Patch 2: always bundle the static splash frame ---------------
    bp = os.path.join(BS, "common", "build", "build.py")
    patch("2/4 static presplash in lottie branch", bp,
          "            shutil.copy(\n"
          "                args.presplash_lottie,\n"
          "                join(res_dir, 'raw/splashscreen.json')\n"
          "            )\n"
          "        else:",
          "            shutil.copy(\n"
          "                args.presplash_lottie,\n"
          "                join(res_dir, 'raw/splashscreen.json')\n"
          "            )\n"
          "            # GHOSTWIRE: always bundle the static frame too, so the\n"
          "            # Java failure listener has something to swap to when the\n"
          "            # lottie animation cannot load (no dark seconds, ever).\n"
          "            shutil.copy(\n"
          "                args.presplash or default_presplash,\n"
          "                join(res_dir, 'drawable/presplash.jpg')\n"
          "            )\n"
          "        else:",
          "always bundle the static frame")

    # -- Patch 3: our art as the default static splash ----------------
    print("--- 3/4 presplash art")
    art_src = os.path.join(PROJECT, "presplash.png")
    art_dst = os.path.join(BS, "common", "build", "templates",
                           "kivy-presplash.jpg")
    if not os.path.isfile(art_src):
        print(f"    MISSING {art_src}")
        FAILURES.append("3/4 presplash art")
    else:
        shutil.copy(art_src, art_dst)
        print(f"    OK (copied {art_src})")

    # -- Patch 4a: reflection imports ---------------------------------
    jp = os.path.join(BS, "sdl2", "build", "src", "main", "java",
                      "org", "kivy", "android", "PythonActivity.java")
    patch("4a/4 Java imports", jp,
          "import java.lang.reflect.InvocationTargetException;\n",
          "import java.lang.reflect.InvocationHandler;\n"
          "import java.lang.reflect.InvocationTargetException;\n"
          "import java.lang.reflect.Method;\n"
          "import java.lang.reflect.Proxy;\n",
          "java.lang.reflect.Proxy")

    # -- Patch 4b: lottie failure listener + static fallback ----------
    patch("4b/4 Java failure-swap", jp,
          "            setBackgroundColor(mLottieView);\n"
          "            return mLottieView;\n"
          "        } catch (NotFoundException e) {\n"
          '            Log.v("SDL", "couldn\'t find lottie layout or animation, trying static splash");\n'
          "        }\n"
          "\n"
          "        // no lottie asset, try to load the static image then\n"
          '        int presplashId = this.resourceManager.getIdentifier("presplash", "drawable");',
          "            setBackgroundColor(mLottieView);\n"
          "            attachLottieFailureListener(mLottieView);\n"
          "            return mLottieView;\n"
          "        } catch (NotFoundException e) {\n"
          '            Log.v("SDL", "couldn\'t find lottie layout or animation, trying static splash");\n'
          "        }\n"
          "\n"
          "        // no lottie asset, try to load the static image then\n"
          "        return getStaticSplash();\n"
          "    }\n"
          "\n"
          "    protected void attachLottieFailureListener(View lottieView) {\n"
          "        /* If the animation fails to load (bad JSON, missing raw\n"
          "         * resource), swap to the static presplash so the user never\n"
          "         * stares at a black screen. Reflection keeps this compiling\n"
          "         * whether or not the lottie classes are on the classpath. */\n"
          "        try {\n"
          '            int id = this.resourceManager.getIdentifier("progressBar", "id");\n'
          "            final Object animView = lottieView.findViewById(id);\n"
          "            if (animView == null) {\n"
          "                return;\n"
          "            }\n"
          "            final Class<?> listenerIface =\n"
          '                    Class.forName("com.airbnb.lottie.LottieListener");\n'
          "            Object proxy = Proxy.newProxyInstance(\n"
          "                    listenerIface.getClassLoader(),\n"
          "                    new Class<?>[] { listenerIface },\n"
          "                    new InvocationHandler() {\n"
          "                        @Override\n"
          "                        public Object invoke(Object p, Method m, Object[] a) {\n"
          '                            if (m.getName().equals("onResult")) {\n'
          "                                swapToStaticSplash();\n"
          "                            }\n"
          "                            return null;\n"
          "                        }\n"
          "                    });\n"
          "            animView.getClass()\n"
          '                    .getMethod("addFailureListener", listenerIface)\n'
          "                    .invoke(animView, proxy);\n"
          "        } catch (Exception e) {\n"
          '            Log.v("SDL", "no lottie failure listener: " + e);\n'
          "        }\n"
          "    }\n"
          "\n"
          "    protected void swapToStaticSplash() {\n"
          "        runOnUiThread(\n"
          "                new Runnable() {\n"
          "                    public void run() {\n"
          "                        try {\n"
          "                            if (mLottieView != null\n"
          "                                    && mLottieView.getParent() != null) {\n"
          "                                ((ViewGroup) mLottieView.getParent())\n"
          "                                        .removeView(mLottieView);\n"
          "                            }\n"
          "                            mLottieView = null;\n"
          "                            mImageView = null;\n"
          "                            showLoadingScreen(getStaticSplash());\n"
          "                        } catch (Exception e) {\n"
          '                            Log.v("SDL", "static splash swap failed: " + e);\n'
          "                        }\n"
          "                    }\n"
          "                });\n"
          "    }\n"
          "\n"
          "    protected View getStaticSplash() {\n"
          '        int presplashId = this.resourceManager.getIdentifier("presplash", "drawable");',
          "attachLottieFailureListener")

    if FAILURES:
        print(f"\n{len(FAILURES)} PATCH GROUP(S) FAILED: {FAILURES}")
        return 1
    print("\nALL PATCHES APPLIED (or already present).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

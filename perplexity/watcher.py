"""
Live-reload loader for Blender.

Run once with:
    blender --python watcher.py

It watches scene.py (same directory) and re-executes it automatically
every time you save it, so edits show up in the viewport without
restarting Blender.
"""

import bpy
import os
import traceback

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCENE_PATH = os.path.join(SCRIPT_DIR, "scene.py")

_last_mtime = 0.0


def _run_scene_script():
    global _last_mtime
    try:
        mtime = os.path.getmtime(SCENE_PATH)
    except OSError:
        return 0.5  # keep polling even if file briefly missing

    if mtime != _last_mtime:
        _last_mtime = mtime
        print(f"\n[watcher] reloading {SCENE_PATH}", flush=True)
        try:
            with open(SCENE_PATH, "r") as f:
                code = f.read()
            exec(compile(code, SCENE_PATH, "exec"), {"__name__": "__main__"})
            print("[watcher] reload OK", flush=True)
        except Exception:
            print("[watcher] reload FAILED:", flush=True)
            traceback.print_exc()
            import sys
            sys.stdout.flush()

    return 0.5  # poll every 0.5s


bpy.app.timers.register(_run_scene_script, first_interval=0.1)

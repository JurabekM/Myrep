# Resources

Optional assets picked up at build time:

* `buildcontrol.ico` — application / installer icon (used by `build_exe.ps1` when present).

Icons in the interface come from `qtawesome`; when it is not installed the
application falls back to vector glyphs painted in `app/ui/widgets/icons.py`,
so no image files are required to run.

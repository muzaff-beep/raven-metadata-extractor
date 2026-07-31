Place your header banner image here as: header.png

Recommended: any width, height exactly 64px (auto-scaled to fit either way,
aspect ratio preserved). PNG with transparency works well against the app's
dark theme.

If this file isn't present, the app shows a plain text banner instead --
nothing breaks either way.

---

App / launcher icons -- place these here too:

  app_icon.ico   Windows window/taskbar icon. Multi-resolution .ico
                 (recommended sizes included inside one file: 16x16, 32x32,
                 48x48, 256x256). Used automatically by raven_gui.py at
                 launch, and should also be passed to PyInstaller via
                 --icon=assets/app_icon.ico when building the Windows EXE
                 (see .github/workflows/build.yml).

  app_icon.png   Cross-platform fallback window/taskbar icon (Linux window
                 manager, and used automatically on any OS if the .ico isn't
                 found/applicable). Recommended: 256x256 or 512x512, PNG with
                 transparency.

  app_icon.icns  macOS Dock icon. Only used by PyInstaller at BUILD time (via
                 --icon=assets/app_icon.icns), not loaded at runtime by
                 raven_gui.py -- Tkinter/Tk has no .icns loader, macOS app
                 icons are set at the .app bundle level instead.

If none of these are present, the app runs fine and just shows Tk's default
feather icon in the title bar -- nothing breaks either way.

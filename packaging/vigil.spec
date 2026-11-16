# Builds Vigil so it needs no Python on the target computer. Build on the system you are targeting: make package
#   macOS:   dist/Vigil.app (and dist/vigil, the same app as a folder)
#   Windows: dist/Vigil.exe, one file
#   Linux:   dist/vigil, a folder with the vigil program inside
import sys
from importlib.util import find_spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parent

native = root / "backend" / "app" / "engine" / "_vigil_fast.so"

# Voice is optional. It is bundled only if `make voice` has been run.
voice_datas, voice_binaries, voice_imports = [], [], []
model = root / "data" / "voice-model"
if model.exists() and find_spec("vosk"):
    voice_datas, voice_binaries, voice_imports = collect_all("vosk")
    voice_datas.append((str(model), "data/voice-model"))
    voice_imports.append("sounddevice")

analysis = Analysis(
    [str(root / "frontend" / "main.py")],
    pathex=[str(root / "backend"), str(root / "frontend")],
    binaries=[*([(str(native), "app/engine")] if native.exists() else []), *voice_binaries],
    hiddenimports=voice_imports,
    datas=[
        (str(root / "frontend" / "qml"), "frontend/qml"),
        (str(root / "frontend" / "fonts"), "frontend/fonts"),
        (str(root / "frontend" / "palette.json"), "frontend"),
        (str(root / "config" / "thresholds.defaults.yaml"), "config"),
        (str(root / "data" / "real_ranges.json"), "data"),
        (str(root / "data" / "sources.json"), "data"),
        (str(root / "data" / "space_weather" / "noaa_solar_proton_events.json"), "data/space_weather"),
        (str(root / "data" / "synthetic" / "results.json"), "data/synthetic"),
        (str(root / "SOURCES.md"), "."),
        (str(root / "backend" / "app" / "engine" / "protocols.json"), "app/engine"),
        *voice_datas,
    ],
)
pyz = PYZ(analysis.pure)
icons = root / "packaging"

if sys.platform == "win32":
    # One file that people can double-click. No console window behind the app.
    EXE(pyz, analysis.scripts, analysis.binaries, analysis.datas, [], name="Vigil", console=False,
        icon=str(icons / "vigil.ico"), upx=False)
else:
    exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name="vigil", console=sys.platform != "darwin")
    coll = COLLECT(exe, analysis.binaries, analysis.datas, name="vigil")
    if sys.platform == "darwin":
        BUNDLE(
            coll, name="Vigil.app", icon=str(icons / "vigil.icns"), bundle_identifier="org.thetrojans.vigil",
            info_plist={
                "CFBundleDisplayName": "Vigil", "CFBundleShortVersionString": "1.0.0", "CFBundleVersion": "1.0.0",
                "NSHighResolutionCapable": True, "LSMinimumSystemVersion": "12.0",
                "NSMicrophoneUsageDescription": "Vigil can turn your speech into journal text, on this computer only.",
            },
        )

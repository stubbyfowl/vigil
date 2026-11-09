# Builds a standalone folder at dist/vigil. It needs no Python on the target computer.
# Build on the operating system and CPU you are targeting: make package
from pathlib import Path

root = Path(SPECPATH).parent

native = root / "backend" / "app" / "engine" / "_vigil_fast.so"

analysis = Analysis(
    [str(root / "frontend" / "main.py")],
    pathex=[str(root / "backend"), str(root / "frontend")],
    binaries=[(str(native), "app/engine")] if native.exists() else [],
    datas=[
        (str(root / "frontend" / "qml"), "frontend/qml"),
        (str(root / "frontend" / "fonts"), "frontend/fonts"),
        (str(root / "frontend" / "palette.json"), "frontend"),
        (str(root / "config" / "thresholds.defaults.yaml"), "config"),
        (str(root / "data" / "real_ranges.json"), "data"),
        (str(root / "data" / "synthetic" / "results.json"), "data/synthetic"),
        (str(root / "SOURCES.md"), "."),
        (str(root / "backend" / "app" / "engine" / "protocols.json"), "app/engine"),
    ],
)
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name="vigil", console=True)
COLLECT(exe, analysis.binaries, analysis.datas, name="vigil")

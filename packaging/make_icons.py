"""Draw the app icon and save it for every platform: vigil.icns (macOS), vigil.ico (Windows), vigil.png (Linux).

The icon is Vigil's mark, an eye drawn as an orbit, in white on a dark rounded square.
Run on macOS from the repo root, since .icns needs Apple's iconutil:  .venv/bin/python packaging/make_icons.py
"""

import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

HERE = Path(__file__).resolve().parent
ICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1B1F25"/><stop offset="1" stop-color="#07080A"/></linearGradient></defs>
  <rect x="64" y="64" width="896" height="896" rx="200" fill="url(#g)"/>
  <rect x="64.5" y="64.5" width="895" height="895" rx="200" fill="none" stroke="#33373D" stroke-width="3"/>
  <g fill="none" stroke="#FFFFFF" stroke-linecap="round" stroke-linejoin="round" transform="translate(512 512) scale(14) translate(-24 -24)">
    <ellipse cx="24" cy="24" rx="20" ry="11" stroke-width="2.6"/>
    <circle cx="24" cy="24" r="5.5" stroke-width="2.6"/>
    <path d="M44 24 a20 11 0 0 0 -10 -9.5" stroke="#8AB4FF" stroke-width="3.6"/>
  </g>
</svg>"""


def render(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(ICON.encode())).render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def png_bytes(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def write_ico(path: Path, sizes: list[int]) -> None:
    """A Windows icon holding one PNG per size, the format Windows Vista and later read."""
    blobs = [png_bytes(render(s)) for s in sizes]
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = b""
    for s, blob in zip(sizes, blobs, strict=True):
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    path.write_bytes(header + entries + b"".join(blobs))


def main() -> int:
    app = QGuiApplication(sys.argv)  # noqa: F841 (Qt needs an application for painting)
    (HERE / "icon.svg").write_text(ICON + "\n")
    render(512).save(str(HERE / "vigil.png"))
    write_ico(HERE / "vigil.ico", [16, 24, 32, 48, 64, 128, 256])
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "vigil.iconset"
        iconset.mkdir()
        for s in (16, 32, 128, 256, 512):
            render(s).save(str(iconset / f"icon_{s}x{s}.png"))
            render(s * 2).save(str(iconset / f"icon_{s}x{s}@2x.png"))
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(HERE / "vigil.icns")], check=True)
    print("Wrote vigil.icns, vigil.ico, vigil.png and icon.svg in", HERE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

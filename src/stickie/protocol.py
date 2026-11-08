"""PM290C's streaming TSPL variant, traced from the official Labelnize APK.

PRINT precedes BITMAP; ALLEND ends the stream. This is not ordinary TSPL.
Raster pixels are packed MSB first, with 1 = white and 0 = black.
"""
from PIL import Image

WIDTH = 384
DOTS_PER_MM = 8
MAX_HEIGHT = 8000
STATUS_QUERY = b"\x1b!?\r\n"
STATUS_NAMES = {
    0: "ready", 1: "lid open", 2: "feeding", 3: "paper error",
    4: "out of paper", 8: "paper jam", 16: "paused", 32: "busy",
    36: "ran out of paper", 48: "low battery", 128: "overheated",
    144: "insufficient power",
}


def status_name(value: int) -> str:
    return STATUS_NAMES.get(value, f"unknown status 0x{value:02x}")


def build_job(image: Image.Image, density: int = 8) -> bytes:
    if image.mode != "1" or image.width != WIDTH:
        raise ValueError("Print image must be monochrome and 384 pixels wide")
    if not 80 <= image.height <= MAX_HEIGHT:
        raise ValueError("Print length must be between 10 and 1000 mm")
    if not 0 <= density <= 15:
        raise ValueError("Density must be between 0 and 15")
    # Mirrors LabelCommand + PrintfTSPLManager's PM230/FakeESC path.
    header = (
        f"SIZE 48 mm,{image.height / DOTS_PER_MM:g} mm\r\n"
        f"DIRECTION 0,0\r\nDENSITY {density}\r\nCLS\r\nPRINT 1\r\n"
        f"BITMAP 0,0,48,{image.height},1,"
    ).encode("ascii")
    return header + image.tobytes() + b"ALLEND\r\n"

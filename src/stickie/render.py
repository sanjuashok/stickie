"""Render all content locally, onto the printer's 48 mm printable width."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from .protocol import WIDTH, MAX_HEIGHT


def font_at(size: int, path: str | None = None):
    if not 8 <= size <= 160:
        raise ValueError("Font size must be between 8 and 160 pixels")
    if path:
        return ImageFont.truetype(path, size)
    for candidate in ["/System/Library/Fonts/Supplemental/Arial.ttf",
                      "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


def mono(image: Image.Image, dither: bool = True, threshold: int = 160):
    if not 0 <= threshold <= 255:
        raise ValueError("Threshold must be between 0 and 255")
    gray = image.convert("L")
    if dither:
        return gray.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    return gray.point(lambda p: 255 if p > threshold else 0, mode="1")


def render_text(text: str, size: int = 32, font: str | None = None,
                margin: int = 16, align: str = "left") -> Image.Image:
    if not text.strip():
        raise ValueError("Text is empty")
    if len(text) > 20000:
        raise ValueError("Text is too long for one sticker")
    if not 0 <= margin <= 96:
        raise ValueError("Margin must be between 0 and 96 pixels")
    face = font_at(size, font)
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    available = WIDTH - margin * 2
    lines = []
    for paragraph in text.expandtabs(4).split("\n"):
        line = ""
        for char in paragraph:
            if draw.textlength(line + char, font=face) > available:
                split = line.rfind(" ")
                if split > 0:
                    lines.append(line[:split])
                    line = line[split + 1:] + char
                else:
                    lines.append(line)
                    line = char
            else:
                line += char
        lines.append(line)
    ascent, descent = face.getmetrics()
    line_height = ascent + descent + max(4, size // 5)
    height = max(80, margin * 2 + line_height * len(lines))
    if height > MAX_HEIGHT:
        raise ValueError("Text exceeds the maximum sticker length of 1000 mm")
    canvas = Image.new("L", (WIDTH, height), 255)
    draw = ImageDraw.Draw(canvas)
    for index, line in enumerate(lines):
        length = draw.textlength(line, font=face)
        x = {"left": margin, "center": (WIDTH - length) / 2,
             "right": WIDTH - margin - length}[align]
        draw.text((x, margin + index * line_height), line, font=face, fill=0)
    return mono(canvas, dither=False)


def render_image(path: str, margin: int = 8, dither: bool = True,
                 threshold: int = 160, rotate: int = 0) -> Image.Image:
    if not 0 <= margin <= 96:
        raise ValueError("Margin must be between 0 and 96 pixels")
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
    if rotate:
        image = image.rotate(rotate, expand=True)
    width = WIDTH - margin * 2
    height = max(1, round(image.height * width / image.width))
    if height + margin * 2 > MAX_HEIGHT:
        raise ValueError("Image exceeds the maximum sticker length of 1000 mm")
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (WIDTH, max(80, height + margin * 2)), "white")
    canvas.alpha_composite(image, (margin, margin))
    return mono(canvas, dither, threshold)

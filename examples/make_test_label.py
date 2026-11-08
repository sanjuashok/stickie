"""Generate a local diagnostic image without accessing a printer."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def test_label():
    image = Image.new("1", (384, 192), 1)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 375, 183), radius=12, outline=0, width=3)
    font = ImageFont.load_default(size=26)
    draw.text((192, 30), "TEST PRINT", font=font, fill=0, anchor="mt")
    for row in range(3):
        for column in range(12):
            if (row + column) % 2 == 0:
                x, y = 48 + column * 24, 88 + row * 24
                draw.rectangle((x, y, x + 23, y + 23), fill=0)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output/test-label.png"))
    args = parser.parse_args()
    target = args.output.expanduser()
    if target.exists():
        parser.error(f"Output already exists: {target}. Choose another --output path.")
    target.parent.mkdir(parents=True, exist_ok=True)
    test_label().save(target, format="PNG")
    print(f"Saved {target} (384 × 192 pixels, 48 × 24 mm)")


if __name__ == "__main__":
    main()

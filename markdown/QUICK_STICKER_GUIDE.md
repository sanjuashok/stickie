# PM290C artwork and printing guide

Use this workflow for text labels, drawings, icons, photos, and picture stickers.
The CLI renders files locally and prints through Bluetooth Classic on macOS.

## Prepare the printer

Run `./setup.sh` once from the repository checkout. Pair the PM290C in macOS
System Settings → Bluetooth, turn it on, and load thermal paper correctly.
Disconnect any phone app using the printer.

```sh
./stickie scan
./stickie status
```

With multiple paired printers, add `--device AA:BB:CC:DD:EE:FF` to each command,
using the actual Classic address from `scan`.

## Size reference

| Property | Value |
| --- | --- |
| Printable width | 384 dots / 48 mm |
| Paper width used in validation | 54 mm |
| Rendering scale | 8 dots per mm, approximately 203 dpi |
| Square label | 384 × 384 dots / 48 × 48 mm with `--margin 0` |
| Supported job height | 80–8000 rows / 10–1000 mm |
| Image margin | 0–96 pixels; default 8 |
| Text margin | 0–96 pixels; default 16 |
| Text font size | 8–160 pixels; default 32 |
| Density | 0–15; default 8 |
| Image threshold | 0–255; default 160 when using `--no-dither` |

Images scale to the printable width minus the left and right margins, keeping
their aspect ratio. The output is padded to a minimum of 80 rows. A square
source becomes exactly 384 × 384 only with zero CLI margin; add any desired
border and inner padding to the artwork itself. The stated height is the
raster/job length, not a guarantee of the total paper feed distance.

## Preview first, then print once

For line art:

```sh
mkdir -p output
./stickie image drawing.png --margin 0 --no-dither --preview output/drawing-print.png
./stickie image output/drawing-print.png --margin 0 --no-dither
```

Run the second command after inspecting the preview. Zero margin preserves its
geometry when printing an already prepared preview. `--preview` never connects
to the printer, and its parent directory must exist.

For photos, omit `--no-dither` during preview generation so gray tones become
black-and-white dots. Print that prepared preview with the same zero-margin
command above. Avoid repeatedly resizing or processing the same artwork.

`--rotate 90`, `180`, or `270` rotates an image before sizing it. Supported input
formats include PNG, JPEG, and other Pillow-readable raster files. Convert PDF
pages to PNG outside the CLI.

## Artwork recommendations

These are recommendations for small illustrations, not restrictions on what
the CLI accepts:

- Use black marks on a white background for crisp line art. Transparency is
  composited onto white.
- Use bold outlines and simple shapes; check details at the actual 384-pixel
  output width. Photos and gray shading can use the default dithering.
- Keep text, marks, and artwork inside the canvas with enough white padding
  to survive reduction. Avoid hairlines, tiny lettering, and large dense fills.
- Add a border only if wanted. For a rounded square design, inset it about
  5% from the canvas edge and leave space between subject, caption, and border.
- For generated illustrations, a square source around 1024 × 1024 pixels is
  convenient. A native 384-pixel-wide source also works.
- Check every character, punctuation mark, and glyph after conversion.

## Text labels

```sh
./stickie text "STORAGE" --font-size 48 --align center --preview output/storage.png
./stickie image output/storage.png --margin 0 --no-dither
```

Use `--font /path/to/font.ttf` for a specific TTF/OTF font. Character coverage
depends on that font. Complex scripts may also need shaping and layout support;
when exact typography matters, render it in a suitable design tool and print
the resulting image. The CLI does not translate text or guarantee a generated
caption's spelling.

## Optional illustration prompt

Adapt this template to the requested subject, language, shape, and caption.
Remove the caption or border instructions if they are not wanted.

```text
Create a square illustration for a monochrome thermal-printer label.
Subject: [SUBJECT], fully visible, with simple recognizable shapes.
Style: bold, clean black outlines on a pure white background, minimal detail.
Composition: center the subject above the exact caption “[CAPTION]”. Set the
caption in large, legible type in the requested language, preserving every
character and mark. Keep clear white space between the subject and caption.
Border: one rounded square outline inset about 5% from the canvas edges.
Keep the full subject, caption, and border inside the canvas without clipping.
The final print is 384 × 384 pixels / 48 × 48 mm; avoid hairlines, tiny details,
gray shading, gradients, shadows, extra text, watermarks, and mockups.
```

Illustration generation is separate from printing. Use the image tool chosen
for the task, save its output locally, and inspect the converted preview.

## Completion and troubleshooting

Wait for `Printer confirmed completion.` before sending another job. If an
operation fails or times out, inspect the paper before retrying; some or all of
the job may already have printed. No automatic retries are performed.

If output is blank or damaged, check the preview and paper orientation. When
appropriate, `./stickie self-test` prints a built-in diagnostic to distinguish
paper/head problems from rendering or transport issues. `./stickie cancel`
requests cancellation and reports readiness.

Use the default Classic transport. BLE image printing is experimental and
produced damaged images in testing; USB printing is not implemented. PM290C
firmware 0.0.6 is the validated configuration. Do not assume an unrelated
printer works because it has the same paper width.

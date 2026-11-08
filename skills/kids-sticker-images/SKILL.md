---
name: kids-sticker-images
description: Generate square black-and-white cartoon stickers from a child's idea, prepare a PM290C-sized preview, and print with Stickie when requested. Use for illustrated kids' stickers with optional captions; use the generic printing workflow for existing files or plain text labels.
---

# Kids' sticker images

Turn the requested idea into a simple, cheerful illustration that reads clearly
on a 48 mm square thermal sticker. Keep the subject and any exact wording the
user supplies. A brief request such as "a dinosaur sticker" is enough to begin;
choose a friendly, recognizable cartoon rather than asking about every detail.

## Design for the small print

- Generate a square PNG, ideally around 1024 × 1024 pixels. The final artwork
  will be reduced to **384 × 384 pixels / 48 × 48 mm**.
- Use pure black lines on a solid white background. Avoid gray shading,
  gradients, shadows, color, textures, and large solid-black areas.
- Use bold, clean outlines that remain roughly 2–4 pixels thick at print size.
  Simplify tiny features instead of relying on fine detail.
- Default to one large cartoon subject within a single rounded square outline,
  inset about 5% from every edge. Follow requests for another layout or border.
- Keep the entire subject and border inside the canvas with clear white space.
  Avoid adding scenery, decorations, extra characters, watermarks, or mockups
  unless they are part of the requested idea.
- Include a caption only when requested. Place it beneath the subject and
  inside the border, leaving room for all characters and marks. Preserve the
  exact text and language; do not silently translate or add a label.

Without a caption, let the subject occupy most of the inner square. With a
caption, reserve the bottom portion for large, readable lettering and leave
space between the subject, text, and border. Long captions may need a simpler
layout or fewer words; do not shrink them into unreadable type.

## Generate the artwork

Use an available image-generation tool for the illustration. Prefer a built-in
tool when available, and follow any applicable image-generation instructions.
The printer CLI itself does not generate illustrations or require an image API
key. If no generator is available, explain that limitation; do not claim that
an image was generated.

Adapt this prompt to the user's idea; omit the caption paragraph when none was
requested:

```text
Create one square cartoon sticker of [SUBJECT] for a small thermal printer.
Use a friendly, recognizable cartoon with bold, clean pure-black outlines on a
pure-white background. Keep details simple and the entire subject visible.
Surround it with one rounded square outline inset about 5% from every edge.
Leave ample white padding and keep the complete border inside the image.

Below the subject, inside the border, center this exact caption: "[CAPTION]".
Use large, correctly shaped lettering in the requested language, preserving
every character and mark. Leave clear space around the caption.

The image will print at 384 × 384 pixels / 48 × 48 mm. Use strong outlines and
minimal detail that survive reduction. No gray shading, gradients, shadows,
textures, scenery, extra text, logos, watermarks, or photographed mockups.
```

Inspect the generated image for the requested subject, complete border, and
correct caption. Correct artwork or spelling errors with the image tool before
printing. Keep the original output and copy the selected image into the
checkout's ignored `output/` directory using a descriptive, unused filename.

## Prepare the actual print preview

Find the Stickie checkout containing `./stickie` and `setup.sh`. Run these
commands from its root, replacing the example filenames with the saved artwork:

```sh
mkdir -p output
./stickie image output/rocket.png --margin 0 --no-dither --preview output/rocket-print.png
```

If the environment is not installed, follow the checkout's setup instructions.
`--preview` saves a PNG without connecting to the printer. Zero CLI margin keeps
the square shape; the source artwork already supplies its own inner padding.
`--no-dither` gives crisp black-and-white line art. Transparency is flattened
onto white by the CLI.

Inspect the **384 × 384 preview**, not just the large source. Confirm that the
subject is recognizable, the border is complete, the background is white, and
every requested character is legible. Save the source and preview paths for
the user. A request to generate a sticker alone ends with the checked image.

## Print when requested

When the user asks to print, use the verified default **Bluetooth Classic**
transport and send the checked preview once:

```sh
./stickie image output/rocket-print.png --margin 0 --no-dither
```

PM290C must be paired in macOS Bluetooth settings, powered on, and released
from other printer apps. If more than one printer is paired, use `./stickie scan`
and select the intended Classic MAC address with `--device`. BLE image printing
is unreliable, and USB printing is not implemented. Other printer models need
separate compatibility verification.

Honor the requested copy count; do not send extra test copies. Wait for
completion before another job. If a transfer fails or times out, inspect the
paper before retrying because it may already have printed. Report the printer's
completion reply accurately without claiming independent physical inspection.

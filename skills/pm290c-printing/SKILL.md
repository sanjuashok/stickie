---
name: pm290c-printing
description: Prepare, preview, and print generic text or image labels with the Stickie CLI for PM290C thermal printers on macOS. Use for local printer jobs and image sizing; other printer models require separate compatibility verification.
---

# PM290C printing with Stickie

Work from the Stickie checkout containing `./stickie`, `setup.sh`, and
`pyproject.toml`. If its `.venv` is missing, follow the repository's setup
instructions. Do not assume a particular user's path, paired device, installed
image generator, language, subject, or label shape.

## Select the printer

Use `./stickie scan` and `./stickie status` when connection details are needed.
Pair PM290C in macOS Bluetooth settings before using the default Classic
transport. Disconnect other apps that hold the printer connection. One paired
PM290C is selected automatically; with multiple devices, use `--device` with the
intended Classic MAC address from scan. macOS BLE UUIDs are not Classic addresses.

Bluetooth Classic RFCOMM channel 1 is verified on PM290C firmware 0.0.6. BLE
image printing produced damaged output, and USB printing is not implemented.
Do not switch transports or claim support for other models based only on their
appearance, paper width, or a TSPL-like command set.

## Prepare content

- Printable width is 384 pixels / 48 mm; rendering uses 8 dots per mm.
- Job height is 80–8000 pixels / 10–1000 mm. Rectangular images retain aspect
  ratio; square source artwork with `--margin 0` becomes 384 × 384 pixels.
- Use high-contrast line art with readable lettering and sufficient white
  padding. Borders, captions, and square layouts are optional design choices.
- `--no-dither` preserves sharp line art by thresholding; default dithering is
  useful for photos. Transparency is flattened onto white. PDF needs conversion
  to an image first.
- Preserve the requested wording and language. Check font coverage and complex
  text shaping; render exact typography into an image when necessary.
- For generated artwork, use the image tool appropriate to the task and inspect
  its result. Image generation is separate from this local printing CLI.

## Preview, then print

Create the output directory and render a preview before sending new artwork:

```sh
mkdir -p output
./stickie image artwork.png --margin 0 --no-dither --preview output/label.png
```

For a text label:

```sh
./stickie text "LABEL" --font-size 48 --align center --preview output/label.png
```

Adjust size, layout, margin, and font to the requested content. Image margin
defaults to 8 pixels, text margin to 16, and density to 8 (range 0–15).

Inspect the actual preview for clipping, unintended dark backgrounds, legibility,
and exact text. `--preview` does not access Bluetooth. When printing is requested,
send the checked preview once, retaining its geometry:

```sh
./stickie image output/label.png --margin 0 --no-dither
```

Apply `--device` to the print command when selecting a specific printer. A
request to create or preview artwork alone is not a request to print it.

## Interpret the result

Send one job at a time. Report `Printer confirmed completion.` as the printer's
response, not as independent visual confirmation. If transmission fails, times
out, or is interrupted, stop and inspect the paper before another attempt;
never silently resend a possibly printed job.

Use `./stickie inspect` for connection details. `./stickie self-test` prints a
built-in diagnostic when a hardware test is needed. `./stickie cancel` requests
cancellation and reports readiness, but cannot undo an already printed label.
Keep device addresses, diagnostic reports, and generated output local unless
sharing those specific artifacts is requested.

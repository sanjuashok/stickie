# Generic test label

Generate a 384 × 192 pixel (48 × 24 mm) test label locally:

```sh
.venv/bin/python examples/make_test_label.py
```

This creates `output/test-label.png` with a border, text, and a checkerboard.
The script does not connect to a printer. A successful physical print should
show readable text, a complete border, and alternating black and white squares.

Preview and print from the repository root:

```sh
./stickie image output/test-label.png --margin 0 --no-dither --preview output/test-label-preview.png
# Inspect the preview before running the print command.
./stickie image output/test-label-preview.png --margin 0 --no-dither
```

Choose a different output path with
`--output output/another-test-label.png`. Add `--device` to the CLI print command
if more than one PM290C is paired.

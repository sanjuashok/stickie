# Stickie

A local command-line tool for printing text and images on a **PM290C thermal
printer from macOS**, over Bluetooth Classic. Printing requires no phone app,
account, or cloud service.

Text and image printing have been physically verified on PM290C firmware
**0.0.6**. Other models and firmware versions are not yet verified. This is an
independent project, unaffiliated with the printer manufacturer or Labelnize.

## Requirements

- macOS with Bluetooth enabled
- Python 3.11 or newer
- Apple Command Line Tools (`xcode-select --install`)
- A PM290C paired in **System Settings → Bluetooth**, with paper loaded

Allow Bluetooth access if macOS prompts for it. Disconnect other apps or phones
from the printer before using Stickie.

## Quick start

From a checkout of this repository:

```sh
./setup.sh
./stickie scan
./stickie status
./stickie text "Hello, world!"
```

Setup installs the project and development dependencies into `.venv`. A small
native Swift helper builds automatically on the first Bluetooth operation and
is cached locally. Rendering previews does not require a printer connection.

For an existing Python environment, `python -m pip install .` installs the
`stickie` command; `python -m pip install '.[dev]'` also installs test tools.
The `./stickie` wrapper uses the checkout's `.venv`.

## Preview and print

```sh
mkdir -p output
./stickie text "PANTRY" --font-size 48 --align center --preview output/pantry.png
./stickie image output/pantry.png --margin 0 --no-dither
```

`--preview` saves a PNG without connecting or printing. Create the destination
directory first. Inspect the preview before printing, especially for small text,
complex lettering, or fine detail.

```sh
# Sharp line art with its own padding
./stickie image drawing.png --margin 0 --no-dither

# Photos use monochrome dithering by default
./stickie image photo.jpg

# Other formatting options
./stickie image landscape.jpg --rotate 90
./stickie text "Custom font" --font /path/to/font.ttf
printf 'Shopping list\nMilk\nCoffee\nRice' | ./stickie text -
```

The printable width is **384 dots / 48 mm** on 54 mm paper. A square image with
`--margin 0` prints at **384 × 384 dots / 48 × 48 mm**. Rectangular images retain
their aspect ratio; the job length is automatic. Transparency becomes white.
PNG, JPEG, and other Pillow-supported image formats are accepted. Export PDFs
to an image first.

See the [artwork and printing guide](markdown/QUICK_STICKER_GUIDE.md) for sizes,
image recommendations, text handling, and a reusable illustration prompt. A
[generic test label](examples/README.md) can be generated entirely locally.

## Select and manage a printer

```sh
./stickie scan
./stickie text "Hello" --device AA:BB:CC:DD:EE:FF
./stickie inspect
./stickie self-test
./stickie cancel
```

Replace the example address with a paired printer's Classic address from
`scan`. With exactly one paired PM290C, selection is automatic. With multiple
printers, use `--device` on each operation. Bluetooth Low Energy identifiers
shown by macOS are different from Classic MAC addresses.

`self-test` prints the printer's built-in diagnostic. `cancel` requests
cancellation and reads readiness; it cannot undo a completed print. Send one
job at a time. If printing times out or is interrupted, check the paper before
retrying: Stickie never automatically resends a job.

## Compatibility

| Interface | Status |
| --- | --- |
| macOS Bluetooth Classic, RFCOMM channel 1 | Verified text and image printing on PM290C firmware 0.0.6; default transport |
| Bluetooth Low Energy | Experimental diagnostics; image tests produced damaged output |
| USB-C | Serial-interface discovery only; printing is not implemented |
| Wi-Fi, Linux, Windows, other printer models | No verified print transport |

The encoder implements a PM290C-specific streaming protocol. Similar paper
widths, Bluetooth names, or TSPL-like commands do not establish compatibility.
See [protocol notes](docs/protocol.md) and [hardware validation](docs/hardware-log.md).

Exit codes: `0` success, `1` operation error, `2` invalid arguments or a non-ready
status, `130` interrupted. A completion reply confirms the printer's response;
it does not independently verify the appearance of the physical output.

## Development and agent use

```sh
./setup.sh
.venv/bin/pytest -q
```

The repository includes a [PM290C printing skill](skills/pm290c-printing/SKILL.md)
for agents working in this checkout. It covers generic text and image jobs,
printer selection, dimensions, previews, and the verified transport without
imposing a particular language or sticker style.

Read that file directly in an agent session, or install the `pm290c-printing`
folder into your agent's skills directory. Point the agent at this checkout
when using it; the skill does not bundle a printer driver or install itself.

For a transport regression, see [Android capture guidance](docs/android-capture.md).
Keep raw device reports, app packages, generated output, credentials, and
personal identifiers out of contributions. The CLI does not contact cloud
services; a separately chosen image-generation tool may do so.

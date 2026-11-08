# PM290C hardware validation

This document records the reproducible conclusions from hardware testing,
rather than individual device identifiers or session transcripts.

## Validated configuration

| Component | Tested configuration |
| --- | --- |
| Printer | PM290C, firmware 0.0.6 |
| Host | Apple silicon Mac, macOS 14.4.1 |
| Print transport | Bluetooth Classic RFCOMM channel 1 |
| Negotiated packet size | 666 bytes on the test device; use the negotiated value |
| Raster | 384 pixels wide, 1 bit per pixel, 8 dots per mm |

Hardware tests were performed in September 2026. No broader firmware, operating
system, or model compatibility is implied.

## Confirmed behavior

- Text printed clearly using the encoder in `src/stickie/protocol.py` over the
  native Classic transport.
- An image containing readable text, a complete outlined rectangle, and an
  alternating checkerboard printed correctly, as confirmed by visual inspection.
- Readiness queries returned ready when loaded and an out-of-paper fault when
  paper was incorrectly installed.
- The built-in self-test produced readable text and patterns.
- Cancellation followed by a readiness query succeeded. One transient native
  serial write error was reported without an automatic retry.

## Transport findings

A successful print from the official app used RFCOMM channel 1. The recording
was filtered and truncated most image data, so it established transport and
packet-size evidence rather than exact payload equivalence. A subsequent
native Mac print verified the existing raster encoder over Classic.

The helper uses synchronous RFCOMM open/writes, negotiated packet sizes,
readiness checks, and a buffered reply parser. Only `63 00` is accepted as print
completion. `63 20` is a next-copy event, not completion.

BLE discovery, status, and identity queries worked. Repeated BLE image tests
produced blank output, lines, partial images, or black blocks. Packet-size,
pacing, inversion, and framing variations did not establish a reliable BLE
print route. A completion reply sometimes accompanied visibly incorrect output.
The CLI therefore defaults to Classic.

USB-C exposed a Jieli CDC serial interface with VID:PID `4c4a:4155`. Identity
probes did not establish printing support. USB printing is not implemented.

## Reporting compatibility

For another printer or firmware, report its model, firmware, macOS version,
transport, sanitized error message, and whether a built-in test and a simple CLI
image print correctly. A printed diagnostic can include a unique device address
or QR code; redact those before sharing. Raw Android reports and proprietary
app files do not belong in this repository.

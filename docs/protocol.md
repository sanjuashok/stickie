# PM290C protocol evidence

## Sources

Inspected on 2026-09-23:

- Manufacturer support page: https://labelnize.com/pages/support
- Official APK linked by that page: https://oss.nelko.net/app_download/labelnize.apk
- Download SHA-256: `b4cd7b6189f7413f7c1448ec365d51b80273b3376e0186e103067013fb94b341`

The APK was inspected locally using JADX 1.5.6. Proprietary app code/assets
are not distributed in this project. Some unrelated methods did not decompile;
the cited print-generation methods were readable. Obfuscated source names
below are JADX output names, useful when inspecting that exact APK.

## Model and command encoding

`assets/release/cloud_config_labelnize.json`, PM290C entry:
maxWidth 48 mm, dpi 203, continuous 54 mm paper, command 1, compression off.
`Devices.isFakeESCCommand()` maps command 1 to the PM230/FakeESC streaming
path. `PrintBaseActivity.handleSendImage()` selects that path.

The CLI follows `com.print.android.base_lib.print.manager.oo0OOO8.m8756()`
with a 48 mm canvas (the app uses its configured label dimensions):

```text
SIZE 48 mm,<height in mm> mm\r\n
DIRECTION 0,0\r\n
DENSITY <0..15>\r\n
CLS\r\n
PRINT 1\r\n
BITMAP 0,0,48,<height in dots>,1,<binary raster>ALLEND\r\n
```

Notable differences from ordinary TSPL: PRINT precedes BITMAP, and ALLEND
terminates the stream. The app's resetBitmap/resetBMW path does not insert a
CRLF between the raster and ALLEND. `LabelCommand.DIRECTION.FORWARD` is 0.
`convertToBMW()` packs MSB first, 1=white, 0=black. Pillow mode `1` has that
same byte representation. Each row is 48 bytes / 384 pixels.

`p387.oO.state()` sends `1b 21 3f 0d 0a`. One-byte status responses are decoded
according to `PrinterInfo.PrinterErrorType`. Known replies include 00 ready,
04 out of paper, 80 overheated. `PrinterInfo.judgeIsContPrint()` recognizes
`63 20` and five-byte packets starting `63 20`; `judgeIsContPrintFinish()`
recognizes `63 00`. Only `63 00` completes a CLI job; `63 20` is a
next-copy event. The app acknowledges five-byte print events and unsolicited
errors with ACK. Current CLI prints one sticker per job over Bluetooth Classic, using the
negotiated RFCOMM MTU and native serial flow control, without automatic retries.

## Verified Bluetooth Classic path

A successful Android app print was captured on 2026-09-23. The HCI recording
identifies RFCOMM channel 1 on the test printer, with 666-byte packets.
The recording is filtered and cannot recover the whole image job; it proves
the transport and packet sizes, not exact byte-for-byte payload equivalence.

A native macOS IOBluetooth probe then opened the same serial channel using
`openRFCOMMChannelSync`, negotiated MTU 666, read the correct CONFIG response,
and printed the CLI's existing 384×86 HELLO MAC raster. The user confirmed a
clear readable print. No raster inversion or extra framing was required.
The production native helper uses synchronous RFCOMM writes and retains
partial response bytes across callbacks. Classic is now the default.

## Earlier BLE/USB observations

- Bluetooth name: PM290C.
- Advertises service AF30, but connected print service is FF00.
- FF02: write without response; FF01: notifications.
- CoreBluetooth reports a 500-byte maximum write-without-response size.
- Additional characteristics/services exist; the CLI does not use them.
- Bluetooth status query initially returned `04` (out of paper), then ready
  after the user adjusted the paper.
- A 384 × 80 pixel / 10 mm text job ("Hello from your Mac!") was transmitted
  over Bluetooth and the printer returned a completion notification. The user
  reported that a little paper advanced, but it was blank. A completion reply
  alone therefore does not establish successful visible printing.
- A second 384 × 400 pixel / 50 mm diagnostic used `SIZE 54 mm,50 mm`,
  density 10, text, and stripes. The initial status was `00`; notifications
  included `f0 00 46 50` twice, then `04` (out of paper). The meaning of the
  four-byte notification is not yet established.
- USB VID:PID 4c4a:4155, Jieli Technology, CDC serial port.
- USB probes at 115200 baud did not establish print support. Some commands
  returned ASCII `ERROR0`; no functional USB print path is claimed.

## Validation status

Clear CLI-generated text and an image containing an outline and checkerboard
are physically verified over Bluetooth Classic on the
connected PM290C firmware 0.0.6. BLE custom printing is not verified and has
repeatedly produced damaged images. USB printing is not implemented. No broader
model or firmware compatibility is claimed. See [hardware log](hardware-log.md)
for individual experiments and subsequent CLI image validation.

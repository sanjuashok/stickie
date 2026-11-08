# Capture a reference print for transport debugging

Use this workflow when investigating a reproducible transport regression or a
new firmware variant. Normal PM290C printing uses the verified Classic CLI
path and does not require Android or packet capture.

## Record one known-good print

1. Install the manufacturer's printing app from its official source. PM290C
   testing used Labelnize, linked from https://labelnize.com/pages/support .
2. On an Android test device, enable Developer options, USB debugging, and
   **Bluetooth HCI snoop log**. Select full logging if available, then restart
   Bluetooth so the change takes effect.
3. Connect the phone to the development Mac with a USB data cable and authorize
   debugging. Use `adb devices -l` to confirm the intended test device.
4. Connect to the printer in the app. Print a simple label such as `TEST PRINT`
   with an outlined rectangle and confirm the output is visually correct.
5. Keep the phone connected while collecting a bug report. Wait for report
   generation to finish before copying or extracting it.

Use Android Platform Tools (`adb`) and Wireshark/TShark installed in your own
environment. Select the device serial explicitly when multiple phones are
connected:

```sh
mkdir -p captures
adb devices -l
adb -s DEVICE_SERIAL bugreport captures/reference-print.zip
```

Replace `DEVICE_SERIAL` with the intended device. The report contains broader
phone diagnostics, not just printer traffic. Keep it local, extract only the
relevant connection for analysis, and do not commit or upload the raw report.
The `captures/` directory is ignored by Git.

## Verify and compare

Look for `btsnoop_hci.log` and rotated logs under the report's
`FS/data/misc/bluetooth/logs/` entries. If only an embedded in-memory recording
is present, Android's `btsnooz.py` may extract it from the report text.

Check capture timestamps against the actual print. Confirm that the file
contains full outgoing data; a setting labelled full does not guarantee an
unfiltered report on every Android build. Do not interpret a truncated payload
as the complete print job or an empty Bluetooth recording as a working print
protocol.

Identify the printer's connection using the test device's own address. Compare
transport (Classic RFCOMM or BLE), initialization, framing, packet sizes, timing,
flow control, and replies with the [protocol notes](protocol.md). For PM290C,
the verified route is Classic RFCOMM channel 1. A completion reply alone does
not establish correct physical output.

Afterward, disable diagnostic logging and revoke temporary debugging access
when it is no longer needed.

## References

- https://source.android.com/docs/core/connect/bluetooth/verifying_debugging
- https://developer.android.com/tools/adb
- https://developer.android.com/studio/debug/bug-report

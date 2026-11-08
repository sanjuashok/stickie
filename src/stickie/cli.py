import argparse
import asyncio
import json
import sys
from pathlib import Path
from bleak.exc import BleakError
from .protocol import build_job, status_name
from .render import render_image, render_text
from .transport import BluetoothPrinter, PrinterError, scan, usb_devices
from .classic import ClassicPrinter, paired_printers


def parser():
    p = argparse.ArgumentParser(prog="stickie", description="Print stickers on a PM290C. No phone or account needed.")
    sub = p.add_subparsers(dest="command", required=True)
    scan_p = sub.add_parser("scan", help="Find nearby PM290 printers and connected USB ports")
    scan_p.add_argument("--timeout", type=float, default=8)
    sub.add_parser("usb", help="List detected PM290C USB serial interfaces (diagnostics only)")
    status = sub.add_parser("status", help="Read printer readiness over Bluetooth")
    inspect = sub.add_parser("inspect", help="Show Bluetooth services for troubleshooting")
    self_test = sub.add_parser("self-test", help="Print the printer's built-in hardware test")
    cancel = sub.add_parser("cancel", help="Request cancellation of a pending job and read status")
    for command in (status, inspect, self_test, cancel):
        connection_options(command)
    for name, help_text in [("text", "Print a text sticker"), ("image", "Print a PNG, JPEG, or other image")]:
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("content", help="Text (use - for stdin)" if name == "text" else "Image path")
        connection_options(cmd)
        cmd.add_argument("--preview", metavar="PNG", help="Save a preview only; do not connect or print")
        cmd.add_argument("--density", type=int, default=8, choices=range(16), metavar="0-15")
        cmd.add_argument("--margin", type=int, default=16 if name == "text" else 8, help="Margin in pixels")
        if name == "text":
            cmd.add_argument("--font-size", type=int, default=32, help="Font size in pixels (8 pixels = 1 mm)")
            cmd.add_argument("--font", help="Path to a TTF/OTF font")
            cmd.add_argument("--align", choices=["left", "center", "right"], default="left")
        else:
            cmd.add_argument("--no-dither", action="store_true", help="Use a threshold for sharp line art")
            cmd.add_argument("--threshold", type=int, default=160)
            cmd.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], default=0)
    return p


def connection_options(cmd):
    cmd.add_argument("--device", help="Paired printer MAC address from scan (BLE UUID for --transport ble)")
    cmd.add_argument("--transport", choices=["classic", "ble"], default="classic",
                     help="Classic is verified; BLE printing is experimental and produces damaged output")
    cmd.add_argument("--timeout", type=float, default=30, help="Connection timeout in seconds")


async def run(args):
    if hasattr(args, "timeout") and not 0 < args.timeout <= 120:
        raise ValueError("Timeout must be greater than 0 and at most 120 seconds")
    if args.command == "usb":
        print(json.dumps(usb_devices(), indent=2))
        print("USB serial is detected separately; USB printing is not yet verified.")
        return
    if args.command == "scan":
        classic, ble = await asyncio.gather(paired_printers(), scan(args.timeout))
        print(json.dumps({"classic": classic, "ble": ble, "usb": usb_devices()}, indent=2))
        return
    image = None
    if args.command == "text":
        text = sys.stdin.read() if args.content == "-" else args.content
        image = render_text(text, args.font_size, args.font, args.margin, args.align)
    elif args.command == "image":
        image = render_image(args.content, args.margin, not args.no_dither, args.threshold, args.rotate)
    if image is not None:
        job = build_job(image, args.density)
        if args.preview:
            target = Path(args.preview).expanduser().resolve()
            image.save(target, format="PNG")
            print(f"Preview saved: {target} ({image.width} × {image.height} pixels, {image.height / 8:g} mm long)")
            return
    printer_type = ClassicPrinter if args.transport == "classic" else BluetoothPrinter
    async with printer_type(args.device, args.timeout) as printer:
        if args.command == "status":
            state = await printer.status()
            print(f"PM290C: {status_name(state)} (0x{state:02x})")
            if state != 0:
                raise SystemExit(2)
        elif args.command == "inspect":
            if args.transport == "classic":
                print(json.dumps(await printer.inspect(), indent=2))
                return
            print(json.dumps({"address": printer.address, "services": [
                {"uuid": service.uuid, "characteristics": [
                    {"uuid": c.uuid, "properties": c.properties,
                     "max_write": c.max_write_without_response_size}
                    for c in service.characteristics]}
                for service in printer.client.services]}, indent=2))
        elif args.command == "self-test":
            await printer.self_test()
            print("Built-in self-test requested. Check the paper for the printer's test pattern.")
        elif args.command == "cancel":
            state = await printer.cancel_job()
            print(f"Cancellation requested. PM290C: {status_name(state)} (0x{state:02x})")
            if state != 0:
                raise SystemExit(2)
        else:
            if args.transport == "ble":
                print("Warning: BLE image printing is unverified and has produced black blocks. Use the default Classic transport.", file=sys.stderr)
            print(f"Printing {image.height / 8:g} mm sticker via Bluetooth {args.transport}…", flush=True)
            await printer.print_job(job, image.height)
            print("Printer confirmed completion.")


def main():
    args = parser().parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nInterrupted. A partially transmitted sticker may need the printer restarted.", file=sys.stderr)
        raise SystemExit(130)
    except (PrinterError, BleakError, OSError, ValueError, TimeoutError) as exc:
        print(f"stickie: {exc}", file=sys.stderr)
        raise SystemExit(1)

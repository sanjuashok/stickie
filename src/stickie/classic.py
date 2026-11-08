"""macOS Bluetooth Classic transport, verified with a PM290C hardware print."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

from .protocol import status_name
from .transport import PrinterError


async def _helper():
    if sys.platform != "darwin":
        raise PrinterError("Bluetooth Classic currently requires macOS.")
    source = Path(__file__).with_name("native") / "ClassicBluetooth.swift"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    cache = Path(tempfile.gettempdir()) / f"stickie-native-{os.getuid()}" / digest
    binary = cache / "stickie-bluetooth"
    if binary.is_file():
        return binary
    cache.mkdir(parents=True, exist_ok=True)
    try:
        process = await asyncio.create_subprocess_exec(
            "xcrun", "swiftc", "-module-cache-path", str(cache / "modules"),
            str(source), "-o", str(binary),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, errors = await process.communicate()
    except FileNotFoundError as exc:
        raise PrinterError("Install Apple's Command Line Tools (xcode-select --install) to build the Bluetooth helper.") from exc
    if process.returncode:
        raise PrinterError("Could not build the Bluetooth helper: " + errors.decode(errors="replace")[-2000:])
    return binary


class ClassicPrinter:
    def __init__(self, address=None, timeout=30):
        self.address = address
        self.timeout = timeout
        self.binary = None

    async def __aenter__(self):
        self.binary = await _helper()
        return self

    async def __aexit__(self, *args):
        # Each operation owns one native connection, closed before it returns.
        pass

    async def _run(self, operation, payload=b"", wait=5):
        binary = self.binary or await _helper()
        process = await asyncio.create_subprocess_exec(
            str(binary), operation, self.address or "", str(wait),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        try:
            output, errors = await asyncio.wait_for(
                process.communicate(payload), self.timeout + wait + 8)
        except (TimeoutError, asyncio.CancelledError) as exc:
            if process.returncode is None:
                process.kill()
            await process.communicate()
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise PrinterError("Bluetooth operation timed out. Keep the printer on, disconnect other apps, and check the paper before retrying.") from exc
        try:
            result = json.loads(output)
        except (ValueError, UnicodeDecodeError) as exc:
            raise PrinterError("Bluetooth helper failed: " + errors.decode(errors="replace")[-1000:]) from exc
        if "error" in result:
            raise PrinterError(result["error"])
        if result.get("not_sent"):
            raise PrinterError(f"Printer is {status_name(result['status'])}. No print data was sent.")
        if result.get("during_print"):
            raise PrinterError(f"Printer reported {status_name(result['status'])} during printing. Check the paper before retrying.")
        if process.returncode:
            raise PrinterError(f"Bluetooth operation failed (exit {process.returncode}).")
        return result

    async def status(self):
        return (await self._run("status"))["status"]

    async def inspect(self):
        return await self._run("info")

    async def print_job(self, job, height):
        await self._run("print", job, wait=max(15, height / 8 / 3))

    async def self_test(self):
        await self._run("self-test", wait=7)

    async def cancel_job(self):
        return (await self._run("cancel", wait=6))["status"]


async def paired_printers():
    async with ClassicPrinter() as printer:
        return (await printer._run("list"))["devices"]

"""Bluetooth transport, and USB discovery/diagnostics.

USB exposes a CDC serial port but has not yet demonstrated print support.
"""
import asyncio
from bleak import BleakClient, BleakScanner
from serial.tools import list_ports
from .protocol import STATUS_QUERY, STATUS_NAMES, status_name

SERVICE = "0000ff00-0000-1000-8000-00805f9b34fb"
WRITE = "0000ff02-0000-1000-8000-00805f9b34fb"
NOTIFY = "0000ff01-0000-1000-8000-00805f9b34fb"


class PrinterError(RuntimeError):
    pass


def usb_devices():
    return [{"port": p.device, "description": p.description,
             "vid": p.vid, "pid": p.pid, "serial": p.serial_number}
            for p in list_ports.comports() if p.vid == 0x4C4A and p.pid == 0x4155]


async def scan(timeout=8):
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    return [{"name": a.local_name or d.name or "", "address": d.address,
             "rssi": a.rssi, "services": a.service_uuids}
            for d, a in found.values()
            if (a.local_name or d.name or "").upper().startswith("PM290")]


class BluetoothPrinter:
    def __init__(self, address=None, timeout=10):
        self.address = address
        self.timeout = timeout
        self.client = None
        self.replies = asyncio.Queue()

    async def __aenter__(self):
        if self.address:
            device = await BleakScanner.find_device_by_address(self.address, timeout=self.timeout)
        else:
            found = await BleakScanner.discover(timeout=self.timeout, return_adv=True)
            matches = [d for d, a in found.values()
                       if (a.local_name or d.name or "").upper() == "PM290C"]
            if len(matches) > 1:
                raise PrinterError("Multiple PM290C printers found. Use --device with an address from scan.")
            device = matches[0] if matches else None
        if device is None:
            raise PrinterError("PM290C not found. Turn it on, keep it nearby, and close other printer apps.")
        self.client = BleakClient(device, timeout=self.timeout)
        try:
            await self.client.connect()
            if not self.client.services.get_service(SERVICE):
                raise PrinterError("Device does not expose the expected PM290C Bluetooth service.")
            await self.client.start_notify(NOTIFY, self._notify)
        except BaseException:
            if self.client.is_connected:
                await self.client.disconnect()
            raise
        self.address = device.address
        return self

    def _notify(self, characteristic, data):
        self.replies.put_nowait(bytes(data))

    async def __aexit__(self, *args):
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    async def write(self, data):
        characteristic = self.client.services.get_characteristic(WRITE)
        size = min(128, characteristic.max_write_without_response_size)
        for offset in range(0, len(data), size):
            await self.client.write_gatt_char(characteristic, data[offset:offset + size], response=False)
            # Conservative pacing avoids overrunning the streaming print buffer.
            await asyncio.sleep(0.03)

    async def status(self):
        while not self.replies.empty():
            self.replies.get_nowait()
        await self.write(STATUS_QUERY)
        deadline = asyncio.get_running_loop().time() + 5
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise PrinterError("Printer did not answer the status query.")
            try:
                data = await asyncio.wait_for(self.replies.get(), remaining)
            except TimeoutError as exc:
                raise PrinterError("Printer did not answer the status query.") from exc
            if len(data) == 1:
                value = data[0]
                if value in STATUS_NAMES and value != 0:
                    await self.write(b"ACK\r\n")
                return value

    async def print_job(self, job, height):
        state = await self.status()
        if state != 0:
            raise PrinterError(f"Printer is {status_name(state)}. No print data was sent.")
        # Consume notifications during transmission so paper/heat faults stop the stream.
        sent = 0
        complete = False
        for start in range(0, len(job), 128):
            await self.write(job[start:start + 128])
            sent += len(job[start:start + 128])
            while not self.replies.empty():
                complete |= await self._print_reply(self.replies.get_nowait(), sent)
        deadline = asyncio.get_running_loop().time() + max(15, height / 8 / 3)
        while not complete:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise PrinterError("Print data sent, but completion was not confirmed. Check the paper before retrying.")
            try:
                data = await asyncio.wait_for(self.replies.get(), remaining)
            except TimeoutError as exc:
                raise PrinterError("Print data sent, but completion was not confirmed. Check the paper before retrying.") from exc
            complete = await self._print_reply(data, sent)

    async def self_test(self):
        state = await self.status()
        if state != 0:
            raise PrinterError(f"Printer is {status_name(state)}. Self-test was not sent.")
        await self.write(b"SELFTEST\r\n")
        # SELFTEST has no verified completion reply; keep the connection alive
        # briefly and report only that the command was sent.
        await asyncio.sleep(2)

    async def cancel_job(self):
        # Labelnize's BLE cancellation is the three ASCII bytes ESC.
        # Report the subsequent status; it cannot verify what is on paper.
        await self.write(b"ESC")
        await asyncio.sleep(1)
        return await self.status()

    async def _print_reply(self, data, sent):
        if len(data) == 1 and data[0] not in (0, 32):
            await self.write(b"ACK\r\n")
            raise PrinterError(f"Printer reported {status_name(data[0])} after {sent} bytes. Check the paper before retrying.")
        if len(data) == 5 and data[:2] == b"c ":
            await self.write(b"ACK\r\n")
        # c<space> requests the next copy; c<NUL> finishes the whole job.
        return data == b"c\x00"

import asyncio
from unittest.mock import AsyncMock
import pytest
from PIL import Image
from stickie.protocol import build_job, STATUS_QUERY
from stickie.render import render_text, render_image
from stickie.transport import BluetoothPrinter, PrinterError
from stickie.cli import parser, run


def test_packet_matches_app_streaming_order_and_pixel_polarity():
    image = Image.new("1", (384, 80), 1)
    image.putpixel((0, 0), 0)
    image.putpixel((7, 0), 0)
    job = build_job(image, 8)
    header = b"SIZE 48 mm,10 mm\r\nDIRECTION 0,0\r\nDENSITY 8\r\nCLS\r\nPRINT 1\r\nBITMAP 0,0,48,80,1,"
    assert job == header + b"\x7e" + b"\xff" * (48 * 80 - 1) + b"ALLEND\r\n"


@pytest.mark.parametrize("image,density", [
    (Image.new("1", (383, 80)), 8), (Image.new("RGB", (384, 80)), 8),
    (Image.new("1", (384, 79)), 8), (Image.new("1", (384, 8001)), 8),
    (Image.new("1", (384, 80)), -1), (Image.new("1", (384, 80)), 16),
])
def test_invalid_jobs_rejected(image, density):
    with pytest.raises(ValueError):
        build_job(image, density)


def test_text_wraps_and_is_not_blank():
    image = render_text("A fairly long line with several words " * 8)
    assert image.width == 384 and image.height > 80
    assert image.mode == "1"
    assert image.getextrema() == (0, 255)
    assert all(image.getpixel((0, y)) for y in range(image.height))


def test_long_word_wraps():
    image = render_text("W" * 80)
    assert image.height > 80
    assert all(image.getpixel((383, y)) for y in range(image.height))


def test_transparent_images_print_white_and_keep_aspect(tmp_path):
    path = tmp_path / "transparent.png"
    Image.new("RGBA", (20, 40), (0, 0, 0, 0)).save(path)
    image = render_image(str(path), margin=8)
    assert image.size == (384, 752)
    assert image.getextrema() == (255, 255)


def test_preview_does_not_connect(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Preview must not access Bluetooth")
    monkeypatch.setattr("stickie.cli.BluetoothPrinter", fail)
    monkeypatch.setattr("stickie.cli.ClassicPrinter", fail)
    path = tmp_path / "preview.png"
    args = parser().parse_args(["text", "Hello", "--preview", str(path)])
    asyncio.run(run(args))
    with Image.open(path) as image:
        assert image.size == (384, 80)


def test_paper_error_prevents_print_data():
    printer = BluetoothPrinter()
    printer.status = AsyncMock(return_value=4)
    printer.write = AsyncMock()
    with pytest.raises(PrinterError, match="out of paper.*No print data"):
        asyncio.run(printer.print_job(b"some job", 80))
    printer.write.assert_not_called()


def test_completion_requires_printer_reply():
    async def scenario():
        printer = BluetoothPrinter()
        printer.status = AsyncMock(return_value=0)
        async def write(data):
            if data == b"job":
                printer.replies.put_nowait(b"c\x00")
        printer.write = AsyncMock(side_effect=write)
        await printer.print_job(b"job", 80)
        printer.write.assert_awaited_once_with(b"job")
    asyncio.run(scenario())


def test_fault_during_send_stops_remaining_data():
    async def scenario():
        printer = BluetoothPrinter()
        printer.status = AsyncMock(return_value=0)
        async def write(data):
            if data != b"ACK\r\n":
                printer.replies.put_nowait(b"\x80")
        printer.write = AsyncMock(side_effect=write)
        with pytest.raises(PrinterError, match="overheated"):
            await printer.print_job(b"x" * 1024, 80)
        assert printer.write.await_count == 2
    asyncio.run(scenario())


def test_status_ignores_nonstatus_notifications():
    async def scenario():
        printer = BluetoothPrinter()
        async def write(data):
            assert data == STATUS_QUERY
            printer.replies.put_nowait(b"unrelated")
            printer.replies.put_nowait(b"\x00")
        printer.write = write
        assert await printer.status() == 0
    asyncio.run(scenario())


def test_next_copy_notification_is_not_job_completion():
    async def scenario():
        printer = BluetoothPrinter()
        printer.write = AsyncMock()
        assert not await printer._print_reply(b"c ", 100)
        assert not await printer._print_reply(b"c \x01\r\n", 100)
        printer.write.assert_awaited_once_with(b"ACK\r\n")
        assert await printer._print_reply(b"c\x00", 100)
    asyncio.run(scenario())


def test_self_test_rejects_paper_fault():
    printer = BluetoothPrinter()
    printer.status = AsyncMock(return_value=4)
    printer.write = AsyncMock()
    with pytest.raises(PrinterError, match="Self-test was not sent"):
        asyncio.run(printer.self_test())
    printer.write.assert_not_called()


def test_print_defaults_to_classic_not_the_broken_ble_path(monkeypatch, capsys):
    sent = []

    class WorkingTransport:
        def __init__(self, address, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def print_job(self, job, height):
            sent.append((job, height))

    def reject_ble(*args, **kwargs):
        raise AssertionError("Normal printing must not select the damaged BLE path")

    monkeypatch.setattr("stickie.cli.ClassicPrinter", WorkingTransport)
    monkeypatch.setattr("stickie.cli.BluetoothPrinter", reject_ble)
    asyncio.run(run(parser().parse_args(["text", "HELLO MAC"])))
    expected = render_text("HELLO MAC")
    assert sent == [(build_job(expected), expected.height)]
    assert "Printer confirmed completion" in capsys.readouterr().out

"""Per-segment colour (0xE1 0x03 with a colour per entry)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from lednetwf_ble import protocol
from lednetwf_ble.device import LEDNetWFDevice

SERVICE_UUID_5A00 = "00005a00-0000-1000-8000-00805f9b34fb"
ADV_PRODUCT_170 = bytes.fromhex("80070865F0065C6800AA210A0107")
ADV_PRODUCT_194 = bytes.fromhex("80070865F017581200C20E030105")


def make_device(service_data: bytes) -> LEDNetWFDevice:
    device = LEDNetWFDevice(MagicMock(), "AA:BB:CC:DD:EE:FF", "IOTBT967", product_id=0x00)
    device.update_from_advertisement({}, {SERVICE_UUID_5A00: service_data})
    return device


def test_frame_layout():
    packet = protocol.build_iotbt_segment_colors_command(
        [(0, 100, 100), (240, 100, 50), (0, 0, 0)]
    )
    payload = bytes(packet[8:])
    assert packet[7] == 0x0B
    assert payload == bytes.fromhex("e10300030000 03".replace(" ", "")) + bytes.fromhex(
        "a1006464" "a1786432" "a1000000"
    )
    # Transport header lengths match the payload.
    assert packet[4] << 8 | packet[5] == len(payload)
    assert packet[6] == len(payload) + 1


def test_uniform_matches_single_colour_builder():
    """Same colour on 20 segments gives the upstream single-colour frame."""
    single = protocol.build_iotbt_segment_color_command(0, 0, 255, 100)
    per_segment = protocol.build_iotbt_segment_colors_command([(240, 100, 100)] * 20)
    assert per_segment[8:] == single[8:]


@pytest.mark.parametrize("count", [0, protocol.IOTBT_SEGMENT_MAX_ENTRIES + 1])
def test_rejects_bad_counts(count):
    with pytest.raises(ValueError):
        protocol.build_iotbt_segment_colors_command([(0, 0, 0)] * count)


def test_max_entries_fit_one_frame():
    packet = protocol.build_iotbt_segment_colors_command(
        [(0, 100, 100)] * protocol.IOTBT_SEGMENT_MAX_ENTRIES
    )
    assert packet[6] <= 0xFF


def test_device_sends_scaled_values():
    device = make_device(ADV_PRODUCT_170)
    device._send_command = AsyncMock(return_value=True)
    ok = asyncio.run(device.set_segment_colors([(255, 0, 0), (0, 0, 0)], brightness=128))
    assert ok
    packet = device._send_command.call_args[0][0]
    assert bytes(packet[15:23]) == bytes.fromhex("a1006432" "a1000000")


def test_device_refuses_non_segment():
    device = make_device(ADV_PRODUCT_194)
    device._send_command = AsyncMock()
    assert asyncio.run(device.set_segment_colors([(255, 0, 0)])) is False
    device._send_command.assert_not_called()

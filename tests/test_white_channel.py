"""White-channel override for IOTBT segment devices.

Product 170 (0xAA, "Symphony_Line") covers both the IOTBTC68 lamp, which has a
warm-white channel (issue #114), and RGB-only addressable strings such as
300 ft permanent outdoor lights, which ignore the 0xE0 0x01 0x00 0xB1 white
command. The override lets the user say which one they have.
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from lednetwf_ble.const import WHITE_CHANNEL_CHOICES
from lednetwf_ble.device import LEDNetWFDevice

SERVICE_UUID_5A00 = "00005a00-0000-1000-8000-00805f9b34fb"

# IOTBTC68, issue #114: product 0x00AA (170).
ADV_PRODUCT_170 = bytes.fromhex("80070865F0065C6800AA210A0107")
# IOTBT6BA, issue #83: product 0x00AD (173), segment, no known white channel.
ADV_PRODUCT_173 = bytes.fromhex("80070865F0BBB6BA00AD1F0A010D")
# IOTBT812: product 0x00C2 (194), Telink.
ADV_PRODUCT_194 = bytes.fromhex("80070865F017581200C20E030105")


def make_device(service_data: bytes, name: str = "IOTBT967") -> LEDNetWFDevice:
    device = LEDNetWFDevice(MagicMock(), "AA:BB:CC:DD:EE:FF", name, product_id=0x00)
    device.update_from_advertisement({}, {SERVICE_UUID_5A00: service_data})
    return device


def test_choices():
    assert WHITE_CHANNEL_CHOICES == ("auto", "present", "none")


def test_auto_keeps_product_default():
    device = make_device(ADV_PRODUCT_170)
    assert device.is_iotbt_segment
    assert device.white_channel_override == "auto"
    assert device.has_segment_white


@pytest.mark.parametrize("value", [None, "auto", "bogus"])
def test_unknown_values_mean_auto(value):
    device = make_device(ADV_PRODUCT_170)
    device.set_white_channel_override("none")
    device.set_white_channel_override(value)
    assert device.white_channel_override == "auto"
    assert device.has_segment_white


def test_none_removes_white_on_rgb_only_string():
    device = make_device(ADV_PRODUCT_170)
    device.set_white_channel_override("none")
    assert not device.has_segment_white
    # Colour and scenes stay on the segment command set.
    assert device.is_iotbt_segment


def test_none_clears_reported_white_mode():
    device = make_device(ADV_PRODUCT_170)
    device._white_mode = True
    device.set_white_channel_override("none")
    assert not device.white_mode


def test_present_enables_white_on_other_segment_products():
    device = make_device(ADV_PRODUCT_173)
    assert device.is_iotbt_segment
    assert not device.has_segment_white
    device.set_white_channel_override("present")
    assert device.has_segment_white


def test_present_ignored_off_the_segment_family():
    device = make_device(ADV_PRODUCT_194)
    assert not device.is_iotbt_segment
    device.set_white_channel_override("present")
    assert not device.has_segment_white


def test_set_white_refused_when_channel_disabled():
    device = make_device(ADV_PRODUCT_170)
    device.set_white_channel_override("none")
    device._send_command = MagicMock()
    assert asyncio.run(device.set_white(255)) is False
    device._send_command.assert_not_called()

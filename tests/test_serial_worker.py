from rgb_sound.serial_worker import SerialWorker, encode_lighting_command, parse_button_event, parse_frame


def test_parse_valid_frame():
    assert parse_frame("0|255|512|1023\r\n") == (0, 255, 512, 1023)


def test_parse_invalid_frames():
    assert parse_frame("1|2|3") is None
    assert parse_frame("1|two|3|4") is None
    assert parse_frame("1|2|3|-1") is None


def test_parse_mute_button_event():
    assert parse_button_event("BTN|MUTE\r\n") == "MUTE"
    assert parse_button_event("FX|SYNC") is None


def test_encode_lighting_command():
    packet = encode_lighting_command({
        "mode": "solid", "color": "#12abef", "brightness": 50,
        "speed": 20, "showVolumeProgress": True,
    })
    assert packet[:7] == bytes((0xA5, 0x81, 128, 20, 0x12, 0xAB, 0xEF))
    assert packet[7] == packet[0] ^ packet[1] ^ packet[2] ^ packet[3] ^ packet[4] ^ packet[5] ^ packet[6]


def test_lighting_update_is_queued_without_reconnect():
    worker = SerialWorker(lambda: {}, lambda _frame: None, lambda: True)
    lighting = {"mode": "off", "brightness": 0, "speed": 1, "color": "#000000", "showVolumeProgress": False}
    worker.update_lighting(lighting)

    assert worker._lighting_pending.is_set()
    assert worker._pending_lighting == encode_lighting_command(lighting)

    class Connection:
        written = None

        def write(self, packet):
            self.written = packet

    connection = Connection()
    worker._write_pending_lighting(connection)
    assert connection.written == encode_lighting_command(lighting)
    assert not worker._lighting_pending.is_set()
    assert worker._pending_lighting is None

from pnp.firmware.emulator import DMA, GPIO, UART, FirmwareEmulator, Timer


def test_emulator_init():
    emu = FirmwareEmulator("stm32")
    st = emu.get_status()
    assert st["target"] == "stm32"
    assert st["timers"] == 14
    assert st["uarts"] == 5


def test_gpio():
    g = GPIO(port="A")
    g.set_mode(0, 1)
    g.write_pin(0, 1)
    assert g.read_pin(0) == 1
    g.toggle_pin(0)
    assert g.read_pin(0) == 0


def test_timer():
    t = Timer(id=1, period=10)
    t.start()
    for _ in range(10):
        t.tick()
    assert t.interrupt


def test_uart():
    u = UART(id=1)
    u.transmit(b"hello")
    assert not u.is_tx_ready()
    u.rx_buffer.extend(b"world")
    assert u.is_rx_available()
    data = u.receive(5)
    assert data == b"world"


def test_dma():
    d = DMA(id=1)
    d.configure(0, 0x1000, 0x2000, 5)
    d.start(0)
    assert d.active[0]
    for _ in range(5):
        d.tick()
    assert d.is_complete(0)


def test_emulator_run():
    emu = FirmwareEmulator("stm32")
    emu.run(100)
    assert emu.tick_count == 100


def test_emulator_reset():
    emu = FirmwareEmulator("stm32")
    emu.run(50)
    emu.reset()
    assert emu.tick_count == 0

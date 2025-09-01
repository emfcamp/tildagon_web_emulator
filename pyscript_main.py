import asyncio
import math
import sys
import time

from pyweb import pydom
from pyscript import when
from pyodide.ffi import to_js
from js import (
    CanvasRenderingContext2D as Context2d,
    ImageData,
    Uint8ClampedArray,
    console,
    document,
)


async def monkey_patch_http():
    # requests doesn't work in pyscript without this voodoo

    import micropip
    await micropip.install("pyodide-http")
    await micropip.install("requests")

    import pyodide_http
    pyodide_http.patch_all()


def monkey_patch_sys():
    if not hasattr(sys, "print_exception"):
        def print_exception(e, file):
            print("Exception:", e, file=file)
        sys.print_exception = print_exception


def monkey_patch_tildagon_helpers():
    class FakeHelpers:
        @staticmethod
        def esp_wifi_set_max_tx_power(*args, **kwargs):
            pass

        @staticmethod
        def esp_wifi_sta_wpa2_ent_set_identity(*args, **kwargs):
            pass

        @staticmethod
        def esp_wifi_sta_wpa2_ent_set_username(*args, **kwargs):
            pass

        @staticmethod
        def esp_wifi_sta_wpa2_ent_set_password(*args, **kwargs):
            pass

    sys.modules["tildagon_helpers"] = FakeHelpers


def monkey_patch_network():
    class FakeNetwork:
        STA_IF = 0
        AP_IF = 1

        class FakeWLAN:
            def __init__(self, interface):
                self.interface = interface
                self._active = True
                self._connected = True

            def active(self, is_active=None):
                if is_active is None:
                    return self._active
                else:
                    self._active = is_active

            def connect(self, ssid, password):
                print(f"Fake connect to SSID {ssid} with password {password}")
                self._connected = True

            def disconnect(self):
                print("Fake disconnect")
                self._connected = False

            def isconnected(self):
                return self._connected

            def status(self):
                if not self._active:
                    return 0

        def __init__(self):
            pass

        def WLAN(self, interface):
            return self.FakeWLAN(interface)

    sys.modules["network"] = FakeNetwork()


def monkey_patch_time():
    if not hasattr(time, "ticks_us"):
        time.ticks_us = lambda: int(time.time_ns() / 1000)

    if not hasattr(time, "ticks_diff"):
        time.ticks_diff = lambda a, b: a - b

    if not hasattr(time, "ticks_ms"):
        time.ticks_ms = lambda: int(time.time_ns() / 1_000_000)

    if not hasattr(time, "ticks_add"):
        time.ticks_add = lambda a, b: a + b


class FakeCtx:
    def __init__(self):
        self.width = 240
        self.height = 240
        self.scale = 3   # The number of web pixels per "display" pixel
        self.border = 10

        self.font_size = 8

        self.CENTER = 1
        self.LEFT = 2
        self.RIGHT = 3
        self.MIDDLE = 4

        self.color = "rgb(0, 255, 0)"   # FIXME: find what the default color is
        self.position = (0, 0)
        self._rectange = None

    def _x_to_web(self, x):
        return ((x + self.width // 2) * self.scale) + self.border

    def _y_to_web(self, y):
        return ((y + self.height // 2) * self.scale) + self.border

    def clone(self):
        ctx = FakeCtx()
        ctx.color = self.color
        ctx.position = self.position
        return ctx

    def gray(self, v):
        new = self.clone()
        new.color = f"rgb({v}, {v}, {v})"
        return new

    def save(self):
#        print("Not implemented: FakeCtx: save()")
        pass

    def restore(self):
#        print("Not implemented: FakeCtx: restore()")
        pass

    def move_to(self, x, y):
#        print("ctx.move_to(%s, %s)" % (x, y))
        new = self.clone()
        new.position = (x, y)
        return new

    def rgb(self, r, g, b):
        new = self.clone()
        new.color = f"rgb({r}, {g}, {b})"
        return new

    def rectangle(self, x, y, w, h):
        canvas = pydom["#screen canvas"][0]
        ctx = canvas._js.getContext("2d")
        ctx.save()
        ctx.beginPath()
        ctx.arc(
            (3 * self.width + 2 * self.border) / 2,
            (3 * self.height + 2 * self.border) / 2,
            (3 * self.width) / 2,
            0,
            2 * math.pi,
        )
        ctx.closePath()
        ctx.clip()

        ctx.fillStyle = self.color
        ctx.strokeStyle = self.color
        ctx.beginPath()
        ctx.rect(self._x_to_web(x), self._y_to_web(y), w * self.scale, h * self.scale)
        ctx.stroke()
        ctx.restore()

        # We need to stash the rectable for fill()
        self._rectangle = (x, y, w, h)
        return self

    def fill(self):
        if self._rectangle:
            x, y, w, h = self._rectangle
            canvas = pydom["#screen canvas"][0]
            ctx = canvas._js.getContext("2d")
            ctx.save()
            ctx.beginPath()
            ctx.arc(
                (3 * self.width + 2 * self.border) / 2,
                (3 * self.height + 2 * self.border) / 2,
                (3 * self.width) / 2,
                0,
                2 * math.pi,
            )
            ctx.closePath()
            ctx.clip()

            ctx.fillStyle = self.color
            ctx.fillRect(self._x_to_web(x), self._y_to_web(y), w * self.scale, h * self.scale)
            ctx.restore()

            self._rectangle = None
        else:
            print("FakeCtx: fill() called without a rectangle")

        return self

    def text_width(self, text):
#        print("Not properly implemented: FakeCtx: text_width(%s)" % text)
        return len(text) * 8

    def text(self, text):
        canvas = pydom["#screen canvas"][0]
        ctx = canvas._js.getContext("2d")
        ctx.save()
        ctx.beginPath()
        ctx.arc(
            (3 * self.width + 2 * self.border) / 2,
            (3 * self.height + 2 * self.border) / 2,
            (3 * self.width) / 2,
            0,
            2 * math.pi,
        )
        ctx.closePath()
        ctx.clip()

        ctx.fillStyle = self.color
        ctx.font = f"{8 * self.scale}px sans-serif"
        x, y = self.position
#        print("Drawing text at", self._x_to_web(x), self._y_to_web(y), "in color", self.color)
        ctx.fillText(text, self._x_to_web(x), self._y_to_web(y))
        ctx.restore()

        return self


def monkey_patch_display():
    # In Tildagon OS, display is a module with a set of functions.
    # In PyScript, we will make display a class then patch it into the modules

    class FakeDisplay:
        @staticmethod
        def gfx_init():
            print("Fake gfx_init()")

        @staticmethod
        def hexagon(ctx, x, y, dim):
            print("Not implemented: FakeDisplay: hexagon(%s, %s, %s)" % (x, y, dim))

        @staticmethod
        def get_ctx():
            return FakeCtx()

        @staticmethod
        def end_frame(ctx):
#            print("Not implemented: FakeDisplay: end_frame()")
            pass

    sys.modules["display"] = FakeDisplay

    class FakeGC9A01PY:
        pass

    sys.modules["gc9a01py"] = FakeGC9A01PY


def monkey_patch_machine():
    class FakePin:
        IN = 1
        OUT = 2

        def __init__(self, pin, mode=None):
            self.pin = pin
            self.mode = mode

        def value(self):
            return 0

    class FakeI2C:
        pass

    class FakeSPI:
        pass

    from types import ModuleType
    m = ModuleType("machine")
    sys.modules[m.__name__] = m

    sys.modules["machine.I2C"] = FakeI2C
    sys.modules["machine.SPI"] = FakeSPI
    sys.modules["machine.Pin"] = FakePin


def monkey_patch_tildagon():
    from types import ModuleType
    m = ModuleType("tildagon")
    sys.modules[m.__name__] = m

    class FakeEPin:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            pass

    class FakePin:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            pass

    sys.modules["tildagon.ePin"] = FakeEPin
    sys.modules["tildagon.Pin"] = FakePin


def monkey_patch_ePin():
    from types import ModuleType
    m = ModuleType("egpio")
    sys.modules[m.__name__] = m

    class FakeEPin:
        def __init__(self, pin):
            self.IN = 1
            self.OUT = 3
            self.PWM = 8
            self.pin = pin
            self.IRQ_RISING = 1
            self.IRQ_FALLING = 2

        def init(self, mode):
            pass

        def on(self):
            pass

        def off(self):
            pass

        def duty(self, duty):
            pass

        def value(self, value=None):
            return 1

        def irq(self, handler, trigger):
            pass

        def __call__(self, *args, **kwargs):
            pass

    sys.modules["egpio.ePin"] = FakeEPin


def monkey_patch_neopixel():
    class FakeNeoPixel:
        def __init__(self, *args, **kwargs):
            self.length = 12
            self.rgb = [(0, 0, 0)] * self.length

        def write(self):
            for led in range(self.length):
                canvas = pydom[f"#led{led} canvas"][0]
                ctx = canvas._js.getContext("2d")
                style = f"rgb({self.rgb[led][0]} {self.rgb[led][1]} {self.rgb[led][2]})"
                ctx.fillStyle = style
                ctx.beginPath()
                ctx.arc(10, 10, 10, 0, 2 * math.pi)
                ctx.fill()
                ctx.closePath()
                canvas.style["display"] = "block"

        def fill(self, color):
            print("Not yet implemented: FakeNeoPixel: fill", color)

        def __setitem__(self, item, value):
            if item > self.length:
                print("FakeNeoPixel: Ignoring setitem out of range", item)
            else:
                self.rgb[item-1] = value

    class FakeNeoPixelModule:
        NeoPixel = FakeNeoPixel

    sys.modules["neopixel"] = FakeNeoPixelModule


async def badge():
    resolution_x = 240
    resolution_y = 240
    border = 10

    # FIXME: for now draw leds as a grey circle
    #        - we need to lay them out properly in the HTML
    #        - we need to hook them up to the code
    for led in range(6):
        canvas = pydom[f"#led{led} canvas"][0]
        ctx = canvas._js.getContext("2d")
        ctx.fillStyle = "rgb(100 100 100)"
        ctx.beginPath()
        ctx.arc(10, 10, 5, 0, 2 * math.pi)
        ctx.fill()
        ctx.closePath()
        canvas.style["display"] = "block"

    canvas = pydom["#screen canvas"][0]
    ctx = canvas._js.getContext("2d")

    # Set the canvas size
    width = 3 * resolution_x + 2 * border
    height = 3 * resolution_y + 2 * border

    canvas.style["width"] = f"{width}px"
    canvas.style["height"] = f"{height}px"
    canvas._js.width = width
    canvas._js.height = height

    # Draw a green circle for the screen border
    ctx.fillStyle = "rgb(0 100 0)"
    ctx.beginPath()
    ctx.arc(
        (3 * resolution_x + 2 * border) / 2,
        (3 * resolution_y + 2 * border) / 2,
        (3 * resolution_x + 2 * border) / 2,
        0,
        2 * math.pi,
    )
    ctx.fill()
    ctx.closePath()

    # Draw a black circle for the screen
    ctx.fillStyle = "rgb(0 0 0)"
    ctx.beginPath()
    ctx.arc(
        (3 * resolution_x + 2 * border) / 2,
        (3 * resolution_y + 2 * border) / 2,
        (3 * resolution_x) / 2,
        0,
        2 * math.pi,
    )
    ctx.fill()
    ctx.closePath()

    # Show the canvas
    canvas.style["display"] = "block"

    await start_tildagon_os()


async def button_handler(event):
    print("Button pressed:", event.target.id)

    from system.eventbus import eventbus
    from frontboards.twentyfour import BUTTONS
    from events.input import ButtonDownEvent, ButtonUpEvent
    print("Emitting ButtonDownEvent for button", BUTTONS[event.target.id])
    await eventbus.emit_async(ButtonDownEvent(button=BUTTONS[event.target.id]))


async def start_tildagon_os():
    # Fix up differences between MicroPython and PyScript
    monkey_patch_time()
    monkey_patch_display()
    monkey_patch_machine()
    monkey_patch_tildagon()
    monkey_patch_neopixel()
    monkey_patch_ePin()
    monkey_patch_sys()
    monkey_patch_network()
    monkey_patch_tildagon_helpers()
    await monkey_patch_http()

    import main
    # Everything gets started on the import above


async def main():
    _ = await asyncio.gather(badge())

asyncio.ensure_future(main())

import asyncio
import math
import sys
import time

from pyweb import pydom
from pyscript import when, document
from pyodide.ffi import to_js, create_proxy
from js import (
    CanvasRenderingContext2D as Context2d,
    ImageData,
    Uint8ClampedArray,
    console,
    document,
)


def monkey_patch_micropython():
    class FakeMicropython:
        @staticmethod
        def const(x):
            return x

    sys.modules["micropython"] = FakeMicropython
    print("Implementation: " + sys.implementation.name)
    sys.implementation.name = "micropython"
    print("Implementation is now: " + sys.implementation.name)


def patch_filesystem():
    # New apps are downloaded to /apps and /backgrounds
    # It's hardcoded. We need to make sure files out of those
    # directories are importable.
    import os

    os.mkdir("/apps")
    os.symlink("/apps", "/home/pyodide/apps")

    os.mkdir("/backgrounds")
    os.symlink("/backgrounds", "/home/pyodide/backgrounds")


async def monkey_patch_http():
    # requests doesn't work in pyscript without this voodoo

    import micropip

    await micropip.install("pyodide-http")
    await micropip.install("requests")

    import pyodide_http

    pyodide_http.patch_all()

    import requests

    # We rewrite requests via a CORS proxy because otherwise we can't fetch
    # tarballs from github/etc
    def get(url, *args, **kwargs):
        print("Requests.get(", url, args, kwargs, ")")
        url = "https://api.codetabs.com/v1/proxy?quest=" + url
        print("Request rewritten to", url)
        try:
            return requests.real_get(url, *args, **kwargs)
        except Exception as e:
            print("Exception in requests.get:", e)
            raise

    requests.real_get = requests.get
    requests.get = get


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
        self.scale = 1  # The number of web pixels per "display" pixel
        self.border = 10

        self.font_size = 8

        self.CENTER = 1
        self.LEFT = 2
        self.RIGHT = 3
        self.MIDDLE = 4

        self.color = "rgb(0, 255, 0)"  # FIXME: find what the default color is
        self.position = (0, 0)
        self._translate = (0, 0)
        self._saves = []
        self._gradient = None

        self._canvas = pydom["#screen canvas"][0]
        self._ctx = self._canvas._js.getContext("2d")

        self._ctx.beginPath()
        self._ctx.arc(
            (self.scale * self.width + 2 * self.border) / 2,
            (self.scale * self.height + 2 * self.border) / 2,
            (self.scale * self.width) / 2,
            0,
            2 * math.pi,
        )
        self._ctx.closePath()
        self._ctx.clip()

    def _x_to_web(self, x):
        return ((x + self._translate[0] + self.width // 2) * self.scale) + self.border

    def _y_to_web(self, y):
        return ((y + self._translate[1] + self.height // 2) * self.scale) + self.border

    def translate(self, x, y):
        new = self.clone()
        new._translate = (x, y)
        return new

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
        new = self.clone()
        new._saves.append(self)
        return new

    def restore(self):
        if len(self._saves) > 0:
            return self._saves.pop()
        else:
            #            print("Warning: restore() called with no matching save()")
            return self

    def move_to(self, x, y):
        #        print("ctx.move_to(%s, %s)" % (x, y))
        new = self.clone()
        new.position = (x, y)
        return new

    def rgb(self, r, g, b):
        new = self.clone()
        new.color = f"rgb({r}, {g}, {b})"
        return new

    def rgba(self, r, g, b, a):
        new = self.clone()
        new.color = f"rgba({r}, {g}, {b}, {a})"
        return new

    def rectangle(self, x, y, w, h):
        ctx = self._ctx
        if not self._gradient:
            ctx.fillStyle = self.color
            ctx.strokeStyle = self.color
        ctx.beginPath()
        ctx.rect(self._x_to_web(x), self._y_to_web(y), w * self.scale, h * self.scale)
        ctx.stroke()

        return self

    def image(self, path, x, y, w, h):
        import base64

        with open(path, "rb") as f:
            data = f.read()
        if path.endswith(".jpg") or path.endswith(".jpeg"):
            encoded = base64.b64encode(data).decode("utf-8")
            src = "data:image/jpeg;base64," + encoded
        elif path.endswith(".png"):
            encoded = base64.b64encode(data).decode("utf-8")
            src = "data:image/png;base64," + encoded
        else:
            print("Unsupported image format:", path)
            return self
        img = document.createElement("img")
        img.src = src

        ctx = self._ctx
        ctx.drawImage(
            img, self._x_to_web(x), self._y_to_web(y), w * self.scale, h * self.scale
        )
        return self

    def linear_gradient(self, x0, y0, x1, y1):
        ctx = self._ctx
        gradient = ctx.createLinearGradient(
            self._x_to_web(x0),
            self._y_to_web(y0),
            self._x_to_web(x1),
            self._y_to_web(y1),
        )
        self._gradient = gradient
        return self

    def add_stop(self, offset, color, alpha):
        if self._gradient:
            # FIXME: We should add alpha to tuple and use rgba()
            self._gradient.addColorStop(offset, "rgb" + str(color))
        return self

    def fill(self):
        ctx = self._ctx

        ctx.fillStyle = self.color
        ctx.fill()

        return self

    def text_width(self, text):
        #        print("Not properly implemented: FakeCtx: text_width(%s)" % text)
        return len(text) * 8

    def text(self, text):
        ctx = self._ctx

        ctx.fillStyle = self.color
        ctx.font = f"{8 * self.scale}px sans-serif"
        x, y = self.position
        #        print("Drawing text at", self._x_to_web(x), self._y_to_web(y), "in color", self.color)
        ctx.fillText(text, self._x_to_web(x), self._y_to_web(y))
        ctx.restore()

        return self

    def clip(self):
        ctx = self._ctx
        ctx.clip()
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


def neopixel_rgb_to_canvas_style(values):
    r, g, b = values
    if r > 1:
        r /= 255
    if g > 1:
        g /= 255
    if b > 1:
        b /= 255
    r = min(1.0, max(0.0, r))
    g = min(1.0, max(0.0, g))
    b = min(1.0, max(0.0, b))
    return f"color(srgb {pow(r, 1 / 2.2)} {pow(g, 1 / 2.2)} {pow(b, 1 / 2.2)})"


def monkey_patch_neopixel():
    class FakeNeoPixel:
        def __init__(self, *args, **kwargs):
            self.length = 12
            self.rgb = [(0, 0, 0)] * self.length

        def write(self):
            for led in range(self.length):
                canvas = pydom[f"#led{led} canvas"][0]
                ctx = canvas._js.getContext("2d")
                ctx.fillStyle = neopixel_rgb_to_canvas_style(self.rgb[led])
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
                self.rgb[item - 1] = value

    class FakeNeoPixelModule:
        NeoPixel = FakeNeoPixel

    sys.modules["neopixel"] = FakeNeoPixelModule


async def badge():
    resolution_x = 240
    resolution_y = 240
    border = 10

    for led in range(6):
        canvas = pydom[f"#led{led} canvas"][0]
        canvas.style["display"] = "block"

    canvas = pydom["#screen canvas"][0]
    ctx = canvas._js.getContext("2d")

    # Set the canvas size
    width = 1 * resolution_x + 2 * border
    height = 1 * resolution_y + 2 * border

    canvas.style["width"] = f"{width}px"
    canvas.style["height"] = f"{height}px"
    canvas._js.width = width
    canvas._js.height = height

    # Draw a green circle for the screen border
    ctx.fillStyle = "rgb(0 100 0)"
    ctx.beginPath()
    ctx.arc(
        (1 * resolution_x + 2 * border) / 2,
        (1 * resolution_y + 2 * border) / 2,
        (1 * resolution_x + 2 * border) / 2,
        0,
        2 * math.pi,
    )
    ctx.fill()
    ctx.closePath()

    # Draw a black circle for the screen
    ctx.fillStyle = "rgb(0 0 0)"
    ctx.beginPath()
    ctx.arc(
        (1 * resolution_x + 2 * border) / 2,
        (1 * resolution_y + 2 * border) / 2,
        (1 * resolution_x) / 2,
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


@create_proxy
async def on_key_down(event):
    from system.eventbus import eventbus
    from frontboards.twentyfour import BUTTONS
    from events.input import ButtonDownEvent, ButtonUpEvent

    match event.key:
        case "ArrowUp":
            print("Emitting ButtonDownEvent for button A")
            await eventbus.emit_async(ButtonDownEvent(button=BUTTONS["A"]))
        case "ArrowDown":
            print("Emitting ButtonDownEvent for button D")
            await eventbus.emit_async(ButtonDownEvent(button=BUTTONS["D"]))
        case "ArrowLeft":
            print("Emitting ButtonDownEvent for button F")
            await eventbus.emit_async(ButtonDownEvent(button=BUTTONS["F"]))
        case "ArrowRight":
            print("Emitting ButtonDownEvent for button C")
            await eventbus.emit_async(ButtonDownEvent(button=BUTTONS["C"]))
        case _:
            print("Key down:", event.key, "code:", event.code)


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
    monkey_patch_micropython()
    await monkey_patch_http()
    patch_filesystem()

    document.addEventListener("keydown", on_key_down)

    import main
    # Everything gets started on the import above


async def main():
    _ = await asyncio.gather(badge())


asyncio.ensure_future(main())

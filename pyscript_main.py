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
    console
)

def monkey_patch_sys():
    if not hasattr(sys, "print_exception"):
        def print_exception(e, file):
            print("Exception:", e, file=file)
        sys.print_exception = print_exception


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

        self.CENTER = 1
        self.LEFT = 2
        self.RIGHT = 3
        self.MIDDLE = 4

    def save(self):
        print("Not implemented: FakeCtx: save()")

    def restore(self):
        print("Not implemented: FakeCtx: restore()")

    def move_to(self, x, y):
        print("Not implemented: FakeCtx: move_to(%s, %s)" % (x, y))
        return self

    def rgb(self, r, g, b):
        print("Not implemented: FakeCtx: rgb(%f, %f, %f)" % (r, g, b))
        return self

    def rectangle(self, x, y, w, h):
        print("Not implemented: FakeCtx: rectangle(%s, %s, %s, %s)" % (x, y, w, h))
        return self

    def fill(self):
        print("Not implemented: FakeCtx: fill()")
        return self

    def text_width(self, text):
        print("Not implemented: FakeCtx: text_width(%s)" % text)
        return len(text) * 8

    def text(self, text):
        print("Not implemented: FakeCtx: text(%s)" % text)
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
            print("Not implemented: FakeDisplay: end_frame()")

    sys.modules["display"] = FakeDisplay

def monkey_patch_machine():
    class FakePin:
        def __init__(self, pin, mode):
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
        pass

    class FakePin:
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

    sys.modules["egpio.ePin"] = FakeEPin


def monkey_patch_neopixel():
    class FakeNeoPixel:
        def __init__(self, *args, **kwargs):
            self.length = 6
            self.rgb = [(0,0,0)] * 6

        def write(self):
            for led in range(self.length):
                canvas = pydom[f"#led{led} canvas"][0]
                ctx = canvas._js.getContext("2d")
                ctx.fillStyle = f"rgb{self.rgb[led]}"
                ctx.beginPath()
                ctx.arc(10, 10, 10, 0, 2 * math.pi)
                ctx.fill()
                ctx.closePath()

        def fill(self, color):
            print("Not yet implemented: FakeNeoPixel: fill", color)

        def __setitem__(self, item, value):
            if item > self.length:
                print("FakeNeoPixel: Ignoring setitem out of range", item)
            else:
                self.rgb[item] = value
            

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
        ctx.arc(10, 10, 10, 0, 2 * math.pi)
        ctx.fill()
        ctx.closePath()
        canvas.style["display"] = "block"

    canvas = pydom["#screen canvas"][0]
    ctx = canvas._js.getContext("2d")

    # Set the canvas size
    width= 3 * resolution_x + 2 * border
    height= 3 * resolution_y + 2 * border

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


async def start_tildagon_os():
    # Fix up differences between MicroPython and PyScript
    monkey_patch_time()
    monkey_patch_display()
    monkey_patch_machine()
    monkey_patch_tildagon()
    monkey_patch_neopixel()
    monkey_patch_ePin()
    monkey_patch_sys()

    import main
    # Everything gets started on the import above

async def main():
    _ = await asyncio.gather(badge())

asyncio.ensure_future(main())


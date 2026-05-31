import js

_RING_START = 1
_RING_COUNT = 12
_buf = [(0, 0, 0)] * (_RING_START + _RING_COUNT)

def set_rgb(ix, r, g, b):
    if 0 <= ix < len(_buf):
        if r > 1: r /= 255
        if g > 1: g /= 255
        if b > 1: b /= 255
        _buf[ix] = (r, g, b)

def get_rgb(ix):
    return _buf[ix] if 0 <= ix < len(_buf) else (0, 0, 0)

def set_all_rgb(r, g, b):
    for i in range(_RING_START, _RING_START + _RING_COUNT):
        set_rgb(i, r, g, b)

def update():
    for ring_i in range(_RING_COUNT):
        r, g, b = _buf[_RING_START + ring_i]
        js.updateLed(ring_i, r, g, b)

def get_steady():
    return False

def set_slew_rate(b):
    pass

def get_slew_rate():
    return 255

def set_auto_update(b):
    pass

def set_brightness(b):
    pass

def set_gamma(r, g, b):
    pass

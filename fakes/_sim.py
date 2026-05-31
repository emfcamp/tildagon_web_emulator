import js as _js

class _Buttons:
    @staticmethod
    def state():
        try:
            return [int(x) for x in str(_js.getBadgeButtonStates()).split(',')]
        except Exception:
            return [0, 0, 0, 0, 0, 0]


class _SimModule:
    buttons = _Buttons()

    def leds_update(self):
        import leds
        leds.update()

_sim = _SimModule()

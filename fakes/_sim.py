import js as _js

class _Buttons:
    @staticmethod
    def state():
        try:
            raw = str(_js.getBadgeButtonStates()).split(',')
            from frontboards.twentyfour import TwentyTwentyFour
            return [int(raw['ABCDEF'.index(k)]) for k in TwentyTwentyFour.button_states.keys()]
        except Exception:
            return [0, 0, 0, 0, 0, 0]


class _SimModule:
    buttons = _Buttons()

    def leds_update(self):
        import leds
        leds.update()

_sim = _SimModule()

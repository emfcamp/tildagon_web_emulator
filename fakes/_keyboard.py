import asyncio
import js
from events.keyboard import KEYBOARD_BUTTONS
from events.input import ButtonDownEvent, ButtonUpEvent
from system.eventbus import eventbus

async def keyboard_task():
    while True:
        raw = js.getKeyboardEvent()
        if raw is not None and str(raw) != 'None':
            event_type, key = str(raw).split(':', 1)
            button = KEYBOARD_BUTTONS.get(key)
            if button:
                if event_type == 'down':
                    eventbus.emit(ButtonDownEvent(button=button))
                else:
                    eventbus.emit(ButtonUpEvent(button=button))
        await asyncio.sleep_ms(50)

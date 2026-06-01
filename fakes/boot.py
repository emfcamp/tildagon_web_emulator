import io
import js
import requests
import time

# Micropython SHOULD be able to await on javascript promises directly since
# 1.27 but for the life of me I can't get it to work and ended up in a twisty
# maze of micropython async bugs. Instead we patch requests to trigger a fetch
# in javascript land, then it polls for the fetch to complete. Ugly but it
# works.

_CORS_PROXY = 'https://api.codetabs.com/v1/proxy?quest='

def _request(method, url, data=None, json=None, **kwargs):
    body = None
    content_type = None
    if json is not None:
        body = _json.dumps(json)
        content_type = 'application/json'
    elif data is not None:
        body = data

    fetch_id = js.mp_fetch_start(_CORS_PROXY + url, method, body, content_type)
    while True:
        result = js.mp_fetch_poll(fetch_id)
        if result is not None:
            break
        # This causes a yield back from WASM to JS because we've patched
        # the micropython HAL sleep() to use emscripten_sleep()
        time.sleep_ms(100)

    resp = requests.Response(io.BytesIO(bytes(result.body)))
    resp.status_code = int(result.status)
    return resp

requests.request = _request

import asyncio
from autostart import autostart
asyncio.create_task(autostart())

import asyncio
import io
import json as _json
import js
import requests

# Micropython SHOULD be able to await on javascript promises directly since
# 1.27 but for the life of me I can't get it to work and ended up in a twisty
# maze of micropython async bugs. Instead we patch requests to trigger a fetch
# in javascript land, then it polls for the fetch to complete. Ugly but it
# works.

_CORS_PROXY = 'https://api.codetabs.com/v1/proxy?quest='

async def _request(method, url, data=None, json=None, **kwargs):
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
        await asyncio.sleep(0.1)

    r = _json.loads(str(result))
    resp = requests.Response(io.BytesIO(r['body'].encode('utf-8')))
    resp.status_code = r['status']
    return resp

requests.request = _request

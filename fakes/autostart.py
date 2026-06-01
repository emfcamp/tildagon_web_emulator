import asyncio
import display
import js
import requests
import time
from firmware_apps.app_store import install_app, list_all_apps
from system.scheduler import scheduler
from system.scheduler.events import RequestStartAppEvent
from system.eventbus import eventbus

APP_STORE_INDEX_URL = 'https://apps.badge.emfcamp.org/demo_api/apps.json'

def draw_text(line1, line2):
    ctx = display.get_ctx()
    ctx.save()
    ctx.gray(0).rectangle(-120, -120, 240, 240).fill()
    ctx.gray(1)
    ctx.text_align = ctx.CENTER
    ctx.text_baseline = ctx.MIDDLE
    ctx.font_size = 18
    ctx.move_to(0, -15).text(line1)
    ctx.font_size = 14
    ctx.move_to(0, 10).text(line2)
    ctx.restore()
    display.end_frame(ctx)

async def autostart():
    fragment = js.getFragment()
    if not fragment or str(fragment) == 'None':
        return

    parts = str(fragment).split('/', 1)
    if len(parts) != 2:
        return
    category, name = parts

    print(f'Autostart: looking for {category}/{name}')
    draw_text('Loading App', f'{category}/{name}')
    resp = requests.get(APP_STORE_INDEX_URL)

    app_entry = None
    for item in resp.json()['items']:
        manifest_app = item.get('manifest', {}).get('app', {})
        if manifest_app.get('name') == name and manifest_app.get('category') == category:
            app_entry = item
            break

    if app_entry is None:
        print(f'Autostart: {category}/{name} not found in app store')
        draw_text(f'{category}/{name}', 'Not found in app store')
        time.sleep(30)
        return

    print(f'Autostart: installing {name}')
    install_app(app_entry)

    installed = [a for a in list_all_apps() if a.get('name') == name]
    if not installed:
        print(f'Autostart: {name} not found after install')
        draw_text(f'{category}/{name}', 'Failed to install')
        time.sleep(30)
        return

    # Wait for the OS to load
    while not scheduler.update_tasks:
        await asyncio.sleep(0.1)

    print(f'Autostart: launching {name}')
    entry = installed[0]
    module = __import__(entry['path'], None, None, (entry['callable'],))
    app_instance = getattr(module, entry['callable'])()
    eventbus.emit(RequestStartAppEvent(app_instance, foreground=True))

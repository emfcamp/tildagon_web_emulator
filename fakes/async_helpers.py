import asyncio


async def unblock(func, periodic_func, *args, **kwargs):
    try:
        result = func(*args, **kwargs)
        if hasattr(result, 'send'):
            result = await result
    except Exception as e:
        result = e
    await periodic_func()
    if isinstance(result, Exception):
        raise result
    return result

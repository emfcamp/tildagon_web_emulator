import ctx as _ctx

def gfx_init():
    pass

def get_ctx():
    c = _ctx.Context()
    c.start_frame()
    c.save()
    c.translate(120, 120)
    return c

def end_frame(c):
    c.restore()
    c.end_frame()

def hexagon(ctx, x, y, dim):
    ctx.round_rectangle(x - dim, y - dim, 2 * dim, 2 * dim, dim).fill()

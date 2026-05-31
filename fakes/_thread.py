def start_new_thread(func, args, kwargs={}):
    pass

def get_ident():
    return 0

def allocate_lock():
    return _Lock()

class _Lock:
    def acquire(self, *a, **kw):
        return True
    def release(self):
        pass
    def locked(self):
        return False
    def __enter__(self):
        return self
    def __exit__(self, *a):
        pass

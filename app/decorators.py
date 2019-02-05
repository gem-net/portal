from threading import Thread
from functools import wraps


def asynch(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        thr = Thread(target=fn, args=args, kwargs=kwargs)
        thr.start()
    return wrapper

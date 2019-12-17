from threading import Thread
from functools import wraps

from flask import request, redirect, url_for
from flask_login import current_user


def asynch(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        thr = Thread(target=fn, args=args, kwargs=kwargs)
        thr.start()
    return wrapper


def membership_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_anonymous or not current_user.in_cgem:
            return redirect(url_for('index', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

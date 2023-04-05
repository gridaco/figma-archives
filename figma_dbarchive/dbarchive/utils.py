def px(r):
    if r is None:
        return None
    return round(r, 2)

def o(r):
    if r is None:
        return None
    return round(r, 4)

def deg(r):
    if r is None:
        return None
    return round(r, 2)

def getfrom(obj, *args, default=None, fallback=None):
    for key in args:
        try:
            obj = obj[key]
        except (KeyError, TypeError):
            return default
    return obj if obj is not None else fallback
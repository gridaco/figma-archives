from typing import List, Union
import math

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

Transform = List[List[float]]

def angle_from_transform(transform: Union[Transform, None] = None) -> int:
    if not transform:
        return 0

    try:
        a, b, c = transform[0]
        d, e, f = transform[1]
        angle = round(math.atan2(b, a) * (180 / math.pi))
        return angle + 360 if angle < 0 else angle
    except Exception:
        return 0
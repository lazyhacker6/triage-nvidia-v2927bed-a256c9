def quote(s, safe="/"):
    from urllib.parse import quote as _q
    return _q(s, safe=safe)

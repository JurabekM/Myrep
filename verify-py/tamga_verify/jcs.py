"""TR-JSON kanonikalashtirish (spec §2.1): RFC 8785, faqat butun sonlar."""

MAX_SAFE = 2**53 - 1

_ESC = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}


class NotCanonical(ValueError):
    pass


def canonical(v) -> str:
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        if abs(v) > MAX_SAFE:
            raise NotCanonical("butun son oraliqdan tashqarida")
        return str(v)
    if isinstance(v, float):
        raise NotCanonical("butun bo'lmagan son")
    if isinstance(v, str):
        out = ['"']
        for ch in v:
            if ch in _ESC:
                out.append(_ESC[ch])
            elif ord(ch) < 0x20:
                out.append(f"\\u{ord(ch):04x}")
            elif 0xD800 <= ord(ch) <= 0xDFFF:
                raise NotCanonical("yolg'iz surrogat")
            else:
                out.append(ch)
        out.append('"')
        return "".join(out)
    if isinstance(v, list):
        return "[" + ",".join(canonical(x) for x in v) + "]"
    if isinstance(v, dict):
        keys = sorted(v, key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(canonical(k) + ":" + canonical(v[k]) for k in keys) + "}"
    raise NotCanonical(f"qo'llab-quvvatlanmaydigan tur: {type(v).__name__}")


def without(obj: dict, key: str) -> dict:
    return {k: v for k, v in obj.items() if k != key}

# -*- coding: utf-8 -*-
"""Yengil log moduli — RAM'da oxirgi N ta yozuvni ham saqlaydi (web dashboard uchun)."""

import time

_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}

_level = 20
_ring = []
_RING_MAX = 40


def set_level(name):
    global _level
    _level = _LEVELS.get(name, 20)


def _stamp():
    t = time.localtime()
    return "%02d:%02d:%02d" % (t[3], t[4], t[5])


def _emit(tag, msg):
    line = "%s [%s] %s" % (_stamp(), tag, msg)
    print(line)
    _ring.append(line)
    if len(_ring) > _RING_MAX:
        del _ring[0]


def debug(msg):
    if _level <= 10:
        _emit("DBG", msg)


def info(msg):
    if _level <= 20:
        _emit("INF", msg)


def warn(msg):
    if _level <= 30:
        _emit("WRN", msg)


def error(msg):
    if _level <= 40:
        _emit("ERR", msg)


def tail(n=20):
    return _ring[-n:]

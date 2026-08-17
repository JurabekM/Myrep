# -*- coding: utf-8 -*-
"""Offline buffer — tarmoq yo'q paytda o'lchovlarni flash'ga yozib turadi.

Format: har bir qator = bitta JSON obyekt (JSONL).
2 MB flash cheklovi tufayli yozuvlar soni qattiq cheklangan.
"""

import json
import os
import config
import logger


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def count():
    if not _exists(config.BUFFER_FILE):
        return 0
    n = 0
    with open(config.BUFFER_FILE) as f:
        for _ in f:
            n += 1
    return n


def append(record):
    """Yozuvni buferga qo'shadi. Limit oshsa eng eski yozuvlarni tashlaydi."""
    try:
        with open(config.BUFFER_FILE, "a") as f:
            f.write(json.dumps(record))
            f.write("\n")
    except OSError as e:
        logger.error("Bufer yozish xatosi: %r" % e)
        return False

    if count() > config.BUFFER_MAX_RECORDS:
        _trim()
    return True


def _trim():
    """Eng eski yozuvlarni o'chirib, limitning 80% ini qoldiradi."""
    keep = int(config.BUFFER_MAX_RECORDS * 0.8)
    try:
        with open(config.BUFFER_FILE) as f:
            lines = f.readlines()
        with open(config.BUFFER_FILE + ".tmp", "w") as f:
            for line in lines[-keep:]:
                f.write(line)
        os.remove(config.BUFFER_FILE)
        os.rename(config.BUFFER_FILE + ".tmp", config.BUFFER_FILE)
        logger.info("Bufer qisqartirildi: %d yozuv qoldi" % keep)
    except OSError as e:
        logger.error("Bufer trim xatosi: %r" % e)


def drain(limit=50):
    """Buferdan yozuvlarni o'qiydi (o'chirmaydi). `commit()` bilan tasdiqlanadi."""
    if not _exists(config.BUFFER_FILE):
        return []
    out = []
    with open(config.BUFFER_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue          # buzilgan qatorni o'tkazib yuboramiz
            if len(out) >= limit:
                break
    return out


def commit(n):
    """Muvaffaqiyatli yuborilgan birinchi n ta yozuvni o'chiradi."""
    if not _exists(config.BUFFER_FILE):
        return
    try:
        with open(config.BUFFER_FILE) as f:
            lines = f.readlines()
        rest = lines[n:]
        if rest:
            with open(config.BUFFER_FILE + ".tmp", "w") as f:
                for line in rest:
                    f.write(line)
            os.remove(config.BUFFER_FILE)
            os.rename(config.BUFFER_FILE + ".tmp", config.BUFFER_FILE)
        else:
            os.remove(config.BUFFER_FILE)
    except OSError as e:
        logger.error("Bufer commit xatosi: %r" % e)


def clear():
    if _exists(config.BUFFER_FILE):
        os.remove(config.BUFFER_FILE)


def free_space():
    s = os.statvfs("/")
    return s[0] * s[3]      # bsize * bavail

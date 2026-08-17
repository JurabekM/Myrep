# -*- coding: utf-8 -*-
"""Home Assistant MQTT Discovery — qurilma HA'da avtomatik paydo bo'ladi.

HA `homeassistant/sensor/<obj_id>/config` topigiga retained xabar kutadi.
Har bir sensor bitta config xabari; hammasi bitta `device` ostida guruhlanadi.
"""

import json
import config
import sensors as sensors_mod
import logger


def _device_block(mac):
    return {
        "identifiers": [config.DEVICE_NAME],
        "name": config.DEVICE_NAME,
        "model": config.DEVICE_MODEL,
        "manufacturer": "Raspberry Pi",
        "sw_version": "1.0.0",
        "connections": [["mac", mac]],
        "suggested_area": config.LOCATION,
    }


async def publish(client, mac, fields):
    """`fields` — e'lon qilinadigan kalitlar ro'yxati (state JSON kalitlari)."""
    if not config.HA_DISCOVERY:
        return

    dev = _device_block(mac)
    published = 0

    for key in fields:
        meta = sensors_mod.FIELDS.get(key)
        if not meta:
            continue
        label, unit, device_class, icon = meta
        obj_id = "%s_%s" % (config.DEVICE_NAME.replace("-", "_"), key)

        payload = {
            "name": label,
            "unique_id": obj_id,
            "object_id": obj_id,
            "state_topic": config.TOPIC_STATE,
            "availability_topic": config.TOPIC_AVAIL,
            "payload_available": "online",
            "payload_not_available": "offline",
            "value_template": "{{ value_json.%s }}" % key,
            "unit_of_measurement": unit,
            "state_class": "measurement",
            "icon": icon,
            "device": dev,
        }
        if device_class:
            payload["device_class"] = device_class

        topic = "%s/sensor/%s/config" % (config.HA_PREFIX, obj_id)
        await client.publish(topic, json.dumps(payload), retain=True, qos=1)
        published += 1

    logger.info("HA discovery: %d ta sensor e'lon qilindi" % published)


async def remove(client, fields):
    """Discovery yozuvlarini o'chirish (bo'sh retained payload)."""
    for key in fields:
        obj_id = "%s_%s" % (config.DEVICE_NAME.replace("-", "_"), key)
        topic = "%s/sensor/%s/config" % (config.HA_PREFIX, obj_id)
        await client.publish(topic, b"", retain=True, qos=1)

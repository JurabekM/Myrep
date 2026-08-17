# -*- coding: utf-8 -*-
"""Pico W IoT sensor node — asosiy dastur.

Arxitektura: bitta asyncio event loop, 5 ta mustaqil vazifa
  sensor_task     — sensorni davriy o'qiydi, tarixni yuritadi
  publish_task    — MQTT'ga yuboradi, offline bo'lsa buferga yozadi
  network_task    — Wi-Fi va MQTT ulanishini tiklab turadi
  web             — lokal dashboard (asyncio.start_server)
  health_task     — watchdog, GC, holat LED'i

Hech bir vazifa boshqasini bloklamaydi.
"""

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

import gc
import json
import machine
import os
import sys
import time

import config
import logger
import buffer
import ha_discovery
import web
from machine import Pin, WDT
from mqtt import MQTTClient, MQTTError
from sensors import Sensors
from wifi import WiFi, sync_time

VERSION = "1.0.0"


class AppState:
    """Barcha vazifalar bo'lishadigan umumiy holat."""

    def __init__(self):
        self.boot_ms = time.ticks_ms()
        self.data = {}
        self.history = {"temperature": [], "humidity": []}
        self.ip = None
        self.rssi = None
        self.wifi_ok = False
        self.mqtt_ok = False
        self.wifi_drops = 0
        self.mqtt_drops = 0
        self.published = 0
        self.buffered = 0
        self.last_read = 0
        self.commands = []
        self.sample_interval = config.SAMPLE_INTERVAL
        self.publish_interval = config.PUBLISH_INTERVAL

    def uptime(self):
        return time.ticks_diff(time.ticks_ms(), self.boot_ms) // 1000

    def free_flash(self):
        try:
            return buffer.free_space()
        except Exception:
            return 0

    def last_read_str(self):
        if not self.last_read:
            return "-"
        t = time.localtime(self.last_read + config.TZ_OFFSET)
        return "%02d:%02d:%02d" % (t[3], t[4], t[5])

    def push_history(self, data):
        for key in self.history:
            if key in data:
                h = self.history[key]
                h.append(data[key])
                if len(h) > config.HISTORY_POINTS:
                    del h[0]

    def queue_command(self, cmd):
        if cmd in ("reboot", "clear_buffer", "resync", "publish_now"):
            self.commands.append(cmd)
            return True
        return False


state = AppState()
sensors = Sensors()
wifi = WiFi()
mqtt = None
led = None


# --------------------------------------------------------------------------- #
# MQTT
# --------------------------------------------------------------------------- #
def _make_client():
    return MQTTClient(
        client_id=config.DEVICE_NAME,
        host=config.MQTT_HOST,
        port=config.MQTT_PORT,
        user=config.MQTT_USER,
        password=config.MQTT_PASSWORD,
        keepalive=config.MQTT_KEEPALIVE,
        ssl=config.MQTT_SSL,
        # Last Will: qurilma tirik emasligini broker o'zi e'lon qiladi
        will=(config.TOPIC_AVAIL, b"offline", True, 1),
    )


def _on_message(topic, payload):
    """Kiruvchi MQTT buyruqlari."""
    try:
        t = topic.decode()
        p = payload.decode()
    except Exception:
        return
    logger.info("MQTT cmd: %s = %s" % (t, p))

    try:
        obj = json.loads(p)
    except ValueError:
        obj = {"cmd": p.strip()}

    cmd = obj.get("cmd", "")
    if cmd == "set_interval":
        val = int(obj.get("value", config.PUBLISH_INTERVAL))
        state.publish_interval = max(10, val)
        logger.info("Yuborish intervali -> %d s" % state.publish_interval)
    else:
        state.queue_command(cmd)


async def _after_connect():
    """Har safar MQTT ulangandan keyin bajariladi."""
    await mqtt.publish(config.TOPIC_AVAIL, b"online", retain=True, qos=1)
    await mqtt.subscribe(config.TOPIC_CMD, qos=1)
    fields = [k for k in state.data if k in ("temperature", "humidity", "pressure",
                                             "dew_point", "core_temp")]
    fields += ["rssi", "uptime"]
    await ha_discovery.publish(mqtt, wifi.mac(), fields)


# --------------------------------------------------------------------------- #
# Vazifalar
# --------------------------------------------------------------------------- #
async def sensor_task():
    while True:
        try:
            data = sensors.read()
            state.data = data
            state.last_read = data.get("ts", time.time())
            state.push_history(data)
            logger.debug("O'lchov: %s" % data)
        except Exception as e:
            logger.error("sensor_task: %r" % e)
        await asyncio.sleep(state.sample_interval)


async def publish_task():
    # birinchi o'lchov tayyor bo'lguncha kutamiz
    while not state.data:
        await asyncio.sleep(1)

    while True:
        payload = dict(state.data)
        payload["rssi"] = wifi.rssi()
        payload["uptime"] = state.uptime()
        payload["free_mem"] = gc.mem_free()

        sent = False
        if mqtt and mqtt.connected:
            try:
                await mqtt.publish(config.TOPIC_STATE, json.dumps(payload), qos=1)
                state.published += 1
                sent = True
                await _flush_buffer()
            except (MQTTError, OSError) as e:
                logger.warn("Publish muvaffaqiyatsiz: %r" % e)
                state.mqtt_ok = False

        if not sent:
            buffer.append(payload)
            state.buffered = buffer.count()
            logger.info("Offline — buferga yozildi (%d ta)" % state.buffered)

        await asyncio.sleep(state.publish_interval)


async def _flush_buffer():
    """Ulanish tiklangach buferdagi yozuvlarni yuboradi."""
    n = buffer.count()
    if not n:
        state.buffered = 0
        return
    logger.info("Buferdan %d yozuv yuborilmoqda" % n)
    while True:
        batch = buffer.drain(limit=20)
        if not batch:
            break
        ok = 0
        for rec in batch:
            try:
                rec["replay"] = True
                await mqtt.publish(config.TOPIC_STATE, json.dumps(rec), qos=1)
                ok += 1
                await asyncio.sleep_ms(50)   # brokerni bosmaymiz
            except Exception as e:
                logger.warn("Bufer yuborish to'xtadi: %r" % e)
                break
        buffer.commit(ok)
        if ok < len(batch):
            break
    state.buffered = buffer.count()


async def network_task():
    """Wi-Fi va MQTT ni tirik ushlab turadi."""
    global mqtt
    while True:
        # --- Wi-Fi ---
        if not wifi.is_connected():
            if state.wifi_ok:
                state.wifi_drops += 1
                logger.warn("Wi-Fi uzildi")
            state.wifi_ok = False
            state.mqtt_ok = False
            await wifi.ensure()
            if wifi.is_connected():
                state.wifi_ok = True
                state.ip = wifi.ip()
                await sync_time()
        else:
            state.wifi_ok = True
            state.ip = wifi.ip()
            state.rssi = wifi.rssi()

        # --- MQTT ---
        if state.wifi_ok and (mqtt is None or not mqtt.connected):
            if state.mqtt_ok:
                state.mqtt_drops += 1
            state.mqtt_ok = False
            try:
                if mqtt:
                    await mqtt._close()
                mqtt = _make_client()
                mqtt.callback = _on_message
                mqtt.on_connect = _after_connect
                await mqtt.connect()
                asyncio.create_task(mqtt.keepalive_task())
                state.mqtt_ok = True
                await _flush_buffer()
            except Exception as e:
                logger.warn("MQTT ulanmadi: %r" % e)
                await asyncio.sleep(10)
        elif mqtt and mqtt.connected:
            state.mqtt_ok = True

        await asyncio.sleep(3)


async def command_task():
    """Web/MQTT dan kelgan buyruqlarni bajaradi."""
    while True:
        while state.commands:
            cmd = state.commands.pop(0)
            logger.info("Buyruq bajarilmoqda: %s" % cmd)
            if cmd == "reboot":
                if mqtt and mqtt.connected:
                    try:
                        await mqtt.publish(config.TOPIC_AVAIL, b"offline", retain=True)
                    except Exception:
                        pass
                await asyncio.sleep(1)
                machine.reset()
            elif cmd == "clear_buffer":
                buffer.clear()
                state.buffered = 0
            elif cmd == "resync":
                await sync_time()
            elif cmd == "publish_now":
                if mqtt and mqtt.connected:
                    try:
                        await mqtt.publish(config.TOPIC_STATE, json.dumps(state.data), qos=1)
                    except Exception:
                        pass
        await asyncio.sleep(1)


async def health_task(wdt):
    """Watchdog, xotira va holat indikatori.

    LED namunasi:  1 chaqnash = hammasi joyida
                   2 chaqnash = Wi-Fi bor, MQTT yo'q
                   uzluksiz   = Wi-Fi yo'q
    """
    while True:
        if wdt:
            wdt.feed()

        if state.wifi_ok and state.mqtt_ok:
            blinks = 1
        elif state.wifi_ok:
            blinks = 2
        else:
            blinks = 0

        if blinks == 0:
            led.on()
            await asyncio.sleep_ms(400)
            led.off()
            await asyncio.sleep_ms(400)
        else:
            for _ in range(blinks):
                led.on()
                await asyncio.sleep_ms(40)
                led.off()
                await asyncio.sleep_ms(180)
            await asyncio.sleep(3)

        if gc.mem_free() < 24000:
            gc.collect()
            logger.debug("GC: bo'sh RAM %d B" % gc.mem_free())


# --------------------------------------------------------------------------- #
# Ishga tushirish
# --------------------------------------------------------------------------- #
async def main():
    global led

    logger.set_level(config.LOG_LEVEL)
    logger.info("=" * 46)
    logger.info("Pico W IoT node v%s  (%s)" % (VERSION, config.DEVICE_NAME))
    logger.info("MicroPython: %s" % sys.version)
    logger.info("Sabab: %s" % machine.reset_cause())

    # DIQQAT: Pico W da LED GP25 emas, CYW43 chipining WL_GPIO0 pinida.
    # Shuning uchun raqam emas, "LED" nomi bilan ochiladi.
    led = Pin("LED", Pin.OUT)
    led.on()

    sensors.init()
    state.data = sensors.read()
    state.buffered = buffer.count()

    web.bind(state)

    # Wi-Fi — birinchi urinish
    if not await wifi.connect():
        if config.AP_FALLBACK:
            wifi.start_ap()
            state.ip = wifi.ip()
    else:
        state.wifi_ok = True
        state.ip = wifi.ip()
        await sync_time()

    if config.WEB_ENABLED:
        await web.start()

    # Watchdog eng oxirida yoqiladi — start sekin bo'lsa reboot qilib yubormasin
    wdt = None
    try:
        wdt = WDT(timeout=config.WDT_TIMEOUT)
        logger.info("Watchdog yoqildi (%d ms)" % config.WDT_TIMEOUT)
    except Exception as e:
        logger.warn("Watchdog yoqilmadi: %r" % e)

    tasks = [
        asyncio.create_task(sensor_task()),
        asyncio.create_task(publish_task()),
        asyncio.create_task(network_task()),
        asyncio.create_task(command_task()),
        asyncio.create_task(health_task(wdt)),
    ]
    logger.info("%d ta vazifa ishga tushdi" % len(tasks))
    await asyncio.gather(*tasks)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    logger.info("Ctrl-C — to'xtatildi")
    try:
        Pin("LED", Pin.OUT).off()
    except Exception:
        pass
except Exception as e:
    # Kutilmagan xato — traceback'ni flash'ga yozib, qayta yuklaymiz
    logger.error("FATAL: %r" % e)
    try:
        with open("crash.log", "a") as f:
            f.write("--- %d ---\n" % time.time())
            sys.print_exception(e, f)
    except Exception:
        pass
    sys.print_exception(e)
    time.sleep(5)
    machine.reset()

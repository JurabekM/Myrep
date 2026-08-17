# -*- coding: utf-8 -*-
"""
UzERP namuna plugini.

Har bir tasdiqlangan savdoni plugin logiga yozadi va web menyuga
"Plugin namunasi" bandini qo'shadi. O'z pluginlaringizni yozishda
shu fayldan andoza sifatida foydalaning.
"""

PLUGIN_NAME = "Namuna plugin"
PLUGIN_VERSION = "1.0"
PLUGIN_DESCRIPTION = "Savdo hodisalarini kuzatuvchi o'quv plugini"


def register(api):
    """Plugin kirish nuqtasi — UzERP yuklanganda bir marta chaqiriladi."""

    def on_sale_confirmed(doc_id=None, doc_type=None, total=None, **kwargs):
        api.log.info(
            "[sample_plugin] Savdo tasdiqlandi: #%s (%s), summa=%s",
            doc_id, doc_type, total,
        )

    api.bus.subscribe("sale.confirmed", on_sale_confirmed)
    api.add_menu_item("Plugin namunasi", "/plugins")

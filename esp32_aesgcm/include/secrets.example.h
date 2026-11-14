/*
 * Bu faylni `secrets.h` deb nusxalang va kalitni o'zingizniki bilan almashtiring.
 * `secrets.h` ni git'ga qo'shmang (.gitignore da turibdi).
 *
 * Yangi kalit yaratish:
 *     python3 tools/aesgcm_peer.py keygen
 *
 * Quyidagi kalit FAQAT NAMUNA — hammaga ma'lum, haqiqiy qurilmada ishlatmang.
 */
#ifndef SECRETS_H
#define SECRETS_H

#include <stdint.h>

static const uint8_t AES_KEY[32] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
    0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f,
};

/* AAD: shifrlanmaydi, lekin teg bilan himoyalanadi. Ikki tomonda bir xil bo'lsin. */
#define DEVICE_ID "esp32-01"

#endif /* SECRETS_H */

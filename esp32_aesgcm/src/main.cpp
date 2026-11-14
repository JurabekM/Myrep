// AES-256-GCM demo: Serial'dan kelgan har bir satrni shifrlaydi, hex ko'rinishda
// chiqaradi, so'ng qayta deshifrlab tekshiradi.
#include <Arduino.h>
#include <string.h>

#include "aesgcm.h"

#if __has_include("secrets.h")
#  include "secrets.h"
#else
#  error "include/secrets.example.h ni include/secrets.h deb nusxalang va kalitni almashtiring"
#endif

extern "C" {
#include "bootloader_random.h"
}

static const size_t MAX_TEXT = 256;

static void printHex(const uint8_t *buf, size_t len) {
  for (size_t i = 0; i < len; i++) {
    Serial.printf("%02x", buf[i]);
  }
  Serial.println();
}

// NIST GCM test vektori (AES-256, 14-holat): kutubxona to'g'ri ishlayotganini
// qurilmaning o'zida tekshiradi.
static bool selfTest() {
  static const uint8_t expected[AESGCM_NONCE_LEN + 16 + AESGCM_TAG_LEN] = {
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0xce, 0xa7, 0x40, 0x3d, 0x4d, 0x60, 0x6b, 0x6e,
      0x07, 0x4e, 0xc5, 0xd3, 0xba, 0xf3, 0x9d, 0x18,
      0xd0, 0xd1, 0xc8, 0xa7, 0x99, 0x99, 0x6b, 0xf0,
      0x26, 0x5b, 0x98, 0xb5, 0xd4, 0x8a, 0xb9, 0x19,
  };
  const uint8_t key[AESGCM_KEY_LEN] = {0};
  const uint8_t nonce[AESGCM_NONCE_LEN] = {0};
  const uint8_t pt[16] = {0};
  uint8_t packet[sizeof expected];
  uint8_t back[sizeof pt];
  size_t n = 0;

  if (aesgcm_encrypt_with_nonce(key, nonce, pt, sizeof pt, nullptr, 0,
                                packet, sizeof packet, &n) != AESGCM_OK ||
      n != sizeof expected || memcmp(packet, expected, n) != 0) {
    return false;
  }
  if (aesgcm_decrypt(key, packet, n, nullptr, 0, back, sizeof back, &n) != AESGCM_OK ||
      n != sizeof pt || memcmp(back, pt, n) != 0) {
    return false;
  }
  packet[AESGCM_NONCE_LEN] ^= 0x01;  // bitta bit buzilsa, rad etilishi shart
  if (aesgcm_decrypt(key, packet, sizeof packet, nullptr, 0,
                     back, sizeof back, &n) != AESGCM_ERR_AUTH) {
    return false;
  }
  // Bo'sh xabar (faqat teg): ESP-IDF dagi GCM porti NULL buferga sezgir.
  if (aesgcm_encrypt(key, nullptr, 0, nullptr, 0, packet, sizeof packet, &n) != AESGCM_OK ||
      n != AESGCM_OVERHEAD) {
    return false;
  }
  return aesgcm_decrypt(key, packet, n, nullptr, 0, nullptr, 0, &n) == AESGCM_OK && n == 0;
}

static void handleLine(const String &line) {
  const uint8_t *aad = (const uint8_t *)DEVICE_ID;
  const size_t aadLen = strlen(DEVICE_ID);

  uint8_t packet[MAX_TEXT + AESGCM_OVERHEAD];
  size_t packetLen = 0;
  int rc = aesgcm_encrypt(AES_KEY, (const uint8_t *)line.c_str(), line.length(),
                          aad, aadLen, packet, sizeof packet, &packetLen);
  if (rc != AESGCM_OK) {
    Serial.printf("Shifrlash xatosi: %d\n", rc);
    return;
  }
  Serial.printf("Paket (%u bayt): ", (unsigned)packetLen);
  printHex(packet, packetLen);

  uint8_t plain[MAX_TEXT + 1];
  size_t plainLen = 0;
  rc = aesgcm_decrypt(AES_KEY, packet, packetLen, aad, aadLen,
                      plain, MAX_TEXT, &plainLen);
  if (rc != AESGCM_OK) {
    Serial.printf("Deshifrlash xatosi: %d\n", rc);
    return;
  }
  plain[plainLen] = '\0';
  Serial.printf("Deshifrlandi: %s\n", (const char *)plain);

  packet[packetLen - 1] ^= 0x01;  // tegning oxirgi bitini buzamiz
  rc = aesgcm_decrypt(AES_KEY, packet, packetLen, aad, aadLen,
                      plain, MAX_TEXT, &plainLen);
  Serial.printf("Buzilgan paket: %s\n\n",
                rc == AESGCM_ERR_AUTH ? "rad etildi (to'g'ri)" : "XATO: qabul qilindi!");
}

void setup() {
  Serial.begin(115200);
  delay(500);

  // WiFi/Bluetooth yoqilmagan bo'lsa, ESP32 ning tasodifiy sonlar generatori
  // haqiqiy entropiya olmaydi. Bu chaqiruv entropiya manbaini yoqadi.
  // WiFi yoki BLE ishlatadigan loyihada bu satrni OLIB TASHLANG (ular bilan
  // ziddiyatga boradi; radio yoqilgach generator o'zi haqiqiy tasodifiy bo'ladi).
  // Bu rejimda ADC va I2S ham band bo'ladi.
  bootloader_random_enable();

  Serial.println();
  Serial.printf("O'z-o'zini tekshirish: %s\n", selfTest() ? "o'tdi" : "O'TMADI");
  Serial.println("Matn yozib Enter bosing:");
}

void loop() {
  if (!Serial.available()) {
    delay(10);
    return;
  }
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) {
    return;
  }
  if (line.length() > MAX_TEXT) {
    Serial.printf("Matn juda uzun (ko'pi bilan %u bayt)\n", (unsigned)MAX_TEXT);
    return;
  }
  handleLine(line);
}

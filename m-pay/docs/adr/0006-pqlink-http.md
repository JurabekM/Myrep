# ADR-0006: PQ Link HTTP ustida xabar darajasida

* Holat: qabul qilingan (2026-10-23)

## Kontekst

Interfeys — HTTP API. PQ Link qurilma ↔ server kanali bo'lishi kerak.

## Qaror

PQ Link xabarlari HTTP `POST` tanasida (`application/x-mpay-pqlink`): handshake
`/v1/pqlink/hello` va `/v1/pqlink/finish`, keyin qurilma endpointlari (`/v1/tokens`, ...)
muhrlangan yozuv qabul qiladi va muhrlangan yozuv qaytaradi. Yozuv ichida JSON.
Server sessiyalarni xotirada TTL bilan saqlaydi.

## Oqibatlar

* PQ Link TLS'dan mustaqil: TLS buzilsa ham (yoki TLS proksi'da ochilsa ham) PAN va LUK himoyalangan.
* So'rov-javob tartibi yozuvlar `seq` ni qat'iy monoton qiladi — replay oddiy tekshiriladi.
* Ko'p instansiyali deployment'da sessiyalar umumiy saqlanishi kerak (`TODO(spec):`).

## Muqobillar

* Alohida TCP protokol — qo'shimcha port, proksi/firewall muammolari.
* WebSocket — holatli ulanish, Android fon cheklovlari.

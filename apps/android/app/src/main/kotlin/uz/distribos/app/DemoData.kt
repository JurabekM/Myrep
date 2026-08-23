package uz.distribos.app

import uz.distribos.data.db.CustomerEntity
import uz.distribos.data.db.DistribosDatabase
import uz.distribos.data.db.MovementEntity
import uz.distribos.data.db.ProductEntity
import uz.distribos.data.db.StockEntity
import uz.distribos.data.db.WarehouseEntity
import uz.distribos.sync.CommandService

/**
 * Namuna ma'lumot — FAQAT debug build'da.
 *
 * Reliz build'da bu kod umuman chaqirilmaydi (`BuildConfig.DEBUG`
 * tekshiruvi `AppContainer` da). Haqiqiy foydalanuvchi bo'sh bazadan
 * boshlaydi va ma'lumotni desktopdan sinxronizatsiya orqali oladi.
 *
 * Nega kerak: bo'sh ekranni ko'rib "ishlayaptimi yoki yo'qmi" deb bilib
 * bo'lmaydi. Namuna ma'lumot bilan har bir ekranni haqiqatan tekshirish
 * mumkin.
 *
 * ## Nima uchun katalog TO'G'RIDAN-TO'G'RI bazaga yoziladi
 *
 * Mahsulot va mijozni AGENT yarata olmaydi — bu `Permissions` da
 * ataylab taqiqlangan (narxni faqat rahbar belgilaydi). Real hayotda
 * telefon bu ma'lumotni desktopdan SINXRONIZATSIYA orqali oladi.
 * Shuning uchun namuna katalog ham xuddi shunday — buyruq orqali emas,
 * "kelib tushgan ma'lumot" sifatida yoziladi.
 *
 * Buyurtma va to'lov esa agentning O'Z amali, shuning uchun ular
 * `CommandService` orqali o'tadi va outbox'ga tushadi.
 */
object DemoData {

    suspend fun seedIfEmpty(database: DistribosDatabase, commands: CommandService) {
        if (database.products().count() > 0) return

        val now = System.currentTimeMillis()
        val warehouseId = "demo-warehouse-0001"
        database.inventory().upsertWarehouse(
            WarehouseEntity(warehouseId, "MARKAZ", "Markaziy ombor", isActive = true)
        )

        // --- katalog (desktopdan kelgandek) -------------------------------

        val catalogue = listOf(
            Catalogue("COLA-1L", "Coca-Cola 1 L", 1_450_000L, minStock = "50", onHand = "120"),
            Catalogue("FANTA-1L", "Fanta 1 L", 1_400_000L, minStock = "50", onHand = "80"),
            Catalogue("SUV-05", "Ichimlik suvi 0.5 L", 300_000L, minStock = "100", onHand = "40"),
            Catalogue("CHOY-100", "Qora choy 100 g", 1_200_000L, minStock = "30", onHand = "15"),
            Catalogue("YOGH-1L", "Paxta yog'i 1 L", 2_400_000L, minStock = "25", onHand = "5"),
        )

        val productIds = catalogue.mapIndexed { index, item ->
            val id = "demo-product-%04d".format(index)
            database.products().upsert(
                ProductEntity(
                    id = id, sku = item.sku, barcode = null, name = item.name,
                    unit = "dona", wholesalePrice = item.price,
                    retailPrice = item.price * 12 / 10, agentPrice = item.price,
                    minStock = item.minStock, isActive = true, updatedAtMs = now,
                )
            )
            // Kirim harakati + qoldiq. Uchta mahsulotda qoldiq ataylab
            // minimaldan past — "kam qoldi" ogohlantirishi ko'rinsin.
            database.inventory().insertMovement(
                MovementEntity(
                    id = "demo-move-%04d".format(index), warehouseId = warehouseId,
                    productId = id, movementType = "RECEIPT", quantity = item.onHand,
                    unitCost = 0, referenceType = null, referenceId = null,
                    occurredAtMs = now, sourceEventId = null, note = null,
                )
            )
            database.inventory().upsertStock(
                StockEntity(warehouseId, id, item.onHand, "0", now)
            )
            id
        }

        // --- mijozlar (desktopdan kelgandek) ------------------------------

        val clients = listOf(
            Client("M-001", "Dilshod savdo do'koni", 15_000_000L),
            Client("M-002", "Nodira market", 8_000_000L),
            Client("M-003", "Chorsu ulgurji", 40_000_000L),
        )
        val customerIds = clients.mapIndexed { index, client ->
            val id = "demo-customer-%04d".format(index)
            database.customers().upsert(
                CustomerEntity(
                    id = id, code = client.code, name = client.name, kind = "COMPANY",
                    phone = "+998 9$index 123 45 67", address = null,
                    latitude = null, longitude = null, priceTier = "wholesale",
                    creditLimit = client.creditLimit, paymentTermDays = 14,
                    assignedAgentId = null, isActive = true, updatedAtMs = now,
                )
            )
            id
        }

        // --- agentning O'Z amallari (buyruq orqali, outbox'ga tushadi) ----

        val orders = listOf(
            Order(0, listOf(0 to "12", 2 to "24"), "B-00001"),
            Order(1, listOf(1 to "8", 3 to "4"), "B-00002"),
            Order(2, listOf(0 to "40", 4 to "2"), "B-00003"),
        )
        for ((index, order) in orders.withIndex()) {
            val orderId = "demo-order-%04d".format(index)
            commands.submit(
                CommandService.NewEvent(
                    eventType = "ORDER_CREATED",
                    aggregateType = "Order",
                    aggregateId = orderId,
                    payload = mapOf(
                        "order_id" to orderId,
                        "number" to order.number,
                        "customer_id" to customerIds[order.customerIndex],
                        "ordered_at_ms" to now,
                        "lines" to order.lines.mapIndexed { lineIndex, line ->
                            mapOf(
                                "line_id" to "$orderId-$lineIndex",
                                "product_id" to productIds[line.first],
                                "quantity" to line.second,
                                "unit_price" to catalogue[line.first].price,
                            )
                        },
                    ),
                )
            )
        }

        commands.submit(
            CommandService.NewEvent(
                eventType = "PAYMENT_RECORDED",
                aggregateType = "Payment",
                aggregateId = "demo-payment-0001",
                payload = mapOf(
                    "payment_id" to "demo-payment-0001",
                    "number" to "T-00001",
                    "direction" to "IN",
                    "amount" to 20_000_000L,
                    "customer_id" to customerIds[0],
                    "method" to "cash",
                    "occurred_at_ms" to now,
                ),
            )
        )
    }

    private data class Catalogue(
        val sku: String,
        val name: String,
        val price: Long,
        val minStock: String,
        val onHand: String,
    )

    private data class Client(val code: String, val name: String, val creditLimit: Long)

    private data class Order(
        val customerIndex: Int,
        val lines: List<Pair<Int, String>>,
        val number: String,
    )
}

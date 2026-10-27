import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:drift/drift.dart';

/// Standart kategoriyalar tartibi (kickoff Vazifa 3).
const List<CategoryKey> defaultCategoryKeys = [
  CategoryKey.rent,
  CategoryKey.credit,
  CategoryKey.groceries,
  CategoryKey.utilities,
  CategoryKey.phone,
  CategoryKey.fuel,
  CategoryKey.transport,
  CategoryKey.dailySmall,
  CategoryKey.children,
  CategoryKey.sadaqa,
  CategoryKey.other,
  CategoryKey.snacks,
  CategoryKey.cafe,
];

/// Standart toifa (SPEC 2B.2). Bola tarbiyasi = `kerak`. Sadaqa toifadan
/// tashqari (SPEC 2B.8: havas emas, «oqib ketish» hisobiga kirmaydi).
Necessity? defaultNecessityOf(CategoryKey key) => switch (key) {
  CategoryKey.rent ||
  CategoryKey.credit ||
  CategoryKey.groceries ||
  CategoryKey.utilities ||
  CategoryKey.transport => Necessity.zarur,
  CategoryKey.phone ||
  CategoryKey.fuel ||
  CategoryKey.dailySmall ||
  CategoryKey.children ||
  CategoryKey.other => Necessity.kerak,
  CategoryKey.snacks || CategoryKey.cafe => Necessity.havas,
  CategoryKey.sadaqa => null,
};

/// v6: mavjud standart kategoriyalarga toifa (foydalanuvchi o'zgartirmagan,
/// ya'ni `null` bo'lsa) va yangi standart kategoriyalar.
Future<void> upgradeCategoriesToV6(
  AppDatabase db,
  SyncMetaFactory metaFactory,
) async {
  for (final key in CategoryKey.values) {
    final n = defaultNecessityOf(key);
    if (n == null) continue;
    await (db.update(db.categories)..where(
          (t) => t.systemKey.equalsValue(key) & t.defaultNecessity.isNull(),
        ))
        .write(CategoriesCompanion(defaultNecessity: Value(n)));
  }
  // Migratsiya oraliq versiyada ishlaydi: joriy klass keyingi versiyalardagi
  // ustunlarni kutadi (masalan, v10 `budget_mode` NOT NULL) — faqat kerakli
  // ustunlar o'qiladi.
  final households = db.households;
  final ids = [
    for (final r in await (db.selectOnly(
      households,
    )..addColumns([households.id])).get())
      r.read(households.id)!,
  ];
  final cats = db.categories;
  for (final id in ids) {
    final existing = {
      for (final r
          in await (db.selectOnly(cats)
                ..addColumns([cats.systemKey])
                ..where(cats.householdId.equals(id)))
              .get())
        r.readWithConverter(cats.systemKey),
    };
    for (final (i, key) in defaultCategoryKeys.indexed) {
      if (existing.contains(key)) continue;
      await db
          .into(db.categories)
          .insert(_category(metaFactory.create(id), key, i));
    }
  }
}

/// Yangi baza: bitta uy xo'jaligi va standart kategoriyalar.
Future<void> seedDefaults(AppDatabase db, SyncMetaFactory metaFactory) async {
  final household = metaFactory.createHousehold();
  await db.batch((b) {
    b
      ..insert(
        db.households,
        HouseholdsCompanion.insert(
          id: household.id,
          householdId: household.householdId,
          createdAt: household.createdAt,
          updatedAt: household.updatedAt,
        ),
      )
      ..insertAll(db.categories, [
        for (final (i, key) in defaultCategoryKeys.indexed)
          _category(metaFactory.create(household.id), key, i),
      ]);
  });
}

CategoriesCompanion _category(SyncMeta meta, CategoryKey key, int order) =>
    CategoriesCompanion.insert(
      id: meta.id,
      householdId: meta.householdId,
      createdAt: meta.createdAt,
      updatedAt: meta.updatedAt,
      systemKey: Value(key),
      defaultNecessity: Value(defaultNecessityOf(key)),
      sortOrder: Value(order),
    );

/// v9: mavjud qarzlar uchun to'lov rejasi (SPEC 2D.5: rejasiz qarz yo'q) —
/// bitta qator: qoldiq muddat sanasida (yo'q bo'lsa — yaratilganidan 30 kun
/// keyin).
Future<void> backfillDebtInstallmentsV9(
  AppDatabase db,
  SyncMetaFactory metaFactory,
) async {
  final t = db.debts;
  final rows =
      await (db.selectOnly(t)..addColumns([
            t.id,
            t.householdId,
            t.remainingMinor,
            t.currency,
            t.dueDate,
            t.createdAt,
            t.deletedAt,
          ]))
          .get();
  for (final r in rows) {
    if (r.read(t.deletedAt) != null || r.read(t.remainingMinor)! <= 0) {
      continue;
    }
    final d = (
      id: r.read(t.id)!,
      householdId: r.read(t.householdId)!,
      remainingMinor: r.read(t.remainingMinor)!,
      currency: r.readWithConverter(t.currency)!,
      dueDate: r.readWithConverter(t.dueDate),
      createdAt: r.read(t.createdAt)!,
    );
    final meta = metaFactory.create(d.householdId);
    await db
        .into(db.debtInstallments)
        .insert(
          DebtInstallmentsCompanion.insert(
            id: meta.id,
            householdId: meta.householdId,
            createdAt: meta.createdAt,
            updatedAt: meta.updatedAt,
            debtId: d.id,
            dueOn:
                d.dueDate ?? Tashkent.dateOf(d.createdAt.toUtc()).plusDays(30),
            amountMinor: d.remainingMinor,
            currency: d.currency,
          ),
        );
  }
}

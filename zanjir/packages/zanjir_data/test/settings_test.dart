import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_data/zanjir_data.dart';

import 'support/harness.dart';

void main() {
  late ZanjirDatabase db;
  late Org org;
  setUp(() async {
    db = memoryDb();
    org = await Org.create(db, 'A');
  });
  tearDown(() => db.close());

  test('standart: k_corr 1,0, zaxira 0, faol to\'plam yo\'q', () async {
    final s = await org.repos.settings.current();
    expect((s.kCorr, s.marginPct, s.activeNormSetVersion), (1.0, 0.0, null));
  });

  test('LEAD o\'zgartiradi — auditga yoziladi va baholashga ta\'sir qiladi', () async {
    final site = await SmallSite.create(org);
    final updated = await org.repos.settings.update(byUserId: org.user.id, kCorr: 0.8, activeNormSetVersion: '0.1.0');
    expect((updated.kCorr, updated.marginPct, updated.activeNormSetVersion), (0.8, 0.0, '0.1.0'));
    final again = await org.repos.settings.update(byUserId: org.user.id, marginPct: 5);
    expect((again.kCorr, again.marginPct), (0.8, 5.0));
    expect((await org.repos.settings.current()).marginPct, 5);
    final changes = (await org.repos.audit.events()).where((e) => e.eventType == 'SETTINGS_CHANGED');
    expect(changes, hasLength(2));

    final session = await org.repos.sessions.start(
      siteId: site.site.id,
      kind: SessionKind.davriy,
      engineerId: org.user.id,
    );
    final m = await org.repos.measurements.record(
      sessionId: session.id,
      nodeId: site.sock1.id,
      type: MeasurementType.loopImpedance,
      instrumentId: site.instrument.id,
      values: {'pair': 'L1-PE', 'zs_ohm': 1.2},
      enteredVia: EnteredVia.manual,
      normSetVersion: '0.1.0',
    );
    // Zs_max = 0,8 · 220 / 160 · 0,95 = 1,045 Ω.
    expect(m.verdict, Verdict.fail);
    expect((m.evalDetail['k_corr'], m.evalDetail['margin_pct']), (0.8, 5.0));
  });

  test('ENGINEER o\'zgartira olmaydi; noto\'g\'ri qiymatlar rad etiladi', () async {
    final eng = await org.repos.users.create(fullName: 'E', phone: '+998', role: 'ENGINEER');
    await expectLater(
      org.repos.settings.update(byUserId: eng.id, kCorr: 0.9),
      throwsA(isA<DataRuleException>().having((e) => e.code, 'code', 'forbidden_role')),
    );
    for (final (k, m, code) in [
      (0.0, null, 'invalid_k_corr'),
      (1.1, null, 'invalid_k_corr'),
      (null, -1.0, 'invalid_margin'),
      (null, 51.0, 'invalid_margin'),
    ]) {
      await expectLater(
        org.repos.settings.update(byUserId: org.user.id, kCorr: k, marginPct: m),
        throwsA(isA<DataRuleException>().having((e) => e.code, 'code', code)),
      );
    }
    await expectLater(
      org.repos.settings.update(byUserId: org.user.id, activeNormSetVersion: '9.9.9'),
      throwsA(isA<NotFoundException>()),
    );
    await expectLater(SettingsRepository(org.ctx).update(byUserId: org.user.id, kCorr: 0.9), throwsStateError);
    expect((await org.repos.settings.current()).kCorr, 1.0, reason: 'muvaffaqiyatsiz urinishlar saqlanmaydi');
  });

  test('laboratoriya rekvizitlari', () async {
    expect((await org.repos.settings.organization()).name, 'A');
    final o = await org.repos.settings.updateLab(
      byUserId: org.user.id,
      name: 'Elektrolab',
      licenseNo: 'L-1',
      licenseValidUntil: DateTime.utc(2028),
    );
    expect((o.name, o.licenseNo, o.rev), ('Elektrolab', 'L-1', 2));
    expect((await org.repos.audit.events()).last.eventType, 'LAB_UPDATED');
    final eng = await org.repos.users.create(fullName: 'E', phone: '+998', role: 'ENGINEER');
    await expectLater(org.repos.settings.updateLab(byUserId: eng.id, name: 'X'), throwsA(isA<DataRuleException>()));
    await expectLater(SettingsRepository(org.ctx).updateLab(byUserId: org.user.id, name: 'X'), throwsStateError);
    await expectLater(
      SettingsRepository(DataContext(db: db, orgId: 'yoq')).organization(),
      throwsA(isA<NotFoundException>()),
    );
  });

  test('LocalPrefRepository', () async {
    final p = LocalPrefRepository(db);
    expect(await p.get(LocalPrefRepository.locale), isNull);
    await p.set(LocalPrefRepository.locale, 'ru');
    await p.set(LocalPrefRepository.locale, 'uz');
    expect(await p.get(LocalPrefRepository.locale), 'uz');
    await p.remove(LocalPrefRepository.locale);
    expect(await p.get(LocalPrefRepository.locale), isNull);
  });
}

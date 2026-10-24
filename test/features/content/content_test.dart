import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/content/data/drift_content_repositories.dart';
import 'package:baraka_daftari/features/content/domain/chapter_unlock.dart';
import 'package:baraka_daftari/features/content/domain/content.dart';
import 'package:baraka_daftari/features/content/domain/content_parser.dart';
import 'package:baraka_daftari/features/content/domain/content_service.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';

Map<String, dynamic> chapterJson(
  int order, {
  String? id,
  String status = 'APPROVED',
}) {
  final cid = id ?? 'ch${order.toString().padLeft(2, '0')}';
  return {
    'id': cid,
    'order': order,
    'title': {'uz': 'Bob $order', 'ru': 'Глава $order'},
    'blocks': [
      {
        'type': 'paragraph',
        'text': {'uz': 'Matn'},
      },
      {
        'type': 'religious',
        'text': {'uz': 'Diniy matn'},
        'source': {'uz': 'Manba'},
        'religiousReviewStatus': status,
      },
    ],
    'law': {
      'number': order,
      'text': {'uz': 'Qonun $order'},
    },
    'weeklyTasks': [
      {
        'id': '$cid.t1',
        'text': {'uz': 'V1'},
        'autoComplete': 'VAULT_OPENED',
      },
      {
        'id': '$cid.t2',
        'text': {'uz': 'V2'},
        'autoComplete': 'INCOME_SHARED',
      },
      {
        'id': '$cid.t3',
        'text': {'uz': 'V3'},
        'autoComplete': 'AUDIT_COMPLETED',
      },
    ],
  };
}

String doc(List<Object?> chapters, {int version = 1}) =>
    jsonEncode({'schemaVersion': version, 'chapters': chapters});

void main() {
  group('ContentParser — sxema validatsiyasi', () {
    test('ilovadagi haqiqiy kontent sxemaga toʻliq mos', () {
      final r = ContentParser.parse(
        File('assets/content/chapters.json').readAsStringSync(),
      );
      expect(r.errors, isEmpty);
      expect(r.chapters.map((c) => c.id), [
        'ch01',
        'ch02',
        'ch03',
        'ch04',
        'ch05',
        'ch06',
        'ch07',
      ]);
      expect(r.chapters.map((c) => c.law.number), [1, 2, 3, 4, 5, 6, 7]);
      final c = r.chapters.first;
      expect(c.weeklyTasks.map((t) => t.trigger), [
        TaskTrigger.vaultOpened,
        TaskTrigger.incomeShared,
        TaskTrigger.auditCompleted,
      ]);
      // Har bobda kamida 2 ta vazifani hozir ham bajarib boʻladi (qoʻlda
      // yoki trigger bilan) — aks holda odat qoidasi keyingi bobni ochmaydi.
      for (final ch in r.chapters) {
        expect(ch.weeklyTasks, hasLength(3), reason: ch.id);
      }
      // Oʻzbekcha matnlarda ASCII apostrof yoʻq (oʻ, gʻ — U+02BB; tutuq —
      // U+02BC).
      final raw = File('assets/content/chapters.json').readAsStringSync();
      expect(raw, isNot(contains("'")));
      // Bob matni va maslahat — oʻz matnimiz (placeholder emas).
      final paragraph = c.blocks.whereType<ParagraphBlock>().first;
      expect(paragraph.text.of('uz'), isNot(contains('Placeholder')));
      expect(c.blocks.whereType<QuoteBlock>(), hasLength(1));
      // Diniy blok tasdiqlanmagan.
      expect(
        c.blocks.whereType<ReligiousBlock>().single.status,
        ReligiousReviewStatus.pending,
      );
    });

    test('docs/content_schema.json — haqiqiy JSON Schema', () {
      final schema =
          jsonDecode(File('docs/content_schema.json').readAsStringSync())
              as Map<String, dynamic>;
      expect(schema[r'$schema'], contains('json-schema.org'));
      // Sxemadagi trigger kodlari Dart reyestri bilan bir xil.
      final raw = File('docs/content_schema.json').readAsStringSync();
      final codes = RegExp('"([A-Z_]{4,})"')
          .allMatches(
            raw.substring(
              raw.indexOf('autoComplete'),
              raw.indexOf(']', raw.indexOf('autoComplete')),
            ),
          )
          .map((m) => m[1])
          .toSet();
      expect(codes, TaskTrigger.values.map((t) => t.code).toSet());
    });

    test('TaskTrigger kodlari takrorlanmaydi va qayta oʻqiladi', () {
      for (final t in TaskTrigger.values) {
        expect(TaskTrigger.fromCode(t.code), t);
      }
      expect(TaskTrigger.fromCode('NO_SUCH'), isNull);
      final bad = chapterJson(1);
      ((bad['weeklyTasks'] as List).first
              as Map<String, dynamic>)['autoComplete'] =
          'NO_SUCH';
      expect(
        ContentParser.parse(doc([bad])).errors.single,
        contains('NO_SUCH'),
      );
    });

    test('tartib boʻyicha saralanadi, ru boʻlmasa uz', () {
      final r = ContentParser.parse(doc([chapterJson(2), chapterJson(1)]));
      expect(r.chapters.map((c) => c.order), [1, 2]);
      expect(r.chapters.first.law.text.of('ru'), 'Qonun 1');
    });

    test('buzuq JSON ilovani yiqitmaydi', () {
      for (final bad in ['', '{', 'null', '[]', '"x"', '{"chapters": 5}']) {
        final r = ContentParser.parse(bad);
        expect(r.chapters, isEmpty, reason: bad);
        expect(r.errors, isNotEmpty, reason: bad);
      }
      expect(
        ContentParser.parse(doc([chapterJson(1)], version: 2)).errors.single,
        contains('schemaVersion'),
      );
    });

    test('buzuq bob oʻtkazib yuboriladi, qolganlari ishlaydi', () {
      Map<String, dynamic> broken(void Function(Map<String, dynamic>) f) {
        final c = chapterJson(5, id: 'bad');
        f(c);
        return c;
      }

      final cases = <String, Map<String, dynamic>>{
        'uz yoʻq': broken((c) => c['title'] = {'ru': 'x'}),
        'boʻsh matn': broken((c) => c['title'] = {'uz': '  '}),
        'nomaʼlum til': broken((c) => c['title'] = {'uz': 'a', 'en': 'b'}),
        '2 ta vazifa': broken(
          (c) => (c['weeklyTasks'] as List).removeLast(),
        ),
        'notoʻgʻri trigger': broken(
          (c) =>
              ((c['weeklyTasks'] as List).first as Map)['autoComplete'] = 'X',
        ),
        'status yoʻq': broken(
          (c) => ((c['blocks'] as List)[1] as Map).remove(
            'religiousReviewStatus',
          ),
        ),
        'manba yoʻq': broken(
          (c) => ((c['blocks'] as List)[1] as Map).remove('source'),
        ),
        'nomaʼlum blok': broken(
          (c) => (c['blocks'] as List).add({'type': 'video'}),
        ),
        'http audio': broken((c) => c['audioUrl'] = 'http://x.uz/a.mp3'),
        'order matn': broken((c) => c['order'] = '1'),
        'id katta harf': broken((c) => c['id'] = 'Ch01'),
        'boʻsh bloklar': broken((c) => c['blocks'] = <Object>[]),
      };
      for (final MapEntry(key: name, value: bad) in cases.entries) {
        final r = ContentParser.parse(doc([chapterJson(1), bad]));
        expect(r.chapters.map((c) => c.id), ['ch01'], reason: name);
        expect(r.errors, hasLength(1), reason: name);
      }
    });

    test('takrorlangan id / order / vazifa id rad etiladi', () {
      final r = ContentParser.parse(
        doc([chapterJson(1), chapterJson(1, id: 'ch02'), chapterJson(3)]),
      );
      expect(r.chapters.map((c) => c.id), ['ch01', 'ch03']);
      expect(r.errors.single, contains('order'));
    });

    test('tasodifiy buzilishlar hech qachon istisno tashlamaydi', () {
      final source = File('assets/content/chapters.json').readAsStringSync();
      final r = Random(7);
      for (var i = 0; i < 500; i++) {
        final chars = source.split('');
        for (var k = 0; k < 1 + r.nextInt(5); k++) {
          final at = r.nextInt(chars.length);
          chars[at] = String.fromCharCode(32 + r.nextInt(90));
        }
        expect(() => ContentParser.parse(chars.join()), returnsNormally);
      }
    });
  });

  group('diniy bloklar — PENDING releaseʼda koʻrinmaydi', () {
    final c = ContentParser.parse(
      doc([chapterJson(1, status: 'PENDING')]),
    ).chapters.single;
    final approved = ContentParser.parse(
      doc([chapterJson(1)]),
    ).chapters.single;

    test('release (showPending: false) — PENDING yashiriladi', () {
      final blocks = c.visibleBlocks(showPendingReligious: false);
      expect(blocks.whereType<ReligiousBlock>(), isEmpty);
      expect(blocks.whereType<ParagraphBlock>(), hasLength(1));
    });

    test('debug — tekshiruv uchun koʻrinadi', () {
      expect(
        c.visibleBlocks(showPendingReligious: true).whereType<ReligiousBlock>(),
        hasLength(1),
      );
    });

    test('APPROVED — har doim koʻrinadi', () {
      expect(
        approved
            .visibleBlocks(showPendingReligious: false)
            .whereType<ReligiousBlock>(),
        hasLength(1),
      );
    });
  });

  group('ChapterUnlockPolicy — vaqt boʻyicha (har juma)', () {
    const policy = TimeBasedUnlockPolicy();
    final chapters = ContentParser.parse(
      doc([chapterJson(1), chapterJson(2), chapterJson(3)]),
    ).chapters;
    UnlockContext ctx(LocalDate today) => UnlockContext(
      // Seshanba boshlagan.
      programStart: LocalDate(2026, 10, 6),
      today: today,
      calendar: const BudgetCalendar(),
    );

    test('1-bob darhol, 2-bob keyingi juma, 3-bob undan keyingi', () {
      final r = policy.evaluate(chapters, ctx(LocalDate(2026, 10, 6)));
      expect(r.map((u) => u.date), [
        LocalDate(2026, 10, 6),
        LocalDate(2026, 10, 9),
        LocalDate(2026, 10, 16),
      ]);
    });

    test('payshanba — 2-bob yopiq; juma — ochiq', () {
      final r = policy.evaluate(chapters, ctx(LocalDate(2026, 10, 6)));
      expect(r[1].isUnlockedOn(LocalDate(2026, 10, 8)), isFalse);
      expect(r[1].isUnlockedOn(LocalDate(2026, 10, 9)), isTrue);
      expect(r[2].isUnlockedOn(LocalDate(2026, 10, 9)), isFalse);
    });
  });

  group('HabitUnlockPolicy — odat boʻyicha (2 vazifa + 7 kun)', () {
    const policy = HabitUnlockPolicy();
    final chapters = ContentParser.parse(
      doc([chapterJson(1), chapterJson(2), chapterJson(3)]),
    ).chapters;
    final start = LocalDate(2026, 10, 6);
    List<ChapterUnlock> run(Map<String, LocalDate> done) => policy.evaluate(
      chapters,
      UnlockContext(
        programStart: start,
        today: start,
        calendar: const BudgetCalendar(),
        taskFirstCompleted: done,
      ),
    );

    test('vazifasiz vaqtning oʻzi bob ochmaydi', () {
      final r = run(const {});
      expect(r[0].date, start);
      expect(r[1].date, isNull);
      expect(r[1].tasksRemaining, 2);
      expect(r[1].notBefore, LocalDate(2026, 10, 13));
      // 3-bob: oldingisi ochilmagan — kun sharti ham nomaʼlum.
      expect(r[2].date, isNull);
      expect(r[2].tasksRemaining, 2);
      expect(r[2].notBefore, isNull);
    });

    test('bitta vazifa yetmaydi', () {
      final r = run({'ch01.t1': LocalDate(2026, 10, 7)});
      expect(r[1].date, isNull);
      expect(r[1].tasksRemaining, 1);
    });

    test('2 vazifa tez bajarilsa — 7 kun toʻlganda ochiladi', () {
      final r = run({
        'ch01.t1': LocalDate(2026, 10, 7),
        'ch01.t3': LocalDate(2026, 10, 8),
      });
      expect(r[1].date, LocalDate(2026, 10, 13));
      expect(r[1].tasksRemaining, 0);
      expect(r[1].isUnlockedOn(LocalDate(2026, 10, 12)), isFalse);
      expect(r[1].isUnlockedOn(LocalDate(2026, 10, 13)), isTrue);
    });

    test(
      '2-vazifa kech bajarilsa — oʻsha kuni ochiladi; zanjir davom etadi',
      () {
        final r = run({
          'ch01.t1': LocalDate(2026, 10, 7),
          'ch01.t2': LocalDate(2026, 10, 20),
          'ch02.t1': LocalDate(2026, 10, 21),
          'ch02.t2': LocalDate(2026, 10, 22),
        });
        expect(r[1].date, LocalDate(2026, 10, 20));
        expect(r[2].date, LocalDate(2026, 10, 27));
      },
    );

    test('boshqa bob vazifalari hisobga olinmaydi', () {
      final r = run({
        'ch02.t1': LocalDate(2026, 10, 7),
        'ch02.t2': LocalDate(2026, 10, 7),
      });
      expect(r[1].date, isNull);
    });

    test('shart sozlanadi', () {
      final r = const HabitUnlockPolicy(requiredTasks: 1, minDays: 0).evaluate(
        chapters,
        UnlockContext(
          programStart: start,
          today: start,
          calendar: const BudgetCalendar(),
          taskFirstCompleted: {'ch01.t2': start},
        ),
      );
      expect(r[1].date, start);
    });
  });

  group('ContentService', () {
    late TestDb t;
    late ContentService service;
    var json = doc([chapterJson(1), chapterJson(2)]);

    setUp(() {
      t = TestDb.open();
      json = doc([chapterJson(1), chapterJson(2)]);
      service = ContentService(
        loadJson: () async => json,
        households: DriftHouseholdRepository(t.db, t.clock),
        pages: DriftDaftarPageRepository(t.db, t.clock),
        completions: DriftTaskCompletionRepository(t.db, t.clock),
        metaFactory: t.meta,
        clock: t.clock,
      );
    });

    test('joriy bob odat bilan almashadi: 2 vazifa + 7 kun', () async {
      // FakeClock — juma 2026-10-09; uy xoʻjaligi shu kuni yaratilgan.
      expect((await service.currentChapter())!.id, 'ch01');
      expect(await service.chapter('ch02'), isNull, reason: 'yopiq');
      t.clock.advance(const Duration(days: 7));
      expect(
        (await service.currentChapter())!.id,
        'ch01',
        reason: 'vaqtning oʻzi yetmaydi',
      );
      final locked = (await service.chapters())[1];
      expect(locked.tasksRemaining, 2);
      expect(locked.unlockDate, isNull);

      await service.recordEvent(TaskTrigger.vaultOpened);
      await service.setTaskDone('ch01.t3', done: true);
      expect((await service.currentChapter())!.id, 'ch02');
    });

    test('vazifa belgisi olib tashlansa ham ochilgan bob yopilmaydi', () async {
      await service.setTaskDone('ch01.t1', done: true);
      await service.setTaskDone('ch01.t2', done: true);
      t.clock.advance(const Duration(days: 7));
      expect((await service.currentChapter())!.id, 'ch02');
      // Oʻtgan haftaning belgilari endi koʻrinmaydi, lekin tarix saqlanadi.
      t.clock.advance(const Duration(days: -7));
      await service.setTaskDone('ch01.t1', done: false);
      t.clock.advance(const Duration(days: 7));
      expect((await service.currentChapter())!.id, 'ch02');
    });

    test(
      'hodisa mos vazifani bir marta belgilaydi, qoʻlda bekor qilish',
      () async {
        expect(await service.recordEvent(TaskTrigger.vaultOpened), ['ch01.t1']);
        expect(await service.recordEvent(TaskTrigger.vaultOpened), isEmpty);
        expect((await service.thisWeek())!.done, {'ch01.t1'});
        await service.setTaskDone('ch01.t2', done: true);
        await service.setTaskDone('ch01.t1', done: false);
        expect((await service.thisWeek())!.done, {'ch01.t2'});
      },
    );

    test('yangi haftada vazifalar yangidan', () async {
      await service.recordEvent(TaskTrigger.auditCompleted);
      await service.recordEvent(TaskTrigger.incomeShared);
      t.clock.advance(const Duration(days: 7));
      final week = (await service.thisWeek())!;
      expect(week.done, isEmpty);
      expect(week.chapter.id, 'ch02');
    });

    test('«Daftar sahifasi» saqlanadi va yangilanadi', () async {
      final ch = (await service.currentChapter())!;
      final first = await service.saveDaftarPage(ch, 'Avval oʻzimga');
      final second = await service.saveDaftarPage(
        ch,
        'Avval oʻzimga toʻlayman',
      );
      expect(second.meta.id, first.meta.id);
      expect(
        (await service.daftarPage('ch01'))!.body,
        'Avval oʻzimga toʻlayman',
      );
      expect(second.lawNumber, 1);
    });

    test('kontent oʻqilmasa — boʻsh natija, istisno yoʻq', () async {
      final broken = ContentService(
        loadJson: () async => throw const FileSystemException('yoʻq'),
        households: DriftHouseholdRepository(t.db, t.clock),
        pages: DriftDaftarPageRepository(t.db, t.clock),
        completions: DriftTaskCompletionRepository(t.db, t.clock),
        metaFactory: t.meta,
        clock: t.clock,
      );
      expect(await broken.chapters(), isEmpty);
      expect(await broken.thisWeek(), isNull);
      expect(await broken.recordEvent(TaskTrigger.vaultOpened), isEmpty);
    });
  });
}

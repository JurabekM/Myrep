import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/household/domain/household_service.dart';
import 'package:baraka_daftari/features/household/domain/member_pin_service.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';
import '../../helpers/fakes.dart';

void main() {
  late TestDb t;
  late InMemorySecureBlobStore store;
  late PinService pins;
  late DriftMemberRepository repo;
  late MemberPinService service;
  late Member wife;
  late Member son;

  setUp(() async {
    t = TestDb.open();
    store = InMemorySecureBlobStore();
    pins = PinService(
      store: store,
      hasher: ReferencePinHasher(),
      clock: t.clock,
      iterations: 1000,
    );
    repo = DriftMemberRepository(t.db, t.clock);
    service = MemberPinService(pins: pins, members: repo);
    final hh = HouseholdService(
      households: DriftHouseholdRepository(t.db, t.clock),
      members: repo,
      metaFactory: t.meta,
    );
    wife = await hh.addMember('Zuhra', MemberRole.adult);
    son = await hh.addMember('Ali', MemberRole.child);
  });

  test('PIN hosila sifatida DB ga yoziladi va qayta oʻqiladi', () async {
    expect(wife.hasPersonalPin, isFalse);
    await service.setPin(wife, '482915');

    final row = await (t.db.select(
      t.db.members,
    )..where((m) => m.id.equals(wife.meta.id))).getSingle();
    expect(row.pinRecord, isNotNull);
    expect(row.pinRecord, isNot(contains('482915')));

    final stored = await repo.findById(wife.meta.id);
    expect(stored!.hasPersonalPin, isTrue);
    expect(await service.verify(stored, '482915'), isA<PinAccepted>());
    expect(await service.verify(stored, '111222'), isA<PinRejected>());
  });

  test('PINsiz aʼzo tasdiqni PIN soʻramasdan oladi', () async {
    expect(await service.verify(son, ''), isA<PinAccepted>());
  });

  test(
    'lockout har aʼzoda alohida, asosiy PIN hisobiga taʼsir qilmaydi',
    () async {
      wife = await service.setPin(wife, '482915');
      son = await service.setPin(son, '730164');

      PinCheck last = const PinAccepted();
      for (var i = 0; i < 6; i++) {
        last = await service.verify(wife, '000000');
      }
      expect(last, isA<PinLockedOut>());
      // Toʻgʻri PIN ham kutish tugaguncha qabul qilinmaydi.
      expect(await service.verify(wife, '482915'), isA<PinLockedOut>());

      expect(await service.verify(son, '730164'), isA<PinAccepted>());
      expect(await pins.activeLockoutUntil(), isNull);

      t.clock.advance(const Duration(hours: 2));
      expect(await service.verify(wife, '482915'), isA<PinAccepted>());
    },
  );

  test(
    'PIN almashtirish lockoutni tozalaydi, oʻchirish PINni olib tashlaydi',
    () async {
      wife = await service.setPin(wife, '482915');
      for (var i = 0; i < 6; i++) {
        await service.verify(wife, '000000');
      }
      wife = await service.setPin(wife, '593017');
      expect(await service.verify(wife, '593017'), isA<PinAccepted>());

      wife = await service.clearPin(wife);
      expect((await repo.findById(wife.meta.id))!.hasPersonalPin, isFalse);
    },
  );

  test('notoʻgʻri formatdagi PIN rad etiladi', () async {
    await expectLater(service.setPin(wife, '12'), throwsArgumentError);
  });
}

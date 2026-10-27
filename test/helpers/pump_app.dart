import 'package:baraka_daftari/app/app.dart';
import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/database_provider.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/ids/uuid_v7.dart';
import 'package:baraka_daftari/core/notifications/reminder_api.pigeon.dart';
import 'package:baraka_daftari/core/security/integrity/integrity_service.dart';
import 'package:baraka_daftari/core/security/pin/pin_hasher.dart';
import 'package:baraka_daftari/core/security/pin/pin_service.dart';
import 'package:baraka_daftari/core/security/secure_blob_store.dart';
import 'package:baraka_daftari/core/security/security_bridge.dart';
import 'package:baraka_daftari/core/security/security_settings.dart';
import 'package:baraka_daftari/core/time/clock.dart';
import 'package:baraka_daftari/core/widget/widget_bridge.dart';
import 'package:baraka_daftari/features/obligations/data/obligation_providers.dart';
import 'package:drift/drift.dart' show driftRuntimeOptions;
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'fakes.dart';

class MockSecurityApi extends Mock implements SecurityApi {}

class MockReminderApi extends Mock implements ReminderApi {}

MockReminderApi stubbedReminderApi({bool enabled = true}) {
  final api = MockReminderApi();
  when(() => api.sync(any(), any())).thenAnswer((_) async {});
  when(api.areNotificationsEnabled).thenAnswer((_) async => enabled);
  when(api.requestNotificationPermission).thenAnswer((_) async {});
  when(() => api.scheduleWeekly(any(), any(), any())).thenAnswer((_) async {});
  when(() => api.syncTreats(any(), any())).thenAnswer((_) async {});
  when(
    () => api.scheduleAgreementRenewal(
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
      any(),
    ),
  ).thenAnswer((_) async {});
  when(() => api.cancelAgreementRenewal(any())).thenAnswer((_) async {});
  when(
    () => api.scheduleIncomeReminder(any(), any(), any(), any(), any()),
  ).thenAnswer((_) async {});
  return api;
}

class MockWidgetApi extends Mock implements WidgetApi {}

/// Vidjet ko'prigi; [pending] — vidjetda bosilgan yozuvlar (bir marta
/// qaytariladi, keyin navbat bo'sh).
MockWidgetApi stubbedWidgetApi({
  List<PendingWidgetExpense> pending = const [],
}) {
  final api = MockWidgetApi();
  var queue = [...pending];
  when(() => api.setTemplates(any(), any())).thenAnswer((_) async {});
  when(() => api.setVisibleUntil(any())).thenAnswer((_) async {});
  when(api.takePending).thenAnswer((_) async {
    final out = queue;
    queue = [];
    return out;
  });
  return api;
}

const testPin = '258036';

IntegritySignals cleanSignals() => IntegritySignals(
  isRooted: false,
  isEmulator: false,
  isDebuggerAttached: false,
  isDebuggableBuild: true,
  signatureSha256: 'AB',
);

/// Native qatlamning standart (sogʻlom qurilma) javoblari.
MockSecurityApi stubbedSecurityApi({
  BiometricAvailability biometric = BiometricAvailability.unavailable,
  BiometricOutcome biometricOutcome = BiometricOutcome.cancelled,
  IntegritySignals? signals,
}) {
  final api = MockSecurityApi();
  when(
    api.ping,
  ).thenAnswer((_) async => NativeInfo(apiVersion: 2, androidSdkInt: 34));
  when(
    () => api.setSecureFlag(enabled: any(named: 'enabled')),
  ).thenAnswer((_) async {});
  when(api.getBiometricAvailability).thenAnswer((_) async => biometric);
  when(
    () => api.authenticate(any(), any(), any()),
  ).thenAnswer((_) async => biometricOutcome);
  when(
    api.getIntegritySignals,
  ).thenAnswer((_) async => signals ?? cleanSignals());
  return api;
}

class TestEnv {
  TestEnv({
    required this.api,
    required this.store,
    required this.clock,
    required this.hasher,
    required this.container,
    required this.db,
    required this.reminders,
    required this.widget,
  });

  final MockSecurityApi api;
  final InMemorySecureBlobStore store;
  final FakeClock clock;
  final ReferencePinHasher hasher;
  final ProviderContainer container;

  /// In-memory Drift bazasi (shifrlash hostʼda yoʻq — u alohida sinaladi).
  final AppDatabase db;
  final MockReminderApi reminders;
  final MockWidgetApi widget;
}

/// Telefon oʻlchamidagi test oynasi (standart 800x600 telefon emas).
void usePhoneViewport(WidgetTester tester) {
  tester.view
    ..physicalSize = const Size(1080, 2340)
    ..devicePixelRatio = 2.75;
  addTearDown(tester.view.reset);
}

/// Butun ilovani soxta native qatlam bilan ishga tushiradi.
///
/// [pinSet] — PIN oldindan oʻrnatilgan; [unlock] — qulf ekranida PIN
/// kiritilib, bosh sahifaga oʻtiladi; [onboarded] — onboarding tugagan
/// (`false` — yangi oʻrnatish, `/onboarding` koʻrinadi).
Future<TestEnv> pumpBarakaApp(
  WidgetTester tester, {
  MockSecurityApi? securityApi,
  MockReminderApi? reminderApi,
  MockWidgetApi? widgetApi,
  List<Override> extraOverrides = const [],
  bool pinSet = true,
  bool unlock = true,
  bool onboarded = true,
  SecuritySettings? settings,
  InMemorySecureBlobStore? store,
  FakeClock? clock,
}) async {
  usePhoneViewport(tester);
  final api = securityApi ?? stubbedSecurityApi();
  final blobs = store ?? InMemorySecureBlobStore();
  final fakeClock = clock ?? FakeClock();
  final hasher = ReferencePinHasher();
  registerFallbackValue(<ObligationReminder>[]);
  registerFallbackValue(<TreatReminder>[]);
  registerFallbackValue(IncomeReminderKind.daily);
  registerFallbackValue(<WidgetTemplate>[]);
  registerFallbackValue(WidgetTexts(title: '', locked: '', empty: ''));
  final widget = widgetApi ?? stubbedWidgetApi();
  final reminders = reminderApi ?? stubbedReminderApi();
  driftRuntimeOptions.dontWarnAboutMultipleDatabases = true;
  final db = AppDatabase(
    NativeDatabase.memory(),
    metaFactory: SyncMetaFactory(UuidV7Generator(clock: fakeClock), fakeClock),
  );
  addTearDown(db.close);
  if (onboarded) {
    // Mavjud testlar onboarding'dan o'tgan foydalanuvchi bilan ishlaydi.
    await db.customStatement(
      'UPDATE households SET onboarded_at = created_at',
    );
  }

  if (pinSet && !blobs.blobs.containsKey(PinService.recordBlob)) {
    await PinService(
      store: blobs,
      hasher: hasher,
      clock: fakeClock,
    ).setPin(testPin);
  }
  if (settings != null) {
    await SecuritySettingsRepository(blobs).save(settings);
  }

  final container = ProviderContainer(
    overrides: [
      securityApiProvider.overrideWithValue(api),
      secureBlobStoreProvider.overrideWithValue(blobs),
      pinHasherProvider.overrideWithValue(hasher),
      clockProvider.overrideWithValue(fakeClock),
      integrityLogProvider.overrideWithValue(RecordingIntegrityLog(fakeClock)),
      appDatabaseProvider.overrideWith((ref) async => db),
      reminderApiProvider.overrideWithValue(reminders),
      widgetApiProvider.overrideWithValue(widget),
      ...extraOverrides,
    ],
  );
  addTearDown(container.dispose);
  await tester.pumpWidget(
    UncontrolledProviderScope(container: container, child: const BarakaApp()),
  );
  await tester.pumpAndSettle();

  final env = TestEnv(
    api: api,
    store: blobs,
    clock: fakeClock,
    hasher: hasher,
    container: container,
    db: db,
    reminders: reminders,
    widget: widget,
  );
  if (pinSet && unlock) {
    await enterPin(tester, testPin);
    await tester.pumpAndSettle();
  }
  return env;
}

Future<void> enterPin(WidgetTester tester, String pin) async {
  for (final digit in pin.split('')) {
    await tester.tap(find.byKey(Key('pin-key-$digit')));
    await tester.pump();
  }
  await tester.pump();
}

/// Ilovani fonga yuborish va qaytarish (haqiqiy ketma-ketlik bilan).
void sendToBackground(WidgetTester tester) {
  for (final s in [
    AppLifecycleState.inactive,
    AppLifecycleState.hidden,
    AppLifecycleState.paused,
  ]) {
    tester.binding.handleAppLifecycleStateChanged(s);
  }
}

void bringToForeground(WidgetTester tester) {
  for (final s in [
    AppLifecycleState.hidden,
    AppLifecycleState.inactive,
    AppLifecycleState.resumed,
  ]) {
    tester.binding.handleAppLifecycleStateChanged(s);
  }
}

/// Bosh sahifadagi boʻlimni bosish: avval koʻrinadigan joyga aylantiriladi
/// (pastdagi tugmalar ostida qolmasin).
Future<void> tapNav(WidgetTester tester, String route) =>
    tapVisible(tester, find.byKey(Key('nav-$route')));

/// Roʻyxatdagi elementni koʻrinadigan joyga aylantirib bosish.
Future<void> tapVisible(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(
    f,
    300,
    scrollable: find.byType(Scrollable).first,
  );
  await Scrollable.ensureVisible(tester.element(f), alignment: 0.3);
  await tester.pumpAndSettle();
  await tester.tap(f);
}

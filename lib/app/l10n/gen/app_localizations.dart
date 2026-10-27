import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_ru.dart';
import 'app_localizations_uz.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'gen/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('ru'),
    Locale('uz'),
  ];

  /// Ilova nomi
  ///
  /// In uz, this message translates to:
  /// **'Baraka Dastur'**
  String get appTitle;

  /// Joriy tilning o'z nomi
  ///
  /// In uz, this message translates to:
  /// **'Oʻzbekcha'**
  String get languageName;

  /// Til almashtirish tugmasi maslahati
  ///
  /// In uz, this message translates to:
  /// **'Tilni almashtirish'**
  String get switchLanguageTooltip;

  /// Yorug'/qorong'i mavzu tugmasi maslahati
  ///
  /// In uz, this message translates to:
  /// **'Mavzuni almashtirish'**
  String get switchThemeTooltip;

  /// Placeholder ekranlardagi izoh
  ///
  /// In uz, this message translates to:
  /// **'Bu ekran keyingi vazifalarda toʻldiriladi.'**
  String get placeholderNotice;

  /// Bosh ekran sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Bosh sahifa'**
  String get homeTitle;

  /// Bosh ekran tavsifi
  ///
  /// In uz, this message translates to:
  /// **'Bu yerda «Oʻzingizga toʻlangan» summa, «Kelajagim» balansi va haftalik vazifalar boʻladi.'**
  String get homeDescription;

  /// Bosh ekrandagi bo'limlar ro'yxati sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Boʻlimlar'**
  String get homeSectionsHeader;

  /// Daromad kiritish ekrani sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Yangi daromad'**
  String get incomeNewTitle;

  /// Daromad kiritish ekrani tavsifi
  ///
  /// In uz, this message translates to:
  /// **'Bu yerda daromad bir necha bosishda kiritiladi.'**
  String get incomeNewDescription;

  /// «Kelajagim» jamg'armasi ekrani sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Kelajagim'**
  String get vaultTitle;

  /// «Kelajagim» ekrani tavsifi
  ///
  /// In uz, this message translates to:
  /// **'Bu yerda «Kelajagim» jamgʻarmasi balansi va odat ketma-ketligi boʻladi.'**
  String get vaultDescription;

  /// Oylik audit ekrani sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Oylik audit'**
  String get auditTitle;

  /// Oylik audit ekrani tavsifi
  ///
  /// In uz, this message translates to:
  /// **'Bu yerda «Pul qayerga ketdi?» degan savolga javob topiladi.'**
  String get auditDescription;

  /// Kontent (boblar) ekrani sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Boblar'**
  String get contentTitle;

  /// Pigeon orqali Kotlin bilan aloqa holati kartasi
  ///
  /// In uz, this message translates to:
  /// **'Xavfsizlik koʻprigi'**
  String get nativeBridgeTitle;

  /// Native ko'prik tekshirilayotgan holat
  ///
  /// In uz, this message translates to:
  /// **'Tekshirilmoqda…'**
  String get nativeBridgeChecking;

  /// Native ko'prik javob qaytargan holat
  ///
  /// In uz, this message translates to:
  /// **'Ishlayapti · API v{apiVersion} · Android SDK {sdkInt}'**
  String nativeBridgeOk(int apiVersion, int sdkInt);

  /// Native ko'prik javob bermagan holat
  ///
  /// In uz, this message translates to:
  /// **'Native qatlam bilan aloqa yoʻq'**
  String get nativeBridgeUnavailable;

  /// Qulf ekranidagi asosiy ko'rsatma
  ///
  /// In uz, this message translates to:
  /// **'PIN kodni kiriting'**
  String get lockEnterPin;

  /// Qulf ekrani sarlavhasi ostidagi iliq izoh
  ///
  /// In uz, this message translates to:
  /// **'Daftaringiz qulflangan'**
  String get lockGreeting;

  /// Noto'g'ri PIN, lockout'gacha qolgan urinishlar
  ///
  /// In uz, this message translates to:
  /// **'Kod mos kelmadi. Kutish vaqtigacha yana {attempts} ta urinish bor.'**
  String pinWrong(int attempts);

  /// Lockout holati; time — mm:ss
  ///
  /// In uz, this message translates to:
  /// **'Juda koʻp notoʻgʻri urinish boʻldi. {time} dan keyin qayta urinib koʻring.'**
  String pinLockedOut(String time);

  /// PIN hosilasi hisoblanayotganda
  ///
  /// In uz, this message translates to:
  /// **'Tekshirilmoqda…'**
  String get pinVerifying;

  /// Kutilmagan xato
  ///
  /// In uz, this message translates to:
  /// **'Nimadir xato ketdi. Qaytadan urinib koʻring.'**
  String get pinErrorGeneric;

  /// PIN klaviaturasidagi o'chirish tugmasi (ekran o'quvchi uchun)
  ///
  /// In uz, this message translates to:
  /// **'Oxirgi raqamni oʻchirish'**
  String get pinKeyDelete;

  /// PIN klaviaturasidagi biometriya tugmasi (ekran o'quvchi uchun)
  ///
  /// In uz, this message translates to:
  /// **'Barmoq izi bilan kirish'**
  String get pinKeyBiometric;

  /// PIN nuqtalari (ekran o'quvchi uchun)
  ///
  /// In uz, this message translates to:
  /// **'{count} / 6 raqam kiritildi'**
  String pinDigitsEntered(int count);

  /// PIN o'rnatish ekrani sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'PIN kod oʻrnatish'**
  String get pinSetupTitle;

  /// PIN o'rnatish — 1-qadam
  ///
  /// In uz, this message translates to:
  /// **'Daftaringizni himoyalash uchun 6 xonali kod oʻylab toping'**
  String get pinSetupEnter;

  /// PIN o'rnatish — tasdiqlash qadami
  ///
  /// In uz, this message translates to:
  /// **'Kodni yana bir marta kiriting'**
  String get pinSetupConfirm;

  /// Tasdiqlash kodi birinchisiga mos emas
  ///
  /// In uz, this message translates to:
  /// **'Kodlar mos kelmadi. Keling, qaytadan boshlaymiz.'**
  String get pinSetupMismatch;

  /// 111111 yoki 123456 kabi oddiy PIN
  ///
  /// In uz, this message translates to:
  /// **'Bu kodni topish oson. Boshqa raqamlarni tanlang.'**
  String get pinTooSimple;

  /// PIN o'rnatish ekranidagi izoh
  ///
  /// In uz, this message translates to:
  /// **'Kodning oʻzi hech qayerda saqlanmaydi. Uni unutmang — tiklash imkoni yoʻq.'**
  String get pinSetupNote;

  /// PIN hosilasi hisoblanib saqlanayotganda
  ///
  /// In uz, this message translates to:
  /// **'Saqlanmoqda…'**
  String get pinSetupSaving;

  /// Biometriyani yoqish taklifi sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Barmoq izi bilan kirish'**
  String get biometricOfferTitle;

  /// Biometriyani yoqish taklifi matni
  ///
  /// In uz, this message translates to:
  /// **'Har safar kod kiritmasdan, barmoq izi yoki qurilma qulfi bilan kirishingiz mumkin. Buni istalgan vaqtda oʻchirsa boʻladi.'**
  String get biometricOfferBody;

  /// Biometriyani yoqish tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Yoqish'**
  String get biometricEnable;

  /// Biometriyani yoqmaslik tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Hozircha kerak emas'**
  String get biometricLater;

  /// Tizim BiometricPrompt oynasi sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Baraka Dastur'**
  String get biometricPromptTitle;

  /// Tizim BiometricPrompt oynasi izohi
  ///
  /// In uz, this message translates to:
  /// **'Daftaringizni ochish uchun tasdiqlang'**
  String get biometricPromptSubtitle;

  /// BiometricPrompt'dagi bekor qilish tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Kod bilan kirish'**
  String get biometricPromptCancel;

  /// Biometriya tizim tomonidan bloklangan
  ///
  /// In uz, this message translates to:
  /// **'Barmoq izi vaqtincha bloklangan. Kod bilan kiring.'**
  String get biometricLockedOut;

  /// Integrity ogohlantirishi sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Qurilmada xavf belgilari bor'**
  String get integrityTitle;

  /// Integrity ogohlantirishi matni
  ///
  /// In uz, this message translates to:
  /// **'Ilova ishlayveradi, lekin bunday qurilmada maʼlumotlaringiz xavfsizligini toʻliq kafolatlab boʻlmaydi. Aniqlangan: {risks}.'**
  String integrityBody(String risks);

  /// Xavf nomi
  ///
  /// In uz, this message translates to:
  /// **'root huquqlari'**
  String get integrityRiskRooted;

  /// Xavf nomi
  ///
  /// In uz, this message translates to:
  /// **'emulyator'**
  String get integrityRiskEmulator;

  /// Xavf nomi
  ///
  /// In uz, this message translates to:
  /// **'ulangan debugger'**
  String get integrityRiskDebugger;

  /// Xavf nomi
  ///
  /// In uz, this message translates to:
  /// **'ilova imzosi mos emas'**
  String get integrityRiskSignature;

  /// Xavf nomi
  ///
  /// In uz, this message translates to:
  /// **'ilova oʻzgartirilgan boʻlishi mumkin'**
  String get integrityRiskDebuggable;

  /// Ogohlantirishni yopish tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Tushunarli'**
  String get integrityDismiss;

  /// Bosh sahifadagi daromad qo'shish tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Daromad'**
  String get homeAddIncome;

  /// Daromad summasi bo'sh holatda
  ///
  /// In uz, this message translates to:
  /// **'Summani kiriting'**
  String get incomeAmountHint;

  /// Oxirgi summalar chip'lari sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Oxirgi summalar'**
  String get incomeRecentAmounts;

  /// Daromad manbai tanlovi
  ///
  /// In uz, this message translates to:
  /// **'Manba'**
  String get incomeSourceLabel;

  /// Manba
  ///
  /// In uz, this message translates to:
  /// **'Kunlik ish'**
  String get incomeSourceDailyWork;

  /// Manba
  ///
  /// In uz, this message translates to:
  /// **'Buyurtma'**
  String get incomeSourceOrder;

  /// Manba
  ///
  /// In uz, this message translates to:
  /// **'Oylik'**
  String get incomeSourceSalary;

  /// Manba
  ///
  /// In uz, this message translates to:
  /// **'Boshqa'**
  String get incomeSourceOther;

  /// Kanal tanlovi
  ///
  /// In uz, this message translates to:
  /// **'Toʻlov turi'**
  String get channelLabel;

  /// Kanal
  ///
  /// In uz, this message translates to:
  /// **'Naqd'**
  String get channelCash;

  /// Kanal
  ///
  /// In uz, this message translates to:
  /// **'Karta'**
  String get channelCard;

  /// Daromadni saqlash tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Saqlash'**
  String get incomeSave;

  /// Daromad saqlangach xabar
  ///
  /// In uz, this message translates to:
  /// **'Daromad yozildi. Barakali boʻlsin!'**
  String get incomeSaved;

  /// Summa klaviaturasidagi o'chirish
  ///
  /// In uz, this message translates to:
  /// **'Oxirgi raqamni oʻchirish'**
  String get keypadDelete;

  /// Ulush taklifi sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Avval oʻzingizga'**
  String get shareOfferTitle;

  /// Ulush taklifi; amount — formatlangan summa
  ///
  /// In uz, this message translates to:
  /// **'Shundan {amount} — kelajagingiz uchun.'**
  String shareOfferBody(String amount);

  /// Maslahatchi maslahati
  ///
  /// In uz, this message translates to:
  /// **'Oz boʻlsa ham har gal ajratsangiz, odatga aylanadi.'**
  String get shareOfferHint;

  /// Ulushni ajratish tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Ajratish'**
  String get shareAllocate;

  /// Boshqa summa tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Boshqa summa'**
  String get shareOtherAmount;

  /// Ajratmaslik tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Bu safar emas'**
  String get shareSkip;

  /// Ajratmaslik tanlanganda
  ///
  /// In uz, this message translates to:
  /// **'Mayli, keyingi safar. Daftar sizni kutadi.'**
  String get shareSkipped;

  /// Ajratilgach
  ///
  /// In uz, this message translates to:
  /// **'Kelajagingizga {amount} qoʻshildi.'**
  String shareDone(String amount);

  /// Streak soni
  ///
  /// In uz, this message translates to:
  /// **'{count} hafta'**
  String vaultHabitWeeks(int count);

  /// Streak izohi
  ///
  /// In uz, this message translates to:
  /// **'ketma-ket oʻzingizga toʻladingiz'**
  String get vaultHabitCaption;

  /// Jami haftalar
  ///
  /// In uz, this message translates to:
  /// **'Jami {count} hafta ajratilgan'**
  String vaultHabitTotal(int count);

  /// Joriy hafta bajarilgan
  ///
  /// In uz, this message translates to:
  /// **'Bu hafta ajratildi — barakalla!'**
  String get vaultThisWeekDone;

  /// Joriy hafta bajarilmagan
  ///
  /// In uz, this message translates to:
  /// **'Bu hafta hali ajratilmadi. Oz summa ham hisobga oʻtadi.'**
  String get vaultThisWeekPending;

  /// Balans yorlig'i
  ///
  /// In uz, this message translates to:
  /// **'Kelajagim jamgʻarmasida'**
  String get vaultBalanceLabel;

  /// Qoida qisqacha (foiz)
  ///
  /// In uz, this message translates to:
  /// **'Ulush: har daromaddan {percent} %'**
  String vaultRuleSummaryPercent(String percent);

  /// Qoida qisqacha (qat'iy)
  ///
  /// In uz, this message translates to:
  /// **'Ulush: oyiga {amount}'**
  String vaultRuleSummaryFixed(String amount);

  /// Progressiv rejim belgisi
  ///
  /// In uz, this message translates to:
  /// **'progressiv'**
  String get vaultRuleProgressiveTag;

  /// Qoidani o'zgartirish tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Ulushni sozlash'**
  String get vaultRuleEdit;

  /// Pul olish tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Pul olish'**
  String get vaultWithdraw;

  /// Tarix sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Tarix'**
  String get vaultHistory;

  /// Bo'sh tarix
  ///
  /// In uz, this message translates to:
  /// **'Hali yozuv yoʻq. Birinchi daromaddan boshlaymiz.'**
  String get vaultHistoryEmpty;

  /// Tarix: sabab
  ///
  /// In uz, this message translates to:
  /// **'Daromad ulushi'**
  String get vaultReasonIncomeShare;

  /// Tarix: sabab
  ///
  /// In uz, this message translates to:
  /// **'Boshlangʻich jamgʻarma'**
  String get vaultReasonInitial;

  /// Tarix: sabab
  ///
  /// In uz, this message translates to:
  /// **'Qoʻshildi'**
  String get vaultReasonManual;

  /// Tarix: pul olish
  ///
  /// In uz, this message translates to:
  /// **'Olindi: {note}'**
  String vaultReasonWithdrawal(String note);

  /// Boshlang'ich balans kartasi sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Avval yigʻilgan pul'**
  String get vaultInitialTitle;

  /// Boshlang'ich balans kartasi matni
  ///
  /// In uz, this message translates to:
  /// **'Ilovadan oldin yigʻib qoʻygan pulingiz bormi? Uni bir marta kiritib qoʻying — hisob toʻliq boʻladi.'**
  String get vaultInitialBody;

  /// Boshlang'ich balansni kiritish
  ///
  /// In uz, this message translates to:
  /// **'Kiritish'**
  String get vaultInitialAction;

  /// Boshlang'ich balans saqlangach
  ///
  /// In uz, this message translates to:
  /// **'Boshlangʻich jamgʻarma yozildi.'**
  String get vaultInitialSaved;

  /// Progressiv taklif sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Barakalla!'**
  String get vaultProgressionTitle;

  /// Progressiv taklif
  ///
  /// In uz, this message translates to:
  /// **'{weeks} hafta ketma-ket oʻzingizga toʻladingiz. Ulushni {percent} % ga oshirasizmi?'**
  String vaultProgressionBody(int weeks, String percent);

  /// Progressiv taklifni qabul qilish
  ///
  /// In uz, this message translates to:
  /// **'Oshirish'**
  String get vaultProgressionAccept;

  /// Progressiv taklifni rad etish
  ///
  /// In uz, this message translates to:
  /// **'Hozircha yoʻq'**
  String get vaultProgressionDecline;

  /// Qoida ekrani sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Ulush sozlamalari'**
  String get ruleTitle;

  /// Qoida varianti
  ///
  /// In uz, this message translates to:
  /// **'5 % — boshlangʻich'**
  String get rulePercent5;

  /// Qoida varianti
  ///
  /// In uz, this message translates to:
  /// **'10 % — maqsad (daromadning oʻndan biri)'**
  String get rulePercent10;

  /// Qoida varianti
  ///
  /// In uz, this message translates to:
  /// **'Qatʼiy summa — oyiga'**
  String get ruleFixed;

  /// Qat'iy summa qiymati
  ///
  /// In uz, this message translates to:
  /// **'Oylik summa: {amount}'**
  String ruleFixedAmount(String amount);

  /// Qat'iy summa hali kiritilmagan
  ///
  /// In uz, this message translates to:
  /// **'Summani tanlang'**
  String get ruleFixedChoose;

  /// Progressiv rejim kaliti
  ///
  /// In uz, this message translates to:
  /// **'Progressiv rejim'**
  String get ruleProgressive;

  /// Progressiv rejim izohi
  ///
  /// In uz, this message translates to:
  /// **'4 hafta ketma-ket ajratsangiz, ulushni 1 % ga oshirishni taklif qilamiz (10 % gacha).'**
  String get ruleProgressiveHint;

  /// Qoidani saqlash
  ///
  /// In uz, this message translates to:
  /// **'Saqlash'**
  String get ruleSave;

  /// Qoida saqlangach
  ///
  /// In uz, this message translates to:
  /// **'Ulush yangilandi.'**
  String get ruleSaved;

  /// Pul olish ekrani sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Kelajagimdan pul olish'**
  String get withdrawTitle;

  /// Pul olish eslatmasi
  ///
  /// In uz, this message translates to:
  /// **'Bu pul — kelajakdagi oʻzingizniki. Uni faqat chinakam zarurat uchun oling.'**
  String get withdrawReminder;

  /// Pul olish — balans
  ///
  /// In uz, this message translates to:
  /// **'Mavjud: {amount}'**
  String withdrawAvailable(String amount);

  /// Pul olish summasi maydoni
  ///
  /// In uz, this message translates to:
  /// **'Qancha olasiz? (soʻm)'**
  String get withdrawAmountLabel;

  /// Pul olish sababi maydoni
  ///
  /// In uz, this message translates to:
  /// **'Nima uchun? (majburiy)'**
  String get withdrawReasonLabel;

  /// Pul olish sababi misoli
  ///
  /// In uz, this message translates to:
  /// **'Masalan: davolanish, uy taʼmiri'**
  String get withdrawReasonHint;

  /// Pul olish — davom etish
  ///
  /// In uz, this message translates to:
  /// **'Davom etish'**
  String get withdrawContinue;

  /// Pul olish pauzasi sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Bir oz oʻylab koʻraylik'**
  String get withdrawPauseTitle;

  /// Pul olish pauzasi matni
  ///
  /// In uz, this message translates to:
  /// **'{amount} kelajagingizdan olinadi. Bu haqiqatan zarurmi?'**
  String withdrawPauseBody(String amount);

  /// Pauza davomida tasdiqlash tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Ha, olaman ({seconds})'**
  String withdrawPauseWait(int seconds);

  /// Pauzadan keyin tasdiqlash tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Ha, olaman'**
  String get withdrawPauseConfirm;

  /// Pul olishdan voz kechish
  ///
  /// In uz, this message translates to:
  /// **'Fikrimdan qaytdim'**
  String get withdrawPauseCancel;

  /// Pul olingach
  ///
  /// In uz, this message translates to:
  /// **'{amount} olindi. Imkon boʻlganda oʻrnini toʻldiramiz.'**
  String withdrawDone(String amount);

  /// Pul olish — summa xatosi
  ///
  /// In uz, this message translates to:
  /// **'Summa mavjud balansdan oshmasin.'**
  String get withdrawErrorAmount;

  /// PIN qayta so'rash sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'PIN kodni qayta kiriting'**
  String get pinConfirmTitle;

  /// Umumiy bekor qilish
  ///
  /// In uz, this message translates to:
  /// **'Bekor qilish'**
  String get cancel;

  /// Summa kiritish oynasi sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Summa'**
  String get amountDialogTitle;

  /// Summa kiritish tasdig'i
  ///
  /// In uz, this message translates to:
  /// **'Tayyor'**
  String get amountDialogDone;

  /// Umumiy xato
  ///
  /// In uz, this message translates to:
  /// **'Nimadir xato ketdi. Qaytadan urinib koʻring.'**
  String get genericError;

  /// Bosh ekran 1-KPI
  ///
  /// In uz, this message translates to:
  /// **'Oʻzingizga toʻlangan (shu oy)'**
  String get homePaidToSelf;

  /// Bosh ekran: jamg'arma
  ///
  /// In uz, this message translates to:
  /// **'Kelajagim'**
  String get homeVaultBalance;

  /// Bosh ekran: streak
  ///
  /// In uz, this message translates to:
  /// **'{count} hafta ketma-ket'**
  String homeStreak(int count);

  /// Bosh ekran: oy yakuni
  ///
  /// In uz, this message translates to:
  /// **'Oy yakuni'**
  String get homeMonthResult;

  /// Musbat oy yakuni izohi
  ///
  /// In uz, this message translates to:
  /// **'Qoʻlingizda qolishi kerak'**
  String get homeMonthResultPlus;

  /// Manfiy oy yakuni izohi
  ///
  /// In uz, this message translates to:
  /// **'Chiqim kirimdan koʻp yozilgan'**
  String get homeMonthResultMinus;

  /// Haftalik vazifalar kartasi
  ///
  /// In uz, this message translates to:
  /// **'Shu haftaning vazifalari'**
  String get homeWeeklyTasks;

  /// Bosh ekran: xarajat tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Xarajat'**
  String get homeAddExpense;

  /// Audit eslatmasi
  ///
  /// In uz, this message translates to:
  /// **'{month} uchun oylik audit — «Pul qayerga ketdi?»'**
  String homeAuditDue(String month);

  /// Audit bajarilgan
  ///
  /// In uz, this message translates to:
  /// **'Oxirgi audit: {month}'**
  String homeAuditDone(String month);

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Xarajatlar'**
  String get sectionExpenses;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Majburiyatlar'**
  String get sectionObligations;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Nasiya daftari'**
  String get sectionNasiya;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Kimning puli?'**
  String get sectionWhoseMoney;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Oila aʼzolari'**
  String get sectionMembers;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Sozlamalar'**
  String get sectionSettings;

  /// Kategoriya
  ///
  /// In uz, this message translates to:
  /// **'Ijara'**
  String get catRent;

  /// Kategoriya
  ///
  /// In uz, this message translates to:
  /// **'Kredit'**
  String get catCredit;

  /// Kategoriya
  ///
  /// In uz, this message translates to:
  /// **'Oziq-ovqat'**
  String get catGroceries;

  /// Kategoriya
  ///
  /// In uz, this message translates to:
  /// **'Kommunal'**
  String get catUtilities;

  /// Kategoriya
  ///
  /// In uz, this message translates to:
  /// **'Telefon'**
  String get catPhone;

  /// Kategoriya
  ///
  /// In uz, this message translates to:
  /// **'Benzin'**
  String get catFuel;

  /// Kategoriya
  ///
  /// In uz, this message translates to:
  /// **'Yoʻlkira'**
  String get catTransport;

  /// Kategoriya
  ///
  /// In uz, this message translates to:
  /// **'Mayda kundalik xarajatlar'**
  String get catDailySmall;

  /// Kategoriya
  ///
  /// In uz, this message translates to:
  /// **'Bola'**
  String get catChildren;

  /// Kategoriya
  ///
  /// In uz, this message translates to:
  /// **'Sadaqa'**
  String get catSadaqa;

  /// Kategoriya
  ///
  /// In uz, this message translates to:
  /// **'Boshqa'**
  String get catOther;

  /// Xarajat ekrani
  ///
  /// In uz, this message translates to:
  /// **'Yangi xarajat'**
  String get expenseNewTitle;

  /// Xarajat kategoriyasi
  ///
  /// In uz, this message translates to:
  /// **'Kategoriya'**
  String get expenseCategory;

  /// Xarajat saqlandi
  ///
  /// In uz, this message translates to:
  /// **'Xarajat yozildi. Har bir soʻmni yozish — pulga egalikning boshi.'**
  String get expenseSaved;

  /// Xarajatlar ro'yxati
  ///
  /// In uz, this message translates to:
  /// **'Shu oyning xarajatlari'**
  String get expensesTitle;

  /// Bo'sh ro'yxat
  ///
  /// In uz, this message translates to:
  /// **'Bu oy hali xarajat yozilmagan.'**
  String get expensesEmpty;

  /// Jami xarajat
  ///
  /// In uz, this message translates to:
  /// **'Jami: {amount}'**
  String expensesTotal(String amount);

  /// Oila a'zosi tanlovi
  ///
  /// In uz, this message translates to:
  /// **'Kim'**
  String get memberLabel;

  /// O'chirish tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Oʻchirish'**
  String get delete;

  /// Saqlash tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Saqlash'**
  String get save;

  /// Bo'sh majburiyatlar
  ///
  /// In uz, this message translates to:
  /// **'Doimiy toʻlovlarni kiriting: ijara, kredit, kommunal. Toʻlovdan bir kun oldin eslatamiz.'**
  String get obligationsEmpty;

  /// Qo'shish tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Majburiyat qoʻshish'**
  String get obligationAdd;

  /// Tahrirlash sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Majburiyatni tahrirlash'**
  String get obligationEdit;

  /// Majburiyat nomi
  ///
  /// In uz, this message translates to:
  /// **'Nomi'**
  String get obligationTitleLabel;

  /// Majburiyat turi
  ///
  /// In uz, this message translates to:
  /// **'Turi'**
  String get obligationKindLabel;

  /// To'lov kuni
  ///
  /// In uz, this message translates to:
  /// **'Har oy nechanchi kuni?'**
  String get obligationDayLabel;

  /// To'lov kuni ko'rinishi
  ///
  /// In uz, this message translates to:
  /// **'Har oy {day}-sana'**
  String obligationDay(int day);

  /// Majburiyatlar jami
  ///
  /// In uz, this message translates to:
  /// **'Oyiga jami: {amount}'**
  String obligationsMonthly(String amount);

  /// Majburiyat turi
  ///
  /// In uz, this message translates to:
  /// **'Ijara'**
  String get kindRent;

  /// Majburiyat turi
  ///
  /// In uz, this message translates to:
  /// **'Kredit'**
  String get kindCredit;

  /// Majburiyat turi
  ///
  /// In uz, this message translates to:
  /// **'Kommunal'**
  String get kindUtility;

  /// Majburiyat turi
  ///
  /// In uz, this message translates to:
  /// **'Telefon'**
  String get kindPhone;

  /// Majburiyat turi
  ///
  /// In uz, this message translates to:
  /// **'Benzin'**
  String get kindFuel;

  /// Majburiyat turi
  ///
  /// In uz, this message translates to:
  /// **'Boshqa'**
  String get kindOther;

  /// Bildirishnoma kanali
  ///
  /// In uz, this message translates to:
  /// **'Toʻlov eslatmalari'**
  String get reminderChannel;

  /// Eslatma sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Ertaga toʻlov: {title}'**
  String reminderTitle(String title);

  /// Eslatma matni (summasiz)
  ///
  /// In uz, this message translates to:
  /// **'Eslatma: ertaga «{title}» toʻlov kuni. Oldindan tayyorlab qoʻysangiz, koʻngil xotirjam boʻladi.'**
  String reminderBody(String title);

  /// Bildirishnoma ruxsati yo'q
  ///
  /// In uz, this message translates to:
  /// **'Bildirishnomalar oʻchirilgan — eslatmalar kelmaydi.'**
  String get notificationsOff;

  /// Bildirishnoma ruxsatini so'rash
  ///
  /// In uz, this message translates to:
  /// **'Yoqish'**
  String get notificationsEnable;

  /// Bo'sh nasiya
  ///
  /// In uz, this message translates to:
  /// **'Doʻkondan nasiyaga olgan narsalaringizni shu yerga yozing — kimga qancha qarzingiz borligi koʻrinib turadi.'**
  String get nasiyaEmpty;

  /// Qo'shish
  ///
  /// In uz, this message translates to:
  /// **'Nasiya qoʻshish'**
  String get nasiyaAdd;

  /// Kreditor nomi
  ///
  /// In uz, this message translates to:
  /// **'Doʻkon yoki kimga'**
  String get nasiyaShopLabel;

  /// Jami nasiya
  ///
  /// In uz, this message translates to:
  /// **'Jami nasiya: {amount}'**
  String nasiyaTotal(String amount);

  /// Qoldiq
  ///
  /// In uz, this message translates to:
  /// **'Qoldiq: {amount}'**
  String nasiyaRemaining(String amount);

  /// Muddat
  ///
  /// In uz, this message translates to:
  /// **'Muddati: {date}'**
  String nasiyaDue(String date);

  /// To'lov tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Toʻlov'**
  String get nasiyaPay;

  /// Nasiya yopilgan
  ///
  /// In uz, this message translates to:
  /// **'Yopildi — barakalla!'**
  String get nasiyaPaid;

  /// Muddat maydoni
  ///
  /// In uz, this message translates to:
  /// **'Qachongacha (ixtiyoriy)'**
  String get nasiyaDueLabel;

  /// Nasiya summasi
  ///
  /// In uz, this message translates to:
  /// **'Summa'**
  String get nasiyaAmountLabel;

  /// Audit davri
  ///
  /// In uz, this message translates to:
  /// **'Davr: {start} — {end}'**
  String auditPeriod(String start, String end);

  /// Audit 1-qadam
  ///
  /// In uz, this message translates to:
  /// **'Daromad'**
  String get auditStepIncome;

  /// Audit 2-qadam
  ///
  /// In uz, this message translates to:
  /// **'Majburiyatlar'**
  String get auditStepObligations;

  /// Audit 3-qadam
  ///
  /// In uz, this message translates to:
  /// **'Xarajatlar'**
  String get auditStepExpenses;

  /// Audit 4-qadam
  ///
  /// In uz, this message translates to:
  /// **'Natija'**
  String get auditStepResult;

  /// Audit daromad izohi
  ///
  /// In uz, this message translates to:
  /// **'Oʻtgan oyda qancha daromad boʻldi? Yozilmaganini qoʻshing.'**
  String get auditIncomeHint;

  /// Audit: daromad qo'shish
  ///
  /// In uz, this message translates to:
  /// **'Yozilmagan daromad qoʻshish'**
  String get auditAddIncome;

  /// Audit majburiyatlar izohi
  ///
  /// In uz, this message translates to:
  /// **'Bu toʻlovlar oyida toʻlangan deb hisoblanadi. Xarajat sifatida yozilgan qismi ikki marta sanalmaydi.'**
  String get auditObligationsHint;

  /// Audit majburiyat qatori
  ///
  /// In uz, this message translates to:
  /// **'{title}: {amount} (yozilgan: {recorded})'**
  String auditObligationLine(String title, String amount, String recorded);

  /// Audit xarajatlar izohi
  ///
  /// In uz, this message translates to:
  /// **'Har bir kategoriya boʻyicha esingizda qolganini qoʻshing.'**
  String get auditExpensesHint;

  /// Kategoriyaga qo'shish
  ///
  /// In uz, this message translates to:
  /// **'{category}ga qoʻshish'**
  String auditAddTo(String category);

  /// Natija qatori
  ///
  /// In uz, this message translates to:
  /// **'Daromad'**
  String get auditIncome;

  /// Natija qatori
  ///
  /// In uz, this message translates to:
  /// **'Majburiyatlar'**
  String get auditObligations;

  /// Natija qatori
  ///
  /// In uz, this message translates to:
  /// **'Kiritilgan xarajatlar'**
  String get auditExpenses;

  /// Natija qatori
  ///
  /// In uz, this message translates to:
  /// **'Jamgʻarma'**
  String get auditSavings;

  /// Natija: izohsiz
  ///
  /// In uz, this message translates to:
  /// **'Izohsiz qolgan summa'**
  String get auditUnexplained;

  /// Izohsiz summa izohi
  ///
  /// In uz, this message translates to:
  /// **'Bu pul qayerga ketgani nomaʼlum. Koʻpincha u mayda kundalik xarajatlar — somsa, ichimlik, yoʻl-yoʻlakay xaridlar.'**
  String get auditUnexplainedHint;

  /// Manfiy izohsiz
  ///
  /// In uz, this message translates to:
  /// **'Chiqim kirimdan koʻp yozilgan. Ehtimol, daromadning bir qismi kiritilmagan.'**
  String get auditNegativeHint;

  /// Izohsizni belgilash
  ///
  /// In uz, this message translates to:
  /// **'Mayda kundalik xarajat deb belgilash'**
  String get auditMarkSmall;

  /// Izohsizni taqsimlash
  ///
  /// In uz, this message translates to:
  /// **'Kategoriyalarga taqsimlash'**
  String get auditDistribute;

  /// Yakunlash
  ///
  /// In uz, this message translates to:
  /// **'Auditni yakunlash'**
  String get auditFinish;

  /// Audit yakunlandi
  ///
  /// In uz, this message translates to:
  /// **'Audit yakunlandi. Pul qayerga ketganini bilish — uni boshqarishning boshi.'**
  String get auditFinished;

  /// Keyingi qadam
  ///
  /// In uz, this message translates to:
  /// **'Keyingi'**
  String get next;

  /// Oldingi qadam
  ///
  /// In uz, this message translates to:
  /// **'Orqaga'**
  String get back;

  /// Kimning puli sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'{month}: daromadingiz kimlarga ketdi'**
  String whoseIntro(String month);

  /// Bo'sh
  ///
  /// In uz, this message translates to:
  /// **'Bu oy uchun hali maʼlumot yoʻq.'**
  String get whoseEmpty;

  /// Ega
  ///
  /// In uz, this message translates to:
  /// **'Uy egasiniki'**
  String get ownerLandlord;

  /// Ega
  ///
  /// In uz, this message translates to:
  /// **'Bankniki'**
  String get ownerBank;

  /// Ega
  ///
  /// In uz, this message translates to:
  /// **'Doʻkondorniki'**
  String get ownerShop;

  /// Ega
  ///
  /// In uz, this message translates to:
  /// **'Davlatniki (kommunal)'**
  String get ownerUtilities;

  /// Ega
  ///
  /// In uz, this message translates to:
  /// **'Yoqilgʻiniki'**
  String get ownerFuel;

  /// Ega
  ///
  /// In uz, this message translates to:
  /// **'Oʻzingizniki'**
  String get ownerSelf;

  /// Ega
  ///
  /// In uz, this message translates to:
  /// **'Sadaqa'**
  String get ownerSadaqa;

  /// Ega
  ///
  /// In uz, this message translates to:
  /// **'Boshqalar'**
  String get ownerOther;

  /// Ega
  ///
  /// In uz, this message translates to:
  /// **'Izohsiz'**
  String get ownerUnexplained;

  /// Ulush foizi
  ///
  /// In uz, this message translates to:
  /// **'{percent} %'**
  String whosePercent(String percent);

  /// Egasining standart nomi
  ///
  /// In uz, this message translates to:
  /// **'Men'**
  String get memberOwnerDefault;

  /// Ega belgisi
  ///
  /// In uz, this message translates to:
  /// **'egasi'**
  String get memberOwnerTag;

  /// Bola belgisi
  ///
  /// In uz, this message translates to:
  /// **'bola'**
  String get memberChildTag;

  /// Qo'shish
  ///
  /// In uz, this message translates to:
  /// **'Aʼzo qoʻshish'**
  String get memberAdd;

  /// Ism maydoni
  ///
  /// In uz, this message translates to:
  /// **'Ismi'**
  String get memberName;

  /// Bola belgisi tanlovi
  ///
  /// In uz, this message translates to:
  /// **'Bola'**
  String get memberIsChild;

  /// A'zolar izohi
  ///
  /// In uz, this message translates to:
  /// **'Byudjetni birga toʻldiring — «Yolgʻiz yozmang». Har yozuvda kim kiritgani koʻrinadi.'**
  String get membersHint;

  /// Oylik kuni sozlamasi
  ///
  /// In uz, this message translates to:
  /// **'Oylik kuni'**
  String get settingsMonthStart;

  /// Oylik kuni izohi
  ///
  /// In uz, this message translates to:
  /// **'Oylik davr shu kundan boshlanadi: {day}-sana'**
  String settingsMonthStartHint(int day);

  /// Har ta'limiy ekrandagi disklеymer (SPEC 3)
  ///
  /// In uz, this message translates to:
  /// **'Taʼlimiy material. Fatvo yoki moliyaviy maslahat emas.'**
  String get contentDisclaimer;

  /// Dars ichidagi maslahat bloki belgisi (umumiy taʼlimiy maslahat, shaxsiy moliyaviy maslahat emas)
  ///
  /// In uz, this message translates to:
  /// **'Maslahatchi'**
  String get contentAdvisor;

  /// Kontent buzuq/yo'q
  ///
  /// In uz, this message translates to:
  /// **'Boblarni yuklab boʻlmadi. Ilovaning keyingi yangilanishida tuzatiladi.'**
  String get contentLoadError;

  /// Yopiq bob
  ///
  /// In uz, this message translates to:
  /// **'{date} kuni ochiladi'**
  String chapterLocked(String date);

  /// Odat qoidasi bilan yopiq bob
  ///
  /// In uz, this message translates to:
  /// **'Oldingi bobdan yana {count} ta vazifa bajarilsa ochiladi'**
  String chapterLockedTasks(int count);

  /// Ochiq bob
  ///
  /// In uz, this message translates to:
  /// **'Ochiq'**
  String get chapterOpen;

  /// Qonun raqami
  ///
  /// In uz, this message translates to:
  /// **'{number}-qonun'**
  String lawLabel(int number);

  /// Daftar sahifasi
  ///
  /// In uz, this message translates to:
  /// **'Daftar sahifasi'**
  String get daftarPageTitle;

  /// Daftar sahifasi izohi
  ///
  /// In uz, this message translates to:
  /// **'Qonunni oʻz qoʻlingiz bilan, oʻz soʻzlaringiz bilan yozing. Qoʻl bilan yozilgan narsa esda qoladi.'**
  String get daftarPageHint;

  /// Saqlandi
  ///
  /// In uz, this message translates to:
  /// **'Daftaringizga yozildi.'**
  String get daftarPageSaved;

  /// Daftar sahifasi to'ldirilgan
  ///
  /// In uz, this message translates to:
  /// **'Yozilgan'**
  String get daftarPageWritten;

  /// Haftalik vazifalar
  ///
  /// In uz, this message translates to:
  /// **'Shu haftaning vazifalari'**
  String get weeklyTasksTitle;

  /// Vazifalar holati
  ///
  /// In uz, this message translates to:
  /// **'{done} / 3 bajarildi'**
  String weeklyTasksProgress(int done);

  /// Avto belgilangan vazifa
  ///
  /// In uz, this message translates to:
  /// **'ilova oʻzi belgiladi'**
  String get taskAuto;

  /// PENDING diniy blok belgisi
  ///
  /// In uz, this message translates to:
  /// **'Ulamo tekshiruvida — faqat test rejimida koʻrinadi'**
  String get religiousPending;

  /// Diniy matn manbasi
  ///
  /// In uz, this message translates to:
  /// **'Manba: {source}'**
  String religiousSource(String source);

  /// Juma bildirishnoma kanali
  ///
  /// In uz, this message translates to:
  /// **'Haftalik bob'**
  String get weeklyChannel;

  /// Juma bildirishnomasi sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Bugun juma — haftalik yakun'**
  String get weeklyNotificationTitle;

  /// Juma bildirishnomasi matni
  ///
  /// In uz, this message translates to:
  /// **'Yangi bob ochilgan boʻlishi mumkin. Oʻtgan haftaning vazifalarini birga koʻrib chiqaylik.'**
  String get weeklyNotificationBody;

  /// Kategoriya
  ///
  /// In uz, this message translates to:
  /// **'Ichimlik va gazak'**
  String get catSnacks;

  /// Kategoriya
  ///
  /// In uz, this message translates to:
  /// **'Choyxona va kafe'**
  String get catCafe;

  /// Zarur/Kerak/Havas sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Toifa'**
  String get necessityLabel;

  /// Toifa: usiz yashab bo'lmaydi
  ///
  /// In uz, this message translates to:
  /// **'Zarur'**
  String get necessityZarur;

  /// Toifa: usiz qiyin
  ///
  /// In uz, this message translates to:
  /// **'Kerak'**
  String get necessityKerak;

  /// Toifa: usiz bemalol yashasa bo'ladi
  ///
  /// In uz, this message translates to:
  /// **'Havas'**
  String get necessityHavas;

  /// Sadaqa toifasi
  ///
  /// In uz, this message translates to:
  /// **'Toifadan tashqari'**
  String get necessityNone;

  /// Sadaqa izohi
  ///
  /// In uz, this message translates to:
  /// **'Sadaqa havas emas va «oqib ketish» hisobiga kirmaydi.'**
  String get necessitySadaqaNote;

  /// Xarajat belgilari sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Belgilar'**
  String get expenseFlagsLabel;

  /// isGift belgisi
  ///
  /// In uz, this message translates to:
  /// **'Sovgʻa — hisobga kirmaydi'**
  String get flagGift;

  /// isOstentation belgisi
  ///
  /// In uz, this message translates to:
  /// **'Obroʻ uchun'**
  String get flagOstentation;

  /// fundedByDebt belgisi
  ///
  /// In uz, this message translates to:
  /// **'Qarzga olingan pul bilan'**
  String get flagDebt;

  /// Qizil bayroq izohi
  ///
  /// In uz, this message translates to:
  /// **'Qarz bilan qilingan havas'**
  String get debtHavasFlag;

  /// Xarajatni odatga bog'lash
  ///
  /// In uz, this message translates to:
  /// **'Odat'**
  String get habitLabel;

  /// Odat tanlanmagan
  ///
  /// In uz, this message translates to:
  /// **'Yoʻq'**
  String get habitNone;

  /// Shablonlar kartasi
  ///
  /// In uz, this message translates to:
  /// **'Tez yozish'**
  String get quickTitle;

  /// Shablon yo'q
  ///
  /// In uz, this message translates to:
  /// **'Tez-tez qiladigan xarajatingizni (somsa, choy, benzin) shablon qiling — keyin bir bosishda yoziladi.'**
  String get quickEmpty;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Oxirgisini takrorlash'**
  String get repeatLast;

  /// Snackbar
  ///
  /// In uz, this message translates to:
  /// **'Takrorlandi: {amount}'**
  String repeatLastDone(String amount);

  /// Snackbar
  ///
  /// In uz, this message translates to:
  /// **'{title} yozildi — {amount}'**
  String templateRecorded(String title, String amount);

  /// Snackbar amali
  ///
  /// In uz, this message translates to:
  /// **'Bekor qilish'**
  String get undo;

  /// Ekran sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Shablonlar'**
  String get templatesTitle;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Shablon qoʻshish'**
  String get templateAdd;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nomi (masalan, Somsa)'**
  String get templateTitleLabel;

  /// Xarajat ekranida belgi
  ///
  /// In uz, this message translates to:
  /// **'Shablon sifatida ham saqlash'**
  String get templateFromForm;

  /// Ekran sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Kategoriyalar va toifalar'**
  String get categoriesTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Har kategoriyaning standart toifasi bor. Oʻzgartirsangiz, yangi xarajatlarga qoʻllanadi; kim va qachon oʻzgartirgani saqlanadi.'**
  String get categoriesHint;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Oʻzgarishlar tarixi'**
  String get categoryHistory;

  /// Bo'sh tarix
  ///
  /// In uz, this message translates to:
  /// **'Hali oʻzgartirilmagan'**
  String get categoryHistoryEmpty;

  /// Tarix qatori
  ///
  /// In uz, this message translates to:
  /// **'{date} · {from} → {to} · {who}'**
  String categoryHistoryItem(String date, String from, String to, String who);

  /// Dialog
  ///
  /// In uz, this message translates to:
  /// **'Kim oʻzgartiryapti?'**
  String get whoChanges;

  /// Jamlash kartasi
  ///
  /// In uz, this message translates to:
  /// **'Mayda xarajatlar jamlanganda'**
  String get rollupTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Oxirgi 30 kun boʻyicha prognoz'**
  String get rollupWindow;

  /// Jamlash qatori
  ///
  /// In uz, this message translates to:
  /// **'haftasiga {week} · oyiga {month} · yiliga {year}'**
  String rollupLine(String week, String month, String year);

  /// Taqqoslash
  ///
  /// In uz, this message translates to:
  /// **'Oyiga — «{obligation}»ning {percent}%i'**
  String rollupShare(String obligation, String percent);

  /// Ekran sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Havas va odatlar'**
  String get havasTitle;

  /// Qoida
  ///
  /// In uz, this message translates to:
  /// **'Havasni oʻldirma, navbatga qoʻy. Chegara oiladagi barcha kattalar rozi boʻlgandagina faol boʻladi; bloklash yoʻq.'**
  String get havasRule;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Havas uchun oylik chegara hali kelishilmagan.'**
  String get havasNoLimit;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Shu oy havasga: {amount}'**
  String havasSpent(String amount);

  /// Progress
  ///
  /// In uz, this message translates to:
  /// **'{spent} / {limit}'**
  String havasOfLimit(String spent, String limit);

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Yana {amount} qoldi'**
  String havasOk(String amount);

  /// 80% ogohlantirish
  ///
  /// In uz, this message translates to:
  /// **'Chegaraga yaqinlashdingiz ({percent}%).'**
  String havasNear(String percent);

  /// 100% ogohlantirish
  ///
  /// In uz, this message translates to:
  /// **'Chegaradan {amount} oshdi. Taqiq yoʻq — keyingi oyni birga rejalashtiring.'**
  String havasOver(String amount);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Chegara taklif qilish'**
  String get havasPropose;

  /// Summa varag'i
  ///
  /// In uz, this message translates to:
  /// **'Havas uchun oylik chegara'**
  String get havasProposeTitle;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Taklif: {amount} — barcha kattalar roziligi kutilmoqda'**
  String havasPending(String amount);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Rozi boʻlish'**
  String get havasConsent;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Rozi'**
  String get havasConsented;

  /// Snackbar
  ///
  /// In uz, this message translates to:
  /// **'Chegara kelishildi — endi faol.'**
  String get havasAgreed;

  /// Snackbar
  ///
  /// In uz, this message translates to:
  /// **'{name} rozi boʻldi'**
  String havasConsentSaved(String name);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Taklifni bekor qilish'**
  String get havasWithdraw;

  /// PIN dialogi
  ///
  /// In uz, this message translates to:
  /// **'{name}, shaxsiy PINʼingiz'**
  String memberPinPrompt(String name);

  /// Tahlil
  ///
  /// In uz, this message translates to:
  /// **'Isrof va saxovat (shu oy)'**
  String get analysisTitle;

  /// Tahlil qatori
  ///
  /// In uz, this message translates to:
  /// **'Obroʻ xarajatlari'**
  String get analysisOstentation;

  /// Tahlil qatori
  ///
  /// In uz, this message translates to:
  /// **'Qarz bilan qilingan havas'**
  String get analysisDebtHavas;

  /// Tahlil qatori
  ///
  /// In uz, this message translates to:
  /// **'Sadaqa — isrof emas'**
  String get analysisSadaqa;

  /// Tahlil qatori
  ///
  /// In uz, this message translates to:
  /// **'Sovgʻalar — hisobga kirmadi'**
  String get analysisGifts;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Juma shirinligi'**
  String get treatsTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Har kungi mayda havasni haftalik oilaviy quvonchga aylantiring.'**
  String get treatsHint;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Ritual qoʻshish'**
  String get treatAdd;

  /// Standart nom
  ///
  /// In uz, this message translates to:
  /// **'Juma shirinligi'**
  String get treatTitleDefault;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'{weekday} · {amount}'**
  String treatLine(String weekday, String amount);

  /// Bildirishnoma kanali
  ///
  /// In uz, this message translates to:
  /// **'Shirinlik kuni'**
  String get treatChannel;

  /// Bildirishnoma
  ///
  /// In uz, this message translates to:
  /// **'Bugun — {title}'**
  String treatNotifTitle(String title);

  /// Bildirishnoma
  ///
  /// In uz, this message translates to:
  /// **'Rejadagi quvonch kuni. Oila bilan baham koʻring!'**
  String get treatNotifBody;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nomi'**
  String get titleLabel;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Odatlar'**
  String get habitsTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Faqat statistika: qancha ketayotganini koʻrasiz, xolos.'**
  String get habitsHint;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Odat qoʻshish'**
  String get habitAdd;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'oyiga {month} · yiliga {year}'**
  String habitLine(String month, String year);

  /// Amal
  ///
  /// In uz, this message translates to:
  /// **'Kuzatishni toʻxtatish'**
  String get habitArchive;

  /// Vidjet sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Tez yozish'**
  String get widgetTitle;

  /// Vidjet: qulf
  ///
  /// In uz, this message translates to:
  /// **'Summalar ilova ochiq paytda koʻrinadi'**
  String get widgetLocked;

  /// Vidjet: shablon yo'q
  ///
  /// In uz, this message translates to:
  /// **'Ilovada shablon qoʻshing'**
  String get widgetEmpty;

  /// Snackbar
  ///
  /// In uz, this message translates to:
  /// **'Vidjetdan {count} ta xarajat yozildi'**
  String widgetRecorded(int count);

  /// Kelajagim tarixi
  ///
  /// In uz, this message translates to:
  /// **'Qutqarilgan pul'**
  String get vaultReasonRescue;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Obunalar va avtotoʻlovlar'**
  String get subscriptionsTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Har biri yiliga qancha turishini koʻring va soʻrang: kerakmi?'**
  String get subscriptionsHint;

  /// Bo'sh
  ///
  /// In uz, this message translates to:
  /// **'Hali obuna yoʻq. Telefon tarifi, kino, musiqa, ilova obunalarini qoʻshing.'**
  String get subscriptionsEmpty;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Obuna qoʻshish'**
  String get subscriptionAdd;

  /// Davr
  ///
  /// In uz, this message translates to:
  /// **'Har oy'**
  String get cycleMonthly;

  /// Davr
  ///
  /// In uz, this message translates to:
  /// **'Har yil'**
  String get cycleYearly;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'{price} · yiliga {yearly}'**
  String subscriptionLine(String price, String yearly);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Oxirgi marta ishlatilgan: {date}'**
  String subscriptionLastUsed(String date);

  /// Unutilgan obuna
  ///
  /// In uz, this message translates to:
  /// **'{days} kundan beri «ishlatdim» belgilanmagan — kerakmi?'**
  String subscriptionForgotten(int days);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Ishlatdim'**
  String get subscriptionUsed;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Bekor qildim'**
  String get subscriptionCancel;

  /// Dialog
  ///
  /// In uz, this message translates to:
  /// **'«{title}» bekor qilindimi? Yiliga {yearly} qutqariladi.'**
  String subscriptionCancelConfirm(String title, String yearly);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Bekor qilingan · yiliga {yearly} tejaladi'**
  String subscriptionCancelledLine(String yearly);

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Bekor qilinganlar'**
  String get subscriptionsCancelledHeader;

  /// Jami
  ///
  /// In uz, this message translates to:
  /// **'Faol obunalar yiliga: {amount}'**
  String subscriptionsAnnualTotal(String amount);

  /// Snackbar
  ///
  /// In uz, this message translates to:
  /// **'Belgilandi'**
  String get subscriptionUsedSaved;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Konvertlar'**
  String get envelopesTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Haftalik konvert: naqd pulni konvertga soling. Karta bilan toʻlangan xarajat ham shu konvertdan ayiriladi.'**
  String get envelopesHint;

  /// Bo'sh
  ///
  /// In uz, this message translates to:
  /// **'Konvert yoʻq. «Bozor», «Yoʻlkira», «Havas» kabi haftalik konvert oching.'**
  String get envelopesEmpty;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Konvert ochish'**
  String get envelopeAdd;

  /// Belgi
  ///
  /// In uz, this message translates to:
  /// **'Naqd konvert'**
  String get envelopeCashMode;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Qaysi xarajatlar shu konvertdan?'**
  String get envelopeCategories;

  /// Summa varag'i
  ///
  /// In uz, this message translates to:
  /// **'Haftalik limit'**
  String get envelopeLimitTitle;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'{spent} / {limit} · qoldi {left}'**
  String envelopeLine(String spent, String limit, String left);

  /// Naqd rejim
  ///
  /// In uz, this message translates to:
  /// **'Bu hafta konvertga {amount} soling'**
  String envelopePutCash(String amount);

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Konvertdan {amount} oshdi'**
  String envelopeOver(String amount);

  /// Yopish
  ///
  /// In uz, this message translates to:
  /// **'«{title}»: oʻtgan hafta ({week}) yakuni'**
  String envelopeCloseTitle(String title, String week);

  /// Summa varag'i
  ///
  /// In uz, this message translates to:
  /// **'Konvertda qancha naqd qoldi?'**
  String get envelopeClosePrompt;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Qoldiqni kiritish'**
  String get envelopeCloseAction;

  /// Snackbar
  ///
  /// In uz, this message translates to:
  /// **'Qoldiq {amount} — «Qutqarilgan pul»ga qoʻshildi'**
  String envelopeClosed(String amount);

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Qutqarilgan pul'**
  String get rescueTitle;

  /// Karta
  ///
  /// In uz, this message translates to:
  /// **'Bu hafta qutqarildi'**
  String get rescueThisWeek;

  /// Karta
  ///
  /// In uz, this message translates to:
  /// **'Shu oy qutqarildi'**
  String get rescueThisMonth;

  /// Maslahatchi savoli
  ///
  /// In uz, this message translates to:
  /// **'Bu hafta qancha qutqardingiz?'**
  String get rescueQuestion;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Havas kamaydi (bazaviy oyga nisbatan)'**
  String get rescueHavas;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Bekor qilingan obunalar'**
  String get rescueSubscriptions;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Konvert qoldiqlari'**
  String get rescueEnvelopes;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Kelajagimga oʻtkazilgan'**
  String get rescueTransferredLine;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Havasni taqqoslash uchun bazaviy oy yoʻq — birinchi oylik auditdan keyin hisoblanadi.'**
  String get rescueNoBaseline;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Bazaviy oy: {month}'**
  String rescueBaseline(String month);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Bazaviy oyni tanlash'**
  String get rescueBaselinePick;

  /// Manfiy holat (ayblamaydi)
  ///
  /// In uz, this message translates to:
  /// **'Bu davrda havasga bazaviy oydan koʻproq ketdi. Hechqisi yoʻq — har hafta yangi imkoniyat.'**
  String get rescueSpentMore;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Kelajagimga oʻtkazish — {amount}'**
  String rescueTransfer(String amount);

  /// Snackbar
  ///
  /// In uz, this message translates to:
  /// **'{amount} Kelajagimga oʻtkazildi'**
  String rescueTransferDone(String amount);

  /// Formula izohi
  ///
  /// In uz, this message translates to:
  /// **'Qutqarilgan = havas kamayishi + bekor qilingan obunalar + konvert qoldiqlari. Koʻproq sarflangan boʻlsa — 0.'**
  String get rescueFormula;

  /// Tasdiq oynasida rad etish ("Bekor qilish" bilan adashmasin)
  ///
  /// In uz, this message translates to:
  /// **'Hali yoʻq'**
  String get notNow;

  /// Favqulodda zaxira
  ///
  /// In uz, this message translates to:
  /// **'Favqulodda zaxira'**
  String get reserveTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Qora kunda qarz eshigiga yugurmaslik uchun. Hech qayerga sarflanmaydi va «oʻsmadi» deb baholanmaydi.'**
  String get reserveHint;

  /// Progress
  ///
  /// In uz, this message translates to:
  /// **'{months} / 6 oy'**
  String reserveMonths(String months);

  /// Maqsad
  ///
  /// In uz, this message translates to:
  /// **'Maqsad: {target} (oylik zarur + kerak {monthly} × 6)'**
  String reserveTarget(String target, String monthly);

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Siz kiritgan taxminiy summa boʻyicha'**
  String get reserveFromEstimate;

  /// Milestone
  ///
  /// In uz, this message translates to:
  /// **'Birinchi bosqich — 3 oy bajarildi'**
  String get reserveMilestone3;

  /// Milestone
  ///
  /// In uz, this message translates to:
  /// **'Toʻliq zaxira — 6 oy. Barakalla!'**
  String get reserveFull;

  /// Taxminiy summa so'rovi
  ///
  /// In uz, this message translates to:
  /// **'Maqsadni hisoblash uchun 3 oylik maʼlumot yetarli emas. Bir oyda zarur va kerak xarajatlarga taxminan qancha ketadi?'**
  String get reserveNeedsEstimate;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Taxminiy summani kiritish'**
  String get reserveEstimateAction;

  /// Summa varag'i
  ///
  /// In uz, this message translates to:
  /// **'Oylik zarur + kerak (taxminan)'**
  String get reserveEstimateTitle;

  /// Jamg'arma turi
  ///
  /// In uz, this message translates to:
  /// **'Oʻsadigan pul'**
  String get growthTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Inflyatsiyadan oldinda yurish uchun — faqat halol (ribosiz) yoʻnalishlarda.'**
  String get growthHint;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Kapital kiritish'**
  String get growthDeposit;

  /// Summa varag'i
  ///
  /// In uz, this message translates to:
  /// **'Oʻsadigan pulga'**
  String get growthDepositTitle;

  /// Darvoza sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Avval tayyorgarlik, keyin sarmoya'**
  String get gateTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Oʻsadigan pul va sheriklik ikki shart bajarilganda ochiladi. Taqiq yoʻq — tushuntirish bor.'**
  String get gateHint;

  /// Shart
  ///
  /// In uz, this message translates to:
  /// **'Favqulodda zaxira — 6 oylik ({months} / 6)'**
  String gateReserve(String months);

  /// Shart
  ///
  /// In uz, this message translates to:
  /// **'Foizli qarz yoʻq yoki qarzdan chiqish rejasi bor'**
  String get gateDebt;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Darvoza ochiq'**
  String get gateOpen;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Baribir kiritish'**
  String get gateBypass;

  /// Dialog
  ///
  /// In uz, this message translates to:
  /// **'Ongli qaror'**
  String get gateBypassTitle;

  /// Ogohlantirish
  ///
  /// In uz, this message translates to:
  /// **'Zaxirangiz hali toʻliq emas. Qora kun kelsa, oʻsadigan puldagi mablagʻ tez qaytmasligi mumkin va qarzga yugurishga toʻgʻri keladi. Baribir davom etasizmi?'**
  String get gateBypassWarning;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Ha, tushunaman'**
  String get gateBypassConfirm;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Darvoza ongli ravishda chetlab oʻtilgan'**
  String get gateBypassed;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Qayerdan?'**
  String get withdrawFrom;

  /// Tasdiq
  ///
  /// In uz, this message translates to:
  /// **'Bu haqiqatan favqulodda holat'**
  String get withdrawEmergency;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Favqulodda zaxira faqat qora kun uchun.'**
  String get withdrawEmergencyHint;

  /// Dialog
  ///
  /// In uz, this message translates to:
  /// **'Qayta toʻldirish rejasi'**
  String get refillTitle;

  /// Reja
  ///
  /// In uz, this message translates to:
  /// **'Har oy {monthly} — {months} oyda favqulodda zaxira tiklanadi.'**
  String refillPlan(String monthly, int months);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Tushunarli'**
  String get ok;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Narx daftari'**
  String get pricesTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Narxni yillar davomida yozib borgan odam narx-navo qanchalik oʻzgarganini aniq koʻradi. Oʻzingiz uchun muhim mahsulotlar narxini vaqti-vaqti bilan yozing — shaxsiy inflyatsiyangizni koʻrasiz.'**
  String get pricesHint;

  /// Bo'sh
  ///
  /// In uz, this message translates to:
  /// **'Savat boʻsh. Goʻsht, non, un, benzin kabi mahsulot qoʻshing.'**
  String get pricesEmpty;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Mahsulot qoʻshish'**
  String get priceItemAdd;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Birlik (kg, dona, litr)'**
  String get priceUnitLabel;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Oyiga qancha (masalan, 4 yoki 1,5)'**
  String get priceQuantityLabel;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Narx yozish'**
  String get priceAdd;

  /// Summa varag'i
  ///
  /// In uz, this message translates to:
  /// **'{name} — bugungi narx (1 {unit})'**
  String priceAddTitle(String name, String unit);

  /// Snackbar
  ///
  /// In uz, this message translates to:
  /// **'Narx yozildi'**
  String get priceSaved;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'{price} · {date}'**
  String priceLast(String price, String date);

  /// Taqqoslash
  ///
  /// In uz, this message translates to:
  /// **'{fromDate}: {from} → bugun {to} ({change})'**
  String priceChange(String fromDate, String from, String to, String change);

  /// Indeks
  ///
  /// In uz, this message translates to:
  /// **'Shaxsiy inflyatsiya (1 yil): {change}'**
  String inflationYear(String change);

  /// Indeks
  ///
  /// In uz, this message translates to:
  /// **'{date} dan beri: {change}'**
  String inflationSince(String date, String change);

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Indeks uchun bir xil mahsulotning ikki xil vaqtdagi narxi kerak.'**
  String get inflationUnknown;

  /// Streak
  ///
  /// In uz, this message translates to:
  /// **'{weeks} hafta ketma-ket narx yozildi'**
  String priceStreak(int weeks);

  /// Bildirishnoma
  ///
  /// In uz, this message translates to:
  /// **'Narx daftari'**
  String get priceReminderTitle;

  /// Bildirishnoma
  ///
  /// In uz, this message translates to:
  /// **'Bu hafta bozordagi narxlarni yozing — shaxsiy inflyatsiyangizni bilib borasiz.'**
  String get priceReminderBody;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Inflyatsiya taʼsiri'**
  String get mouseTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Yotgan pulning qadrini narx-navo sezdirmasdan kamaytiradi. Bu qoʻrqitish emas, tushuntirish.'**
  String get mouseHint;

  /// Bo'sh
  ///
  /// In uz, this message translates to:
  /// **'Hisoblash uchun «Narx daftari»ga kamida bitta mahsulot narxini yozing.'**
  String get mouseNoPrices;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Favqulodda zaxirangiz: {amount}'**
  String mouseBalance(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Bugungi narxda: {qty} {unit} {name}'**
  String mouseToday(String qty, String unit, String name);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Bir yil oldingi narxda edi: {qty} {unit}'**
  String mouseYearAgo(String qty, String unit);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Narx yiliga {rate} oshsa, {years} yildan keyin: {qty} {unit}'**
  String mouseFuture(String rate, int years, String qty, String unit);

  /// Keyingi qadam
  ///
  /// In uz, this message translates to:
  /// **'Keyingi qadam: favqulodda zaxirani 6 oylik miqdorga yetkazing — u yotgan boʻlsa ham, qora kunda sizni qarzdan asraydi.'**
  String get mouseNextReserve;

  /// Keyingi qadam
  ///
  /// In uz, this message translates to:
  /// **'Keyingi qadam: zaxira toʻliq. Ortiqcha pulni oʻsadigan qismga — halol savdo va sheriklikka yoʻnaltiring.'**
  String get mouseNextGrowth;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Kelajagimga oʻtish'**
  String get mouseOpenVault;

  /// Ter/mol/tavakkal
  ///
  /// In uz, this message translates to:
  /// **'Foyda qayerdan? (ixtiyoriy)'**
  String get incomeSourceTypeLabel;

  /// IncomeSourceType
  ///
  /// In uz, this message translates to:
  /// **'Ter — mehnat'**
  String get incomeTypeTer;

  /// IncomeSourceType
  ///
  /// In uz, this message translates to:
  /// **'Mol — savdo'**
  String get incomeTypeMol;

  /// IncomeSourceType
  ///
  /// In uz, this message translates to:
  /// **'Tavakkal — sheriklik'**
  String get incomeTypeTavakkal;

  /// IncomeSourceType
  ///
  /// In uz, this message translates to:
  /// **'Foiz (ribo)'**
  String get incomeTypeRibo;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Uchalasidan biri (ter, mol, tavakkal) boʻlmasa — bu ribo. Bunday daromad alohida koʻrsatiladi.'**
  String get incomeRiboNote;

  /// Audit
  ///
  /// In uz, this message translates to:
  /// **'Foizli daromad (alohida): {amount}'**
  String auditRiboIncome(String amount);

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Qarzlar'**
  String get debtsTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Qarz — teshik emas, yara. Hech bir qarz tashlab ketilmaydi: bank, doʻkon, qarindosh, doʻst.'**
  String get debtsHint;

  /// Jami
  ///
  /// In uz, this message translates to:
  /// **'Jami qarz: {amount}'**
  String debtsTotal(String amount);

  /// Yuk
  ///
  /// In uz, this message translates to:
  /// **'Oylik qarz yuki: {payments} — daromadning {percent}%i'**
  String debtsLoad(String payments, String percent);

  /// Yuk
  ///
  /// In uz, this message translates to:
  /// **'Oylik qarz yuki: {payments} (daromad hali yozilmagan)'**
  String debtsLoadUnknown(String payments);

  /// Bo'sh
  ///
  /// In uz, this message translates to:
  /// **'Qarz yoʻq. Alhamdulillah!'**
  String get debtsEmpty;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Olgan qarzlarim'**
  String get debtsBorrowed;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Bergan qarzlarim'**
  String get debtsLent;

  /// Jami
  ///
  /// In uz, this message translates to:
  /// **'Menga qaytishi kerak: {amount}'**
  String debtsLentTotal(String amount);

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Maqsadlarimiz'**
  String get debtsGoals;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Qarz qoʻshish'**
  String get debtAdd;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Qarz berdim'**
  String get debtLend;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Maqsad qoʻshish'**
  String get goalAdd;

  /// Summa varag'i
  ///
  /// In uz, this message translates to:
  /// **'Maqsad summasi'**
  String get goalTargetTitle;

  /// Kreditor
  ///
  /// In uz, this message translates to:
  /// **'Bank'**
  String get creditorBank;

  /// Kreditor
  ///
  /// In uz, this message translates to:
  /// **'Doʻkon (nasiya)'**
  String get creditorShop;

  /// Kreditor
  ///
  /// In uz, this message translates to:
  /// **'Qarindosh'**
  String get creditorRelative;

  /// Kreditor
  ///
  /// In uz, this message translates to:
  /// **'Doʻst'**
  String get creditorFriend;

  /// Kreditor
  ///
  /// In uz, this message translates to:
  /// **'Boshqa'**
  String get creditorOther;

  /// Belgi
  ///
  /// In uz, this message translates to:
  /// **'Foizli (ribo)'**
  String get debtInterestFlag;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Navbatdagi: {amount} · {date}'**
  String debtNext(String amount, String date);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Qoldi: {amount}'**
  String debtRemaining(String amount);

  /// Friction
  ///
  /// In uz, this message translates to:
  /// **'Toʻxta va oʻyla'**
  String get checkTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Bu taqiq emas — ongli qaror uchun uchta savol.'**
  String get checkHint;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Bu zaruratmi yoki hashamatmi?'**
  String get checkNecessity;

  /// Javob
  ///
  /// In uz, this message translates to:
  /// **'Zarurat'**
  String get checkNeed;

  /// Javob
  ///
  /// In uz, this message translates to:
  /// **'Hashamat'**
  String get checkLuxury;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Foizsiz muqobil bormi?'**
  String get checkAlternative;

  /// Javob
  ///
  /// In uz, this message translates to:
  /// **'Favqulodda zaxira'**
  String get altReserve;

  /// Javob
  ///
  /// In uz, this message translates to:
  /// **'Qarindoshdan foizsiz'**
  String get altRelative;

  /// Javob
  ///
  /// In uz, this message translates to:
  /// **'Buyum sotish'**
  String get altSell;

  /// Javob
  ///
  /// In uz, this message translates to:
  /// **'Yoʻq'**
  String get altNone;

  /// Yuk
  ///
  /// In uz, this message translates to:
  /// **'Shu qarz bilan oylik qarz yuki daromadning {percent}%iga yetadi'**
  String checkLoad(String percent);

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Kimdan?'**
  String get debtCreditorLabel;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Ismi yoki nomi'**
  String get debtCreditorName;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Asosiy summa'**
  String get debtAmountLabel;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Sababi (toʻy, mashina, roʻzgʻor…)'**
  String get debtReasonLabel;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Toʻlov rejasi'**
  String get debtScheduleLabel;

  /// Jadval turi
  ///
  /// In uz, this message translates to:
  /// **'Oʻzim yozaman'**
  String get scheduleManual;

  /// Jadval turi
  ///
  /// In uz, this message translates to:
  /// **'Teng toʻlov (bank)'**
  String get scheduleAnnuity;

  /// Jadval turi
  ///
  /// In uz, this message translates to:
  /// **'Kamayib boruvchi (bank)'**
  String get scheduleDifferentiated;

  /// Jadval turi
  ///
  /// In uz, this message translates to:
  /// **'Qatʼiy ustama'**
  String get scheduleFixedMarkup;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Muddat (oy)'**
  String get debtTermLabel;

  /// Maydon (bank krediti hisob-kitobi)
  ///
  /// In uz, this message translates to:
  /// **'Yillik stavka, %'**
  String get debtRateLabel;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Ustama summasi'**
  String get debtMarkupLabel;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Muddatidan oldin toʻlash shartlari (jarima, komissiya)'**
  String get debtEarlyTerms;

  /// Qizil ogohlantirish
  ///
  /// In uz, this message translates to:
  /// **'Bu qarzda foiz yoki ustama bor — bu ribo. Foizsiz muqobil topishga harakat qiling. Kalkulyator faqat taxminiy natija beradi.'**
  String get debtRibaWarning;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Qator qoʻshish'**
  String get manualRowAdd;

  /// Summa varag'i
  ///
  /// In uz, this message translates to:
  /// **'Toʻlov summasi'**
  String get manualRowAmount;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Reja jami asosiy summaga teng boʻlishi kerak: {planned} / {principal}'**
  String planMustCover(String planned, String principal);

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Toʻlash niyati — rejasiz qarzni saqlab boʻlmaydi.'**
  String get scheduleRequired;

  /// Karta
  ///
  /// In uz, this message translates to:
  /// **'Qarzning haqiqiy narxi'**
  String get costTitle;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Asosiy summa'**
  String get costPrincipal;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Jami toʻlanadi'**
  String get costTotal;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Ortiqcha toʻlov'**
  String get costOver;

  /// Imkoniyat narxi
  ///
  /// In uz, this message translates to:
  /// **'Bu ortiqcha toʻlov «{goal}»ning {percent}%i'**
  String costOpportunity(String goal, String percent);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Qarzni saqlash'**
  String get debtSaveAction;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Toʻlov qildim'**
  String get debtPay;

  /// Summa varag'i
  ///
  /// In uz, this message translates to:
  /// **'Toʻlov summasi'**
  String get debtPayTitle;

  /// Belgi
  ///
  /// In uz, this message translates to:
  /// **'Qoʻshimcha (muddatidan oldin) toʻlov'**
  String get debtPrepayment;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Toʻlovlar tarixi'**
  String get debtPaymentsHeader;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'toʻlangan'**
  String get debtPlanPaid;

  /// Tugma va sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Qarz tilxati'**
  String get debtReceipt;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Ikkinchi tomon va guvohlar shu telefonda ismini yozib, imzo chizadi. Bu shaxsiy hisob uchun yozuv, yuridik kafolat emas.'**
  String get receiptHint;

  /// Rol
  ///
  /// In uz, this message translates to:
  /// **'Qarz beruvchi'**
  String get roleLender;

  /// Rol
  ///
  /// In uz, this message translates to:
  /// **'Qarz oluvchi'**
  String get roleBorrower;

  /// Rol
  ///
  /// In uz, this message translates to:
  /// **'Guvoh'**
  String get roleWitness;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Guvoh qoʻshish'**
  String get witnessAdd;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Imzolash'**
  String get signAction;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Imzolangan'**
  String get signed;

  /// Imzo ekrani
  ///
  /// In uz, this message translates to:
  /// **'{role}: ismingiz va imzongiz'**
  String signTitle(String role);

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Shu yerga barmoq bilan imzo chizing'**
  String get signHere;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Tozalash'**
  String get signClear;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'PDF yaratish va ulashish'**
  String get receiptShare;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Qarz tilxati'**
  String get receiptPdfTitle;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Tomonlar va shartlar'**
  String get receiptPdfParties;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Summa'**
  String get receiptPdfAmount;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Sana'**
  String get receiptPdfDate;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Sabab'**
  String get receiptPdfReason;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Foiz / ustama'**
  String get receiptPdfMarkup;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Yoʻq — qarzi hasana'**
  String get receiptPdfNoMarkup;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Toʻlov'**
  String get receiptPdfPayment;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Imzolar'**
  String get receiptPdfSignatures;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Bu hujjat shaxsiy hisob uchun yozuv, yuridik kafolat emas.'**
  String get receiptPdfNote;

  /// Dialog
  ///
  /// In uz, this message translates to:
  /// **'Qarz berdim (qarzi hasana)'**
  String get lendTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Bergan qarzda foiz boʻlmaydi.'**
  String get lendHint;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Kimga?'**
  String get lendDebtor;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Qaytarish muddati: {date}'**
  String lendDue(String date);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Qaytardi'**
  String get lendReceive;

  /// Bosh ekran kartasi
  ///
  /// In uz, this message translates to:
  /// **'Muddati yaqin'**
  String get dueTitle;

  /// Eslatma
  ///
  /// In uz, this message translates to:
  /// **'{name} — {amount}, muddat {date}. Xushmuomalalik bilan eslatib qoʻysangiz boʻladi.'**
  String dueReceivable(String name, String amount, String date);

  /// Eslatma
  ///
  /// In uz, this message translates to:
  /// **'{name}ga toʻlov: {amount} · {date}'**
  String dueDebt(String name, String amount, String date);

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Qarzdan chiqish rejimi'**
  String get recoveryTitle;

  /// Taklif
  ///
  /// In uz, this message translates to:
  /// **'Daromadni 70 / 20 / 10 ga boʻling: roʻzgʻor, qarzni tezroq uzish va baribir «Kelajagim». Qarzdan reja bilan chiqiladi.'**
  String get recoveryOfferBody;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Rejimni yoqish'**
  String get recoveryEnable;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Yoqilgan: roʻzgʻor {needs} % · qarz {debt} % · «Kelajagim» {savings} %'**
  String recoveryActive(String needs, String debt, String savings);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Sozlash'**
  String get recoverySettings;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Qarz — oʻtmishga toʻlov, jamgʻarma — kelajakka toʻlov. Jamgʻarmasiz qarzdan chiqqan odam birinchi tashvishda yana qarz oladi.'**
  String get recoveryExplain;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Roʻzgʻor, % (majburiy qarz toʻlovlari shu ichida)'**
  String get recoveryNeeds;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Qarzni tezroq uzish, %'**
  String get recoveryDebt;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'«Kelajagim», %'**
  String get recoverySavings;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Jamgʻarma ulushi 0 boʻlmaydi — kamida 1 %.'**
  String get recoverySavingsZero;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Jami 100 % boʻlishi kerak (hozir {total} %).'**
  String recoveryTotalError(int total);

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Oylik taqsimot (oʻrtacha daromad {income})'**
  String recoveryBudgetTitle(String income);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Roʻzgʻor: {amount}'**
  String recoveryBudgetNeeds(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'shundan majburiy qarz toʻlovlari: {amount}'**
  String recoveryBudgetMandatory(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'roʻzgʻorga qoladi: {amount}'**
  String recoveryBudgetHousehold(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Qoʻshimcha qarz toʻlovi: {amount}'**
  String recoveryBudgetDebt(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'«Kelajagim»: {amount}'**
  String recoveryBudgetSavings(String amount);

  /// Ogohlantirish
  ///
  /// In uz, this message translates to:
  /// **'Majburiy toʻlovlar roʻzgʻor ulushidan oshib ketdi — ulushlarni qayta koʻrib chiqing.'**
  String get recoveryMandatoryOver;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Daromad hali yozilmagan — summalar daromad kiritilgach chiqadi.'**
  String get recoveryNoIncome;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Saqlash va yoqish'**
  String get recoverySaveEnable;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Rejimdan chiqish'**
  String get recoveryDisable;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Standart 70 / 20 / 10'**
  String get recoveryStandard;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Alhamdulillah, qarzsiz!'**
  String get freedShareTitle;

  /// Taklif
  ///
  /// In uz, this message translates to:
  /// **'Hamma qarz yopildi — rejim odatiyga qaytdi. Boʻshagan {percent} % ni favqulodda zaxira va oʻsadigan pulga yoʻnaltiramizmi?'**
  String freedShareBody(String percent);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Ha, «Kelajagim»ga'**
  String get freedShareAccept;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Qarzdan chiqish rejasi'**
  String get payoffTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Taxminiy hisob: bank grafigi, jarima va komissiya shartnomaga bogʻliq.'**
  String get payoffEstimate;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Har oy qoʻshimcha: {amount}'**
  String payoffMonthly(String amount);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Bir martalik: {amount}'**
  String payoffLump(String amount);

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Har oy qoʻshimcha toʻlov'**
  String get payoffMonthlyTitle;

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Bir martalik qoʻshimcha toʻlov'**
  String get payoffLumpTitle;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Qoʻshimcha toʻlov manbalari'**
  String get payoffSources;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Ulush ({percent} %): oyiga {amount}'**
  String payoffSourceShare(String percent, String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Ulush: «Qarzdan chiqish» rejimi yoqilganda daromadning 20 %i'**
  String get payoffSourceShareOff;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Qutqarilgan pul (bu hafta): {amount}'**
  String payoffSourceRescue(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Sotilgan buyumlar: {amount}'**
  String payoffSourceSold(String amount);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Qarzga'**
  String get payoffApply;

  /// Xabar
  ///
  /// In uz, this message translates to:
  /// **'{amount} «{name}» qarziga qoʻshimcha toʻlov qilindi.'**
  String payoffApplied(String amount, String name);

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Yopish tartibi'**
  String get payoffOrder;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Avval foizli (eng qimmati), keyin foizsiz — muddati yaqini. Tartibni oʻzgartirish mumkin.'**
  String get payoffOrderHint;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Standart tartib'**
  String get payoffOrderReset;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Yuqoriga'**
  String get payoffUp;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Pastga'**
  String get payoffDown;

  /// Natija
  ///
  /// In uz, this message translates to:
  /// **'Qarzsiz kun: {base} → {plan}'**
  String payoffDebtFree(String base, String plan);

  /// Natija
  ///
  /// In uz, this message translates to:
  /// **'{months} oy erta'**
  String payoffEarly(int months);

  /// Natija
  ///
  /// In uz, this message translates to:
  /// **'{amount} tejaladi'**
  String payoffSaved(String amount);

  /// Natija
  ///
  /// In uz, this message translates to:
  /// **'Muddat oʻzgarmaydi'**
  String get payoffSameEnd;

  /// Natija
  ///
  /// In uz, this message translates to:
  /// **'Jarima / komissiya: {amount}'**
  String payoffFees(String amount);

  /// Ustun
  ///
  /// In uz, this message translates to:
  /// **'Odatiy'**
  String get payoffBaseline;

  /// Ustun
  ///
  /// In uz, this message translates to:
  /// **'Qoʻshimcha bilan'**
  String get payoffAccelerated;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Grafiklarni koʻrish'**
  String get payoffShowTable;

  /// Natija
  ///
  /// In uz, this message translates to:
  /// **'{months} oy'**
  String payoffMonths(int months);

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Muddatidan oldin toʻlash jarimasi, %'**
  String get payoffFeeLabel;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Jarima: {percent} %'**
  String payoffFeeValue(String percent);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Jarima yoʻq'**
  String get payoffNoFee;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Qarzsiz kun: {date}'**
  String debtFreeOn(String date);

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Yelkadoshlar'**
  String get contributorsTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Qarzni oila bilan birga toʻlash: kim qancha toʻlayotganini yozib boring.'**
  String get contributorsHint;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Yelkadosh qoʻshish'**
  String get contributorAdd;

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Oylik ulushi (ixtiyoriy)'**
  String get contributorShareTitle;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Oyiga {share} · toʻlagan {paid}'**
  String contributorLine(String share, String paid);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Toʻlagan: {paid}'**
  String contributorPaid(String paid);

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Kim toʻladi?'**
  String get whoPaid;

  /// Variant
  ///
  /// In uz, this message translates to:
  /// **'Oilaning oʻzi'**
  String get whoPaidFamily;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'jarima {amount}'**
  String debtFeeNote(String amount);

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Alhamdulillah! Qarz yopildi'**
  String get debtClosedTitle;

  /// Matn
  ///
  /// In uz, this message translates to:
  /// **'«{name}» qarzi toʻliq uzildi. Bitta majburiyatdan ozod boʻldingiz.'**
  String debtClosedBody(String name);

  /// Taklif
  ///
  /// In uz, this message translates to:
  /// **'Endi har oy {amount} boʻshaydi. Uni «Kelajagim»ga yoʻnaltiramizmi?'**
  String debtClosedFreed(String amount);

  /// Xabar
  ///
  /// In uz, this message translates to:
  /// **'«Kelajagim» ulushi oshirildi.'**
  String get debtClosedRedirected;

  /// Xabar
  ///
  /// In uz, this message translates to:
  /// **'Daromad yozilmagani uchun ulush avtomatik oshirilmaydi — «Kelajagim» sozlamasida oʻzingiz oshiring.'**
  String get debtClosedNoIncome;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Rahmat'**
  String get debtClosedDone;

  /// Xabar
  ///
  /// In uz, this message translates to:
  /// **'Barcha qarzlar yopildi — «Qarzdan chiqish» rejimi odatiyga qaytdi.'**
  String get modeReturned;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Sotiladigan buyumlar'**
  String get sellablesTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Uyda 6 oydan beri ishlatilmayotgan qimmatbaho buyumlar. Sotilgan puli bir bosishda qarzga yoʻnaltiriladi.'**
  String get sellablesHint;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Buyum qoʻshish'**
  String get sellableAdd;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Buyum nomi'**
  String get sellableName;

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Taxminiy narxi'**
  String get sellableEstimate;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Sotuvda · taxminan {amount}'**
  String sellableListed(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Sotildi: {amount}'**
  String sellableSold(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Sotildi: {amount} · «{name}» qarziga'**
  String sellableAppliedTo(String amount, String name);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Sotildi'**
  String get sellableMarkSold;

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Sotilgan narxi'**
  String get sellableSoldPrice;

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Qaysi qarzga?'**
  String get sellableChooseDebt;

  /// Bo'sh
  ///
  /// In uz, this message translates to:
  /// **'Hali buyum yoʻq.'**
  String get sellablesEmpty;

  /// Karta
  ///
  /// In uz, this message translates to:
  /// **'Qarzsiz kun: {date}'**
  String homeDebtFree(String date);

  /// Karta
  ///
  /// In uz, this message translates to:
  /// **'Qolgan qarz: {amount} · {months} oy'**
  String homeDebtFreeBody(String amount, int months);

  /// Karta
  ///
  /// In uz, this message translates to:
  /// **'Reja boʻyicha: {date}'**
  String homeDebtFreePlan(String date);

  /// Karta
  ///
  /// In uz, this message translates to:
  /// **'«Qarzdan chiqish» rejimini yoqing — 70 / 20 / 10'**
  String get homeRecoveryOffer;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Marosimlar'**
  String get ceremoniesTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Toʻy va marosimni oldindan, qarzsiz rejalash: stsenariylarni taqqoslang, oila bilan maslahatlashing.'**
  String get ceremoniesHint;

  /// Bo'sh
  ///
  /// In uz, this message translates to:
  /// **'Hali reja yoʻq.'**
  String get ceremoniesEmpty;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Reja tuzish'**
  String get ceremonyAdd;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nomi (masalan, oʻgʻlimning toʻyi)'**
  String get ceremonyNameLabel;

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Marosim turi'**
  String get ceremonyTypeTitle;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Toʻy'**
  String get ceremonyTypeToy;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Beshik toʻy'**
  String get ceremonyTypeBeshik;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Sunnat toʻy'**
  String get ceremonyTypeSunnat;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Maʼraka'**
  String get ceremonyTypeMaraka;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Boshqa'**
  String get ceremonyTypeOther;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Qoralama'**
  String get ceremonyStatusDraft;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Oilada muhokama qilindi'**
  String get ceremonyStatusDiscussed;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Tasdiqlandi'**
  String get ceremonyStatusConfirmed;

  /// Standart stsenariy nomi
  ///
  /// In uz, this message translates to:
  /// **'Asosiy'**
  String get ceremonyFirstScenario;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Sana: {date}'**
  String ceremonyDate(String date);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Sanasi belgilanmagan'**
  String get ceremonyDateNone;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'{count} kishi'**
  String ceremonyGuests(int count);

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Mehmonlar soni'**
  String get ceremonyGuestsTitle;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Stsenariy qoʻshish'**
  String get scenarioAdd;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Stsenariy nomi (masalan, 1 kunlik, 100 kishi, ixcham)'**
  String get scenarioName;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Stsenariylar taqqoslashi'**
  String get scenarioCompare;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Tanlash'**
  String get scenarioSelect;

  /// Belgi
  ///
  /// In uz, this message translates to:
  /// **'Tanlangan'**
  String get scenarioSelected;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Oʻchirish'**
  String get scenarioRemove;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Jami: {amount}'**
  String scenarioTotal(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Qarz: {amount}'**
  String scenarioDebt(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Qarzsiz'**
  String get scenarioNoDebt;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Qarz {months} oyda uziladi ({date} gacha)'**
  String scenarioPayoff(int months, String date);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'ortiqcha toʻlov {amount}'**
  String scenarioPayoffInterest(String amount);

  /// Ogohlantirish
  ///
  /// In uz, this message translates to:
  /// **'Bu toʻlov bilan qarz hech qachon tugamaydi'**
  String get scenarioPayoffNever;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Toʻlash muddati uchun «qarzni oyiga» summasini kiriting'**
  String get scenarioPayoffUnknown;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Bu pulga: «{goal}» — {percent} %'**
  String scenarioGoal(String goal, String percent);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Qator qoʻshish'**
  String get lineAdd;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nomi (osh, xonanda, sarpo…)'**
  String get lineTitle;

  /// Variant
  ///
  /// In uz, this message translates to:
  /// **'Bir martalik'**
  String get lineOneTime;

  /// Variant
  ///
  /// In uz, this message translates to:
  /// **'Kishi boshiga'**
  String get linePerGuest;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'{price} × {guests} = {total}'**
  String linePerGuestValue(String price, int guests, String total);

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Summa'**
  String get lineAmountTitle;

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Kishi boshiga narx'**
  String get linePriceTitle;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Qayerdan moliyalanadi?'**
  String get lineSourceTitle;

  /// Manba
  ///
  /// In uz, this message translates to:
  /// **'Jamgʻarma'**
  String get fundingSavings;

  /// Manba
  ///
  /// In uz, this message translates to:
  /// **'Oila hissasi'**
  String get fundingFamily;

  /// Manba
  ///
  /// In uz, this message translates to:
  /// **'Kutilayotgan toʻyona'**
  String get fundingGifts;

  /// Manba
  ///
  /// In uz, this message translates to:
  /// **'Qarz'**
  String get fundingDebt;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Qarzni oyiga: {amount}'**
  String ceremonyDebtTerms(String amount);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Qarzni oyiga qancha toʻlay olasiz?'**
  String get ceremonyDebtTermsUnset;

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Qarzni oyiga toʻlash'**
  String get ceremonyDebtMonthlyTitle;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Buni qarzsiz qanday oʻtkazamiz?'**
  String get discussionTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Rejada qarz bor. Tasdiqlashdan oldin oila birga oʻtirib, shu savollarni muhokama qiladi va har bir katta aʼzo belgi qoʻyadi.'**
  String get discussionHint;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Mehmonlar sonini kamaytirsak boʻladimi?'**
  String get discussionQ1;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Bir kunlik, ixcham marosim yetarli emasmi?'**
  String get discussionQ2;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Qaysi xarajatni jamgʻarma yoki oila hissasidan qoplay olamiz?'**
  String get discussionQ3;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Qarzni kim, qachon va qanday toʻlaydi?'**
  String get discussionQ4;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Shu pulga yosh oila uchun nima qilish mumkin edi?'**
  String get discussionQ5;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Muhokama qildim'**
  String get discussionMark;

  /// Belgi
  ///
  /// In uz, this message translates to:
  /// **'Belgilandi'**
  String get discussionMarked;

  /// Xabar
  ///
  /// In uz, this message translates to:
  /// **'Oila muhokama qildi — endi tasdiqlash mumkin.'**
  String get discussionDone;

  /// Xabar
  ///
  /// In uz, this message translates to:
  /// **'{name} belgi qoʻydi.'**
  String discussionMarkedSnack(String name);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Rejani tasdiqlash'**
  String get ceremonyConfirm;

  /// Xabar
  ///
  /// In uz, this message translates to:
  /// **'Reja tasdiqlandi.'**
  String get ceremonyConfirmedSnack;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Rejada qarz bor — avval oilaviy muhokama.'**
  String get ceremonyConfirmBlocked;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Qayta ochish'**
  String get ceremonyReopen;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Reja tasdiqlangan. Oʻzgartirish uchun qayta oching.'**
  String get ceremonyLocked;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Toʻyona oʻrniga jamgʻarma'**
  String get giftTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Yosh oila uchun maqsad: mehmonlar dabdaba oʻrniga shu jamgʻarmaga hissa qoʻshadi. Hissalar qoʻlda yoziladi.'**
  String get giftHint;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Maqsad ochish'**
  String get giftCreate;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Maqsad nomi (masalan, yosh oilaga uy)'**
  String get giftGoalName;

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Maqsad summasi'**
  String get giftTargetTitle;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Yigʻildi: {collected} / {target}'**
  String giftProgress(String collected, String target);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Hissa yozish'**
  String get giftAddContribution;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Kim qoʻshdi?'**
  String get giftContributorName;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Ulashish'**
  String get giftShare;

  /// Ulashish matni
  ///
  /// In uz, this message translates to:
  /// **'{title}: toʻyona oʻrniga yosh oilaning «{goal}» maqsadiga hissa qoʻshing. Maqsad: {target}, yigʻildi: {collected}.'**
  String giftShareText(
    String title,
    String goal,
    String target,
    String collected,
  );

  /// Kartochka
  ///
  /// In uz, this message translates to:
  /// **'El uch kun gapiradi, toʻrtinchi kuni oʻz dardi bilan ovora boʻladi.'**
  String get pressure1;

  /// Kartochka
  ///
  /// In uz, this message translates to:
  /// **'Yosh oilaga eng katta sovgʻa — qarzsiz boshlangan hayot.'**
  String get pressure2;

  /// Kartochka
  ///
  /// In uz, this message translates to:
  /// **'Bir kunlik dabdaba uchun yillab qarz toʻlash — oʻzingiz zimmangizga olgan ogʻir yuk.'**
  String get pressure3;

  /// Imzolovchi roli
  ///
  /// In uz, this message translates to:
  /// **'Sherik'**
  String get roleParty;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Sheriklik'**
  String get pnTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Bir odamning puli bekor yotadi, boshqasining hunari pulsizlikdan bekor turadi. Sheriklik — sadaqa ham, qarz ham emas: tavakkal boʻlishiladi.'**
  String get pnHint;

  /// Bo'sh
  ///
  /// In uz, this message translates to:
  /// **'Hali sheriklik yoʻq.'**
  String get pnEmpty;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Shartnoma tuzish'**
  String get pnNew;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Mudoraba'**
  String get pnTypeMudaraba;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Musharaka'**
  String get pnTypeMusharaka;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Kapital bir tomondan, mehnat ikkinchi tomondan. Moliyaviy zarar kapital egasida, mehnat egasi mehnatidan ayriladi.'**
  String get pnTypeMudarabaHint;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Har ikki tomon kapital kiritadi. Zarar kiritilgan kapitalga mutanosib boʻlinadi.'**
  String get pnTypeMusharakaHint;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Imzolanmagan'**
  String get pnStatusDraft;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Imzolangan'**
  String get pnStatusSigned;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Faol'**
  String get pnStatusActive;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Yopilgan'**
  String get pnStatusClosed;

  /// Rol
  ///
  /// In uz, this message translates to:
  /// **'Kapital egasi'**
  String get pnRoleProvider;

  /// Rol
  ///
  /// In uz, this message translates to:
  /// **'Mehnat egasi'**
  String get pnRoleWorker;

  /// Rol
  ///
  /// In uz, this message translates to:
  /// **'Kapital va mehnat'**
  String get pnRoleBoth;

  /// Davr
  ///
  /// In uz, this message translates to:
  /// **'Har oy'**
  String get pnPeriodMonthly;

  /// Davr
  ///
  /// In uz, this message translates to:
  /// **'Har chorak'**
  String get pnPeriodQuarterly;

  /// Davr
  ///
  /// In uz, this message translates to:
  /// **'Har yil'**
  String get pnPeriodYearly;

  /// Kapital
  ///
  /// In uz, this message translates to:
  /// **'Pul'**
  String get pnCapitalCash;

  /// Kapital
  ///
  /// In uz, this message translates to:
  /// **'Uskuna'**
  String get pnCapitalEquipment;

  /// Qadam
  ///
  /// In uz, this message translates to:
  /// **'Tur'**
  String get pnStepType;

  /// Qadam
  ///
  /// In uz, this message translates to:
  /// **'Tomonlar'**
  String get pnStepParties;

  /// Qadam
  ///
  /// In uz, this message translates to:
  /// **'Kapital'**
  String get pnStepCapital;

  /// Qadam
  ///
  /// In uz, this message translates to:
  /// **'Foyda va zarar'**
  String get pnStepProfit;

  /// Qadam
  ///
  /// In uz, this message translates to:
  /// **'Shartlar'**
  String get pnStepTerms;

  /// Qadam
  ///
  /// In uz, this message translates to:
  /// **'Koʻrib chiqish'**
  String get pnStepReview;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nomi (masalan, tikuvchilik sexi)'**
  String get pnName;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Mening rolim'**
  String get pnMyRole;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Mening ismim'**
  String get pnMyName;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Sherigim ismi'**
  String get pnPartnerName;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Sherigim roli'**
  String get pnPartnerRole;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'{name}: {amount}'**
  String pnCapitalOf(String name, String amount);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Kapital qoʻshish'**
  String get pnCapitalAdd;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nomi (masalan, tikuv mashinasi)'**
  String get pnCapitalTitle;

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Narxi yoki summasi'**
  String get pnCapitalAmount;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Kapital kiritmaydi (mehnat)'**
  String get pnCapitalNone;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Foyda qanday boʻlinadi?'**
  String get pnProfitMethod;

  /// Variant
  ///
  /// In uz, this message translates to:
  /// **'Sof foydaning foizi'**
  String get pnProfitPercent;

  /// Variant
  ///
  /// In uz, this message translates to:
  /// **'Qatʼiy summa (oyiga …)'**
  String get pnProfitFixed;

  /// Variant
  ///
  /// In uz, this message translates to:
  /// **'Zarar boʻlsa ham vaʼda qilingan foyda'**
  String get pnProfitGuaranteed;

  /// Tushuntirish
  ///
  /// In uz, this message translates to:
  /// **'Bu sheriklik emas — ribo yoki qarz. Sheriklikda foyda faqat sof foydaning foizi boʻladi: foyda boʻlmasa — hech kim olmaydi, zarar boʻlsa — qoidaga koʻra boʻlinadi.'**
  String get pnNotPartnership;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Mening ulushim, %'**
  String get pnMyShare;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Sherigim ulushi: {percent} %'**
  String pnPartnerShare(String percent);

  /// Qoida
  ///
  /// In uz, this message translates to:
  /// **'Zarar: moliyaviy zarar kapital egasida; mehnat egasi mehnatidan ayriladi. Istisno — beparvolik yoki shart buzilishi (izoh bilan).'**
  String get pnLossRuleMudaraba;

  /// Qoida
  ///
  /// In uz, this message translates to:
  /// **'Zarar kapitalga mutanosib: {shares}.'**
  String pnLossRuleMusharaka(String shares);

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Muddat (oy)'**
  String get pnTermMonths;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Hisobot davriyligi'**
  String get pnReportPeriod;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Muddat tugaganda nima boʻladi?'**
  String get pnEndTerms;

  /// Standart
  ///
  /// In uz, this message translates to:
  /// **'Hisob-kitob qilinadi: kapital va uskunalar egasiga qaytadi, oxirgi foyda ulushlar boʻyicha boʻlinadi.'**
  String get pnEndTermsDefault;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nizolar qanday hal qilinadi?'**
  String get pnDisputeTerms;

  /// Standart
  ///
  /// In uz, this message translates to:
  /// **'Avval oʻzaro maslahat, soʻng guvohlar va ishonchli oqsoqol ishtirokida.'**
  String get pnDisputeTermsDefault;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Guvohlar'**
  String get pnWitnesses;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Guvoh qoʻshish'**
  String get pnWitnessAdd;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Keyingi'**
  String get pnNext;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Orqaga'**
  String get pnBack;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Shartnomani yaratish'**
  String get pnCreate;

  /// Ogohlantirish
  ///
  /// In uz, this message translates to:
  /// **'Shablon yurist va ulamo tomonidan hali tekshirilmagan — shaxsiy hisob uchun yozuv, yuridik kafolat emas.'**
  String get pnTemplatePending;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Shartnoma, {version}-versiya'**
  String pnContractVersion(int version);

  /// Ogohlantirish
  ///
  /// In uz, this message translates to:
  /// **'Shartnoma oʻzgardi — hamma qayta imzolashi kerak.'**
  String get pnResign;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Shartnomani oʻzgartirish'**
  String get pnAmend;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Yangi muddat (oy)'**
  String get pnAmendTerm;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'PDF yaratish va ulashish'**
  String get pnPdf;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Sheriklik shartnomasi'**
  String get pnPdfTitle;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Tomonlar va kapital'**
  String get pnPdfParties;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Shartlar'**
  String get pnPdfTerms;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Foyda ulushi'**
  String get pnPdfShare;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Kapital'**
  String get pnPdfCapital;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Rol'**
  String get pnPdfRole;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Ism'**
  String get pnPdfName;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Turi'**
  String get pnPdfType;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Zarar qoidasi'**
  String get pnPdfLoss;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Sheriklik — sadaqa ham, qarz ham emas: foyda faqat sof foydaning foizi, oldindan vaʼda qilingan daromad yoʻq. Shaxsiy hisob uchun yozuv, yuridik kafolat emas.'**
  String get pnPdfNote;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Versiya'**
  String get pnPdfVersion;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Zarar boʻlsa kim koʻtaradi?'**
  String get pnLossCalc;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Zarar summasi: {amount}'**
  String pnLossAmount(String amount);

  /// Belgi
  ///
  /// In uz, this message translates to:
  /// **'Mehnat egasining beparvoligi yoki shart buzilishi'**
  String get pnNegligence;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Izoh (nima boʻldi?)'**
  String get pnNegligenceNote;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Beparvolik izohsiz qabul qilinmaydi.'**
  String get pnNegligenceNoteRequired;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Sheriklikni boshlash'**
  String get pnActivate;

  /// Xabar
  ///
  /// In uz, this message translates to:
  /// **'Sheriklik faol.'**
  String get pnActivated;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Boshlashdan oldin shartnomani hamma imzolaydi.'**
  String get pnSignFirst;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Kapital kiritish — tayyorgarlik darvozasi'**
  String get pnGateTitle;

  /// Ogohlantirish
  ///
  /// In uz, this message translates to:
  /// **'Darvoza yopiq: avval 6 oylik favqulodda zaxira va qarz rejasi. Baribir kiritsangiz — bu ongli qaror sifatida yoziladi.'**
  String get pnGateClosed;

  /// Xabar
  ///
  /// In uz, this message translates to:
  /// **'Darvoza ochiq — kapital kiritishga tayyorsiz.'**
  String get pnGateOpen;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Baribir boshlash'**
  String get pnGateBypass;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Bu qarz emas'**
  String get pnNotDebtTitle;

  /// Tushuntirish
  ///
  /// In uz, this message translates to:
  /// **'Mudorabada siz olgan kapital qarz emas: uni qaytarish majburiyati yoʻq, zarar kapital egasida (beparvolik bundan mustasno). Foyda kelishilgan ulushda boʻlinadi. Buni oila bilan maslahatlashing.'**
  String get pnNotDebtBody;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Tushundim'**
  String get pnNotDebtAck;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Oilaviy rozilik'**
  String get pnConsentTitle;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Roziman'**
  String get pnConsent;

  /// Belgi
  ///
  /// In uz, this message translates to:
  /// **'Rozi'**
  String get pnConsented;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Ulushni bosqichma-bosqich sotib olish'**
  String get pnBuyoutTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Mehnat egasi foyda ulushidan oz-ozdan toʻlab, kapital egasining ulushini sotib oladi va oxirida mustaqil boʻladi.'**
  String get pnBuyoutHint;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Oyiga: {amount}'**
  String pnBuyoutMonthly(String amount);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Oylik toʻlovni belgilash'**
  String get pnBuyoutSet;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Kapital egasining qolgan ulushi: {amount} ({percent} %)'**
  String pnBuyoutRemaining(String amount, String percent);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Toʻliq sotib olinadi: {date} ({months} oy)'**
  String pnBuyoutEnd(String date, int months);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Toʻlov yozish'**
  String get pnBuyoutPay;

  /// Buyout to'lovlari kartasi sarlavhasi (kassa daftaridan alohida)
  ///
  /// In uz, this message translates to:
  /// **'Buyout toʻlovlari'**
  String get pnBuyoutHistory;

  /// Buyout to'lovlari yo'q bo'lganda
  ///
  /// In uz, this message translates to:
  /// **'Hali toʻlov yoʻq.'**
  String get pnBuyoutNone;

  /// Bitta buyout to'lovi qatori
  ///
  /// In uz, this message translates to:
  /// **'{amount} — {date}'**
  String pnBuyoutPaidRow(String amount, String date);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Sheriklikni yopish'**
  String get pnClose;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Ulushlar yigʻindisi 100 % boʻlishi kerak.'**
  String get pnErrorShares;

  /// Imzolagan tomon qayta imzolashga urinsa
  ///
  /// In uz, this message translates to:
  /// **'Bu tomon allaqachon imzolagan.'**
  String get agAlreadySigned;

  /// Xarajat suring bilan oʻchirilgandan keyingi xabar
  ///
  /// In uz, this message translates to:
  /// **'Xarajat oʻchirildi.'**
  String get expenseDeleted;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Bu tomon allaqachon imzolagan.'**
  String get pnAlreadySigned;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Musharakada har ikki tomon kapital kiritadi.'**
  String get pnErrorCapital;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Mudorabada kapital bir tomondan, mehnat ikkinchi tomondan boʻladi.'**
  String get pnErrorRoles;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Kapital egasi kiritadigan pul yoki uskunani qoʻshing.'**
  String get pnErrorNoCapital;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Kassa daftari'**
  String get ledgerTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Biznes puli uy pulidan alohida: uy byudjetiga faqat taqsimlangan ulushingiz tushadi.'**
  String get ledgerHint;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Daftarni mehnat egasi yuritadi; siz uni faqat koʻrasiz va davr hisobotini olasiz.'**
  String get ledgerReadOnly;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Ochiq davr: {start} — bugun'**
  String ledgerOpenPeriod(String start);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Kirim: {amount}'**
  String ledgerIncome(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Xarajat: {amount}'**
  String ledgerExpense(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Sof foyda: {amount}'**
  String ledgerNet(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Zarar: {amount}'**
  String ledgerLoss(String amount);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Yozuv qoʻshish'**
  String get ledgerAdd;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Kirim (buyurtma)'**
  String get ledgerKindIncome;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Xarajat'**
  String get ledgerKindExpense;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Fors-major'**
  String get ledgerKindForce;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Tuzatish'**
  String get ledgerKindCorrection;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nima uchun? (buyurtma, mato, ish haqi…)'**
  String get ledgerEntryTitle;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Izoh (dalil, tafsilot)'**
  String get ledgerNote;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Chek rasmi'**
  String get ledgerAttach;

  /// Belgi
  ///
  /// In uz, this message translates to:
  /// **'Rasm biriktirildi'**
  String get ledgerAttached;

  /// Belgi
  ///
  /// In uz, this message translates to:
  /// **'Foydani kamaytiradi'**
  String get ledgerCorrectionMinus;

  /// Belgi
  ///
  /// In uz, this message translates to:
  /// **'Yopilgan davr — oʻzgarmaydi'**
  String get ledgerLocked;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Davrni yopish va taqsimlash'**
  String get ledgerClose;

  /// Tasdiq
  ///
  /// In uz, this message translates to:
  /// **'Davr yopilgach yozuvlar oʻzgarmaydi; tuzatish faqat keyingi davrda yangi yozuv bilan. Yopamizmi?'**
  String get ledgerCloseConfirm;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Yopilgan davrlar'**
  String get ledgerClosedTitle;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'{start} — {end}'**
  String ledgerPeriod(String start, String end);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'{name}: {amount}'**
  String ledgerShareLine(String name, String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Buyout: {amount}'**
  String ledgerBuyoutLine(String amount);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Hisobot PDF'**
  String get ledgerReport;

  /// Bo'sh
  ///
  /// In uz, this message translates to:
  /// **'Hali yozuv yoʻq.'**
  String get ledgerEmpty;

  /// Xabar
  ///
  /// In uz, this message translates to:
  /// **'Davr yopildi. Ulushingiz uy daromadiga yozildi: {amount}'**
  String ledgerClosedSnack(String amount);

  /// Xabar
  ///
  /// In uz, this message translates to:
  /// **'Davr yopildi.'**
  String get ledgerClosedPlain;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Sheriklik davr hisoboti'**
  String get ledgerReportTitle;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Taqsimot'**
  String get ledgerReportDistribution;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Yozuvlar'**
  String get ledgerReportEntries;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Kapital egasining qolgan ulushi'**
  String get ledgerReportBuyout;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Hisobot sherikka shaffoflik uchun: kirim, xarajat, foyda va taqsimot shu daftar yozuvlaridan.'**
  String get ledgerReportNote;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Kassa daftari'**
  String get ledgerOpenButton;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Hunardan ishga'**
  String get ideasTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Oiladagi bekor yotgan hunarlar — tikuvchilik, pazandachilik, taʼmirlash, til bilish… Hisob-kitobni uch marta qiling.'**
  String get ideasHint;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Hunarlar'**
  String get skillsTitle;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Hunar qoʻshish'**
  String get skillAdd;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Hunar (masalan, tikuvchilik)'**
  String get skillName;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Gʻoyalar'**
  String get ideasList;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Gʻoya hisobi'**
  String get ideaAdd;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Gʻoya (masalan, uyda tikuv sexi)'**
  String get ideaName;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Boshlangʻich xarajat (CAPEX)'**
  String get ideaCapex;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Band qoʻshish'**
  String get ideaCapexAdd;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nima? (overlok, bichish stoli, mato…)'**
  String get ideaCapexTitle;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Jami: {amount}'**
  String ideaCapexTotal(String amount);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Oylik kirim (oʻrtacha): {amount}'**
  String ideaIncome(String amount);

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Oylik xarajat: {amount}'**
  String ideaExpense(String amount);

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Oʻrtacha oylik kirim'**
  String get ideaIncomeTitle;

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Oylik xarajat'**
  String get ideaExpenseTitle;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Sheriklikda mening ulushim, %'**
  String get ideaShare;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Hisoblash va saqlash'**
  String get ideaSave;

  /// Stsenariy
  ///
  /// In uz, this message translates to:
  /// **'Pessimistik'**
  String get scenarioPessimistic;

  /// Stsenariy
  ///
  /// In uz, this message translates to:
  /// **'Oʻrtacha'**
  String get scenarioBase;

  /// Stsenariy
  ///
  /// In uz, this message translates to:
  /// **'Optimistik'**
  String get scenarioOptimistic;

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Kirim {income} · xarajat {expense} · foyda {net}'**
  String ideaScenarioLine(String income, String expense, String net);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Ulushdan keyin: {amount}'**
  String ideaMyNet(String amount);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Qoplanadi: {months} oyda'**
  String ideaPayback(int months);

  /// Qator
  ///
  /// In uz, this message translates to:
  /// **'Qoplanmaydi — xarajat yoki narxni qayta koʻring'**
  String get ideaNoPayback;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Shartnoma qoralamasi'**
  String get ideaToContract;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Taklifni tekshirish'**
  String get offerTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Tavakkalsiz foyda vaʼda qilinsa — u yerda yo ribo, yo firibgarlik bor.'**
  String get offerHint;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Taklif (masalan, «signal guruhi»)'**
  String get offerName;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Foyda oldindan vaʼda qilinganmi (zarar boʻlsa ham)?'**
  String get offerQGuaranteed;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Zarar boʻlsa, u boʻlishiladimi?'**
  String get offerQLoss;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Orqasida real mol yoki ish bormi?'**
  String get offerQReal;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Yangi odam jalb qilish talab qilinadimi?'**
  String get offerQRecruit;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'«Hozir qaror qiling» deb shoshiltirishyaptimi?'**
  String get offerQPressure;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Yozma shartnoma bormi?'**
  String get offerQContract;

  /// Javob
  ///
  /// In uz, this message translates to:
  /// **'Ha'**
  String get offerYes;

  /// Javob
  ///
  /// In uz, this message translates to:
  /// **'Yoʻq'**
  String get offerNo;

  /// Javob
  ///
  /// In uz, this message translates to:
  /// **'Bilmayman'**
  String get offerUnknown;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Baholash'**
  String get offerCheck;

  /// Natija
  ///
  /// In uz, this message translates to:
  /// **'Yashil: jiddiy xavf belgisi topilmadi. Baribir shartnomani oʻqing va maslahatlashing.'**
  String get offerGreen;

  /// Natija
  ///
  /// In uz, this message translates to:
  /// **'Sariq: aniqlashtiring — quyidagi belgilar shubhali.'**
  String get offerYellow;

  /// Natija
  ///
  /// In uz, this message translates to:
  /// **'Qizil: bu yo ribo, yo firibgarlik belgisi. Pul bermang.'**
  String get offerRed;

  /// Bayroq
  ///
  /// In uz, this message translates to:
  /// **'Tavakkalsiz foyda vaʼdasi — sheriklik emas: yo ribo, yo firibgarlik.'**
  String get offerFlagGuaranteed;

  /// Bayroq
  ///
  /// In uz, this message translates to:
  /// **'Zarar boʻlishilmasa — bu sheriklik emas, qarz yoki ribo.'**
  String get offerFlagLoss;

  /// Bayroq
  ///
  /// In uz, this message translates to:
  /// **'Real mol yoki ish boʻlmasa, «foyda» yangi kelganlar pulidan toʻlanadi.'**
  String get offerFlagReal;

  /// Bayroq
  ///
  /// In uz, this message translates to:
  /// **'Yangi aʼzo jalb qilish talabi — piramida belgisi.'**
  String get offerFlagRecruit;

  /// Bayroq
  ///
  /// In uz, this message translates to:
  /// **'Shoshiltirish — oʻylashga vaqt bermaslik usuli.'**
  String get offerFlagPressure;

  /// Bayroq
  ///
  /// In uz, this message translates to:
  /// **'Yozma shartnomasiz kelishuvni himoya qilib boʻlmaydi.'**
  String get offerFlagContract;

  /// Bayroq: nomaʼlum javob; question — savol matni
  ///
  /// In uz, this message translates to:
  /// **'Javobini bilmaysiz — avval aniqlashtiring: {question}'**
  String offerFlagUnknown(String question);

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Avvalgi tekshiruvlar'**
  String get offerHistory;

  /// Baho
  ///
  /// In uz, this message translates to:
  /// **'Yashil'**
  String get offerVerdictGreen;

  /// Baho
  ///
  /// In uz, this message translates to:
  /// **'Sariq'**
  String get offerVerdictYellow;

  /// Baho
  ///
  /// In uz, this message translates to:
  /// **'Qizil'**
  String get offerVerdictRed;

  /// Karta
  ///
  /// In uz, this message translates to:
  /// **'Kimdir tavakkalsiz foyda vaʼda qildimi? Bir daqiqada tekshiring.'**
  String get homeOfferCheckBody;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Sof foyda'**
  String get ledgerNetLabel;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Zarar'**
  String get ledgerLossLabel;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Buyout toʻlovi'**
  String get ledgerBuyoutLabel;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Keyingi davr: {start} dan'**
  String ledgerNextPeriod(String start);

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Assalomu alaykum! Baraka Dasturga xush kelibsiz'**
  String get obWelcome;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Til'**
  String get obLanguage;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Keyin sozlamalarda ham oʻzgartirish mumkin.'**
  String get obLanguageHint;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Zaxira nusxadan tiklash'**
  String get obRestore;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Oila aʼzolari'**
  String get obFamily;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Har yozuvda «kim?» belgisi boʻladi. Yolgʻiz yuritsangiz — faqat ismingizni yozing.'**
  String get obFamilyHint;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Ismingiz'**
  String get obOwnerName;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Aʼzo qoʻshish'**
  String get obAddMember;

  /// Rol
  ///
  /// In uz, this message translates to:
  /// **'Katta'**
  String get obMemberAdult;

  /// Rol
  ///
  /// In uz, this message translates to:
  /// **'Bola'**
  String get obMemberChild;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Daromadingiz qanday keladi?'**
  String get obIncome;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Shunga qarab bosh ekran va eslatmalar moslashadi.'**
  String get obIncomeHint;

  /// Variant
  ///
  /// In uz, this message translates to:
  /// **'Kunlik naqd'**
  String get obIncomeDaily;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Taksi, bozor, usta — har kuni kechqurun «bugun qancha?» deb eslatamiz.'**
  String get obIncomeDailyHint;

  /// Variant
  ///
  /// In uz, this message translates to:
  /// **'Buyurtma boʻyicha'**
  String get obIncomeOrders;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Tikuv, pazandachilik, taʼmirlash — har shanba haftalik eslatma.'**
  String get obIncomeOrdersHint;

  /// Variant
  ///
  /// In uz, this message translates to:
  /// **'Oylik maosh'**
  String get obIncomeSalary;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Maosh kuni eslatamiz va oylik davr shu kundan boshlanadi.'**
  String get obIncomeSalaryHint;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Maosh kuni'**
  String get obSalaryDay;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Hozir qarzingiz bormi?'**
  String get obDebt;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Bank, doʻkon nasiyasi, qarindosh yoki doʻst — hammasi hisobga olinadi. Bu sir ilovadan chiqmaydi.'**
  String get obDebtHint;

  /// Variant
  ///
  /// In uz, this message translates to:
  /// **'Ha, bor'**
  String get obDebtYes;

  /// Variant
  ///
  /// In uz, this message translates to:
  /// **'Yoʻq'**
  String get obDebtNo;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Qarzlarni yozgach, «Qarzdan chiqish» rejimini taklif qilamiz: daromadning 70 % i roʻzgʻorga, 20 % i qarzni tezroq uzishga, 10 % i baribir «Kelajagim»ga.'**
  String get obDebtRecovery;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Davom etish'**
  String get obNext;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Boshlash'**
  String get obFinish;

  /// Qadam
  ///
  /// In uz, this message translates to:
  /// **'{step} / {total}'**
  String obStep(int step, int total);

  /// Bildirishnoma
  ///
  /// In uz, this message translates to:
  /// **'Daromadni yozdingizmi?'**
  String get reminderIncomeTitle;

  /// Bildirishnoma
  ///
  /// In uz, this message translates to:
  /// **'Bugun qancha topdingiz? Bir daqiqada yozing — ulush ham ajraladi.'**
  String get reminderIncomeDaily;

  /// Bildirishnoma
  ///
  /// In uz, this message translates to:
  /// **'Bu haftadagi buyurtmalar puli yozildimi?'**
  String get reminderIncomeWeekly;

  /// Bildirishnoma
  ///
  /// In uz, this message translates to:
  /// **'Bugun maosh kuni. Avval oʻzingizga toʻlang — «Kelajagim» ulushini ajrating.'**
  String get reminderIncomeMonthly;

  /// Sozlama
  ///
  /// In uz, this message translates to:
  /// **'Daromad turi'**
  String get settingsIncomeKind;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Zaxira nusxa'**
  String get backupTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Butun daftar siz tanlagan parol bilan shifrlangan faylga yoziladi. Telefon almashsa yoki ilova oʻchirilsa — shu fayl va parol bilan tiklaysiz. Parolni unutmang: uni hech kim tiklay olmaydi.'**
  String get backupHint;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Parol (kamida 8 belgi)'**
  String get backupPassword;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Parolni takrorlang'**
  String get backupPasswordRepeat;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Parollar mos emas.'**
  String get backupPasswordMismatch;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Nusxa yaratish va saqlash'**
  String get backupExport;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Fayldan tiklash'**
  String get backupImport;

  /// Tasdiq
  ///
  /// In uz, this message translates to:
  /// **'Hozirgi maʼlumotlar toʻliq nusxadagisi bilan almashtiriladi. Davom etamizmi?'**
  String get backupImportConfirm;

  /// Oyna
  ///
  /// In uz, this message translates to:
  /// **'Nusxa paroli'**
  String get backupImportPassword;

  /// Xabar
  ///
  /// In uz, this message translates to:
  /// **'Tiklandi: {count} ta yozuv.'**
  String backupRestored(int count);

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Parol notoʻgʻri yoki fayl buzilgan.'**
  String get backupBadPassword;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Bu Baraka Dastur zaxira nusxasi emas.'**
  String get backupBadFormat;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Nusxa ilovaning boshqa versiyasida yaratilgan — ilovani yangilang.'**
  String get backupVersion;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Shifrlanmoqda…'**
  String get backupWorking;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Bugungi tushum'**
  String get homeAddIncomeDaily;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Buyurtma puli'**
  String get homeAddIncomeOrders;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Maosh'**
  String get homeAddIncomeSalary;

  /// Kanal
  ///
  /// In uz, this message translates to:
  /// **'Daromad eslatmalari'**
  String get reminderIncomeChannel;

  /// Sozlama
  ///
  /// In uz, this message translates to:
  /// **'Parol bilan shifrlangan fayl: saqlash va tiklash'**
  String get settingsBackupHint;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Tiklanmoqda…'**
  String get backupRestoring;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Nusxa yaratish'**
  String get backupExportTitle;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Nusxadan tiklash'**
  String get backupImportTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Faylni tanlang va nusxa yaratilgandagi parolni kiriting.'**
  String get backupImportHint;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Olib tashlash'**
  String get obMemberRemove;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Yana koʻrsatish ({count})'**
  String showMore(int count);

  /// Sozlama
  ///
  /// In uz, this message translates to:
  /// **'Tanlang'**
  String get settingsIncomeKindUnset;

  /// Rol
  ///
  /// In uz, this message translates to:
  /// **'Hakam'**
  String get roleArbiter;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Ismni yozing.'**
  String get receiptErrName;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Imzo chizilmagan.'**
  String get receiptErrSignature;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Kelishuvlar'**
  String get agTitle;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Kelishuv'**
  String get agScreenTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Ogʻzaki kelishuv — qumga qurilgan uy. Yozish ishonchsizlik emas, ishonchni asrash vositasi.'**
  String get agIntro;

  /// Bo'sh
  ///
  /// In uz, this message translates to:
  /// **'Hali kelishuv yoʻq. Ijara, xizmat, oilaviy kelishuv yoki hozir ogʻzaki davom etayotganini yozib qoʻying.'**
  String get agEmpty;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Yangi kelishuv'**
  String get agNew;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Sheriklik'**
  String get agTypePartnership;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Qarz tilxati'**
  String get agTypeLoan;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Ijara'**
  String get agTypeRent;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Xizmat yoki ish'**
  String get agTypeService;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Oilaviy kelishuv'**
  String get agTypeFamily;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Boshqa'**
  String get agTypeOther;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Qoralama'**
  String get agStatusDraft;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Imzolangan'**
  String get agStatusSigned;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Amalda'**
  String get agStatusActive;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Nizoda'**
  String get agStatusDispute;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Yopilgan'**
  String get agStatusClosed;

  /// Versiya
  ///
  /// In uz, this message translates to:
  /// **'{n}-versiya'**
  String agVersion(int n);

  /// Belgi
  ///
  /// In uz, this message translates to:
  /// **'ogʻzakidan yozilgan'**
  String get agOralBadge;

  /// Sana
  ///
  /// In uz, this message translates to:
  /// **'Kuchga kirgan sana: {date}'**
  String agEffectiveFrom(String date);

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Bu hujjat 9 savolli tartibdan oldin imzolangan — imzolar oʻz kuchida. Keyingi versiyada savollarni toʻldiring.'**
  String get agLegacyHint;

  /// To'liqlik
  ///
  /// In uz, this message translates to:
  /// **'{n} / 9 savolga javob berildi'**
  String agProgress(int n);

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'9 savol tayyor — imzolash mumkin.'**
  String get agReadyHint;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Imzolash 9 savolning hammasiga javob berilgach (yoki izoh bilan «tegishli emas» deb belgilangach) ochiladi.'**
  String get agSignLocked;

  /// Kelishuv ekranidagi maslahatchi maslahati
  ///
  /// In uz, this message translates to:
  /// **'Maslahat: noqulay bandlarni ham oldindan yozing — masalan, kimdir vazifasini bir hafta bajara olmasa nima boʻladi. Aniq yozilgan qoida keyingi tortishuvning oldini oladi.'**
  String get agAdvisorTip;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Javob kerak'**
  String get agNeedsAnswer;

  /// Belgi
  ///
  /// In uz, this message translates to:
  /// **'Hujjatdan avtomatik'**
  String get agAutoBadge;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Bu savol asl hujjatdan olinadi — oʻzgartirish uchun shartnoma yoki qarz yozuvini tahrirlang.'**
  String get agAutoHint;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Imzolangan versiya oʻzgarmaydi — yangi versiya yarating.'**
  String get agErrSigned;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Kim bilan kim?'**
  String get agQ1;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Kim nima qoʻshyapti?'**
  String get agQ2;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Kim nima qiladi?'**
  String get agQ3;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Foyda qanday boʻlinadi?'**
  String get agQ4;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Zarar koʻrilsa nima boʻladi?'**
  String get agQ5;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Pul qayerda, hisobni kim yuritadi, ikkinchi tomon qachon koʻradi?'**
  String get agQ6;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Qanday ajralib chiqiladi?'**
  String get agQ7;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Kelisha olmasangiz, kim hakam?'**
  String get agQ8;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Qachon yangilanadi?'**
  String get agQ9;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Toʻliq ism-sharif, roli va aloqasi. Kamida ikki tomon.'**
  String get agQ1Hint;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Pul, mol, mehnat yoki tanish-bilish — har bir tomonda kamida bitta hissa.'**
  String get agQ2Hint;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Har vazifaga yagona masʼul va «bajarilmasa» bandi. Umumiy qoldirilgan ish koʻpincha hech kimning ishi boʻlmay qoladi.'**
  String get agQ3Hint;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Faqat foizda. Soʻmdagi qatʼiy summa sheriklikda taqiqlangan.'**
  String get agQ4Hint;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Mudarabada zarar kapital egasida, musharakada — kapitalga mutanosib.'**
  String get agQ5Hint;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Standart — oyiga bir marta ochiq hisob koʻrigi.'**
  String get agQ6Hint;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Oldindan ogohlantirish, ulushni baholash, toʻlash muddati va mol-mulkni boʻlish.'**
  String get agQ7Hint;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Ikkala tomon ishonadigan, tomonlardan biri boʻlmagan odam. Hakam ham roziligini imzolaydi.'**
  String get agQ8Hint;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Muddat va yillik yangilash sanasi; 30 kun oldin eslatamiz.'**
  String get agQ9Hint;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'{n}. {title}'**
  String agQuestionTitle(int n, String title);

  /// Kalit
  ///
  /// In uz, this message translates to:
  /// **'Tegishli emas'**
  String get agNotApplicable;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nega tegishli emas (izoh majburiy)'**
  String get agNaReason;

  /// Mazmun
  ///
  /// In uz, this message translates to:
  /// **'Tegishli emas: {reason}'**
  String agNaSummary(String reason);

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Toʻliq ism-sharif'**
  String get agPartyName;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Roli'**
  String get agPartyRole;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Aloqasi (qarindosh, qoʻshni…)'**
  String get agPartyRelation;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Tomon qoʻshish'**
  String get agPartyAdd;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Kim'**
  String get agWho;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Hissa turi'**
  String get agContribKind;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Pul'**
  String get agContribMoney;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Mol yoki uskuna'**
  String get agContribGoods;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Mehnat'**
  String get agContribLabor;

  /// Tur
  ///
  /// In uz, this message translates to:
  /// **'Tanish-bilish'**
  String get agContribNetwork;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Summa (soʻm)'**
  String get agAmountSom;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Tavsif'**
  String get agDescription;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Hissa qoʻshish'**
  String get agContribAdd;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Masʼul — bitta tomon. «Hamma» tanlab boʻlmaydi.'**
  String get agDutyHint;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Vazifa'**
  String get agDutyTitle;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Yagona masʼul'**
  String get agDutyOwner;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Bajarilmasa (masalan, 1 kun ichida xabar beradi va oʻrniga yechim topadi)'**
  String get agDutyBreach;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Vazifa qoʻshish'**
  String get agDutyAdd;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Ulushlar foizda, yigʻindisi 100 %.'**
  String get agProfitHint;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'{name} ulushi, %'**
  String agProfitShare(String name);

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Yoki soʻz bilan (masalan, ijara haqi oyiga …)'**
  String get agProfitText;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Zarar qanday taqsimlanadi'**
  String get agLossText;

  /// Matn
  ///
  /// In uz, this message translates to:
  /// **'Zarar kapitalga mutanosib taqsimlanadi.'**
  String get agLossMusharaka;

  /// Matn
  ///
  /// In uz, this message translates to:
  /// **'Qarzda foyda va zarar boʻlishilmaydi — faqat asosiy summa qaytariladi (foiz yoʻq).'**
  String get agLossLoan;

  /// Matn
  ///
  /// In uz, this message translates to:
  /// **'Qaytarish jadvali (qarz yozuvidan)'**
  String get agLoanSchedule;

  /// Matn
  ///
  /// In uz, this message translates to:
  /// **'Foiz yoʻq'**
  String get agLoanNoInterest;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Pul qayerda turadi'**
  String get agCustodyWhere;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Hisobni kim yuritadi'**
  String get agCustodyKeeper;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Ochiq hisob koʻrigi'**
  String get agCustodyEvery;

  /// Davr
  ///
  /// In uz, this message translates to:
  /// **'Har hafta'**
  String get agEveryWeek;

  /// Davr
  ///
  /// In uz, this message translates to:
  /// **'Ikki haftada bir'**
  String get agEvery2Weeks;

  /// Davr
  ///
  /// In uz, this message translates to:
  /// **'Oyiga bir marta'**
  String get agEveryMonth;

  /// Davr
  ///
  /// In uz, this message translates to:
  /// **'Uch oyda bir'**
  String get agEveryQuarter;

  /// Davr
  ///
  /// In uz, this message translates to:
  /// **'Yiliga bir marta'**
  String get agEveryYear;

  /// Davr
  ///
  /// In uz, this message translates to:
  /// **'Har {days} kunda'**
  String agEveryDays(int days);

  /// Ogohlantirish
  ///
  /// In uz, this message translates to:
  /// **'Koʻrik oyiga bir martadan siyrak — kelishmovchilik yigʻilib qolmasin, tez-tez koʻring.'**
  String get agReviewTooRare;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Oldindan ogohlantirish (kun)'**
  String get agExitNotice;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Ulush qanday baholanadi'**
  String get agExitValuation;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Qachon va qanday toʻlanadi'**
  String get agExitPayout;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Mol-mulk qanday boʻlinadi'**
  String get agExitAssets;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Hakam tomonlardan biri boʻla olmaydi.'**
  String get agArbiterHint;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Hakamning ism-sharifi'**
  String get agArbiterName;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Kim (masalan, mahalla oqsoqoli)'**
  String get agArbiterRole;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Guvohlar (vergul bilan)'**
  String get agWitnesses;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Muddat (oy)'**
  String get agTermMonths;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Yillik yangilash sanasi'**
  String get agReviewDate;

  /// Mazmun
  ///
  /// In uz, this message translates to:
  /// **'Yangilash: {date}'**
  String agReviewOn(String date);

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Kamida ikki tomon (ismi bilan) kerak.'**
  String get agErrPartiesMin2;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Har bir tomonning hissasi yozilsin.'**
  String get agErrContribution;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Har vazifaga bitta masʼul tanlang.'**
  String get agErrDutyOwner;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Har vazifaga «bajarilmasa» bandini yozing.'**
  String get agErrDutyBreach;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Ulushlar yigʻindisi 100 % boʻlsin.'**
  String get agErrShares;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Bu sheriklik emas — qatʼiy summa ribo yoki qarz boʻladi. Foyda faqat foizda.'**
  String get agErrGuaranteed;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Hakam tomonlardan biri boʻla olmaydi.'**
  String get agErrArbiterParty;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'«Tegishli emas» uchun izoh yozing.'**
  String get agErrNaReason;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Nomini yozing.'**
  String get agErrTitle;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Avval 9 savolning hammasiga javob bering.'**
  String get agErrIncomplete;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Ogʻzaki kelishuv oʻtgan sanadan boshlanadi.'**
  String get agErrFuture;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Avval hamma imzolasin.'**
  String get agErrNotSigned;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Imzolar'**
  String get agSignatures;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Imzolashga oʻtish'**
  String get agPrepareSign;

  /// Havola
  ///
  /// In uz, this message translates to:
  /// **'Imzolar sheriklik shartnomasi ekranida'**
  String get agSignInPartnership;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Kuchga kiritish'**
  String get agActivate;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Yillik yangilash: oʻzgarishsiz tasdiqlash'**
  String get agRenewUnchanged;

  /// Versiya izohi
  ///
  /// In uz, this message translates to:
  /// **'Oʻzgarishsiz tasdiqlandi'**
  String get agUnchangedNote;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Yangi versiya (oʻzgartirish)'**
  String get agNewVersion;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Hisob jurnali'**
  String get agJournal;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'{n} ta yozuv · zanjir butun, hech biri oʻzgartirilmagan'**
  String agChainOk(int n);

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Diqqat: {n}-yozuvdan boshlab zanjir buzilgan — yozuv oʻzgartirilgan boʻlishi mumkin'**
  String agChainBroken(int n);

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Zanjir boshi'**
  String get agChainHead;

  /// Jurnal
  ///
  /// In uz, this message translates to:
  /// **'Hissa'**
  String get agJContribution;

  /// Jurnal
  ///
  /// In uz, this message translates to:
  /// **'Foyda ulushi'**
  String get agJProfit;

  /// Jurnal
  ///
  /// In uz, this message translates to:
  /// **'Zarar ulushi'**
  String get agJLoss;

  /// Jurnal
  ///
  /// In uz, this message translates to:
  /// **'Qarz toʻlovi'**
  String get agJLoanPayment;

  /// Jurnal
  ///
  /// In uz, this message translates to:
  /// **'Kirim'**
  String get agJIncome;

  /// Jurnal
  ///
  /// In uz, this message translates to:
  /// **'Xarajat'**
  String get agJExpense;

  /// Jurnal
  ///
  /// In uz, this message translates to:
  /// **'Fors-major'**
  String get agJForceMajeure;

  /// Jurnal
  ///
  /// In uz, this message translates to:
  /// **'Ulush sotib olish'**
  String get agJBuyout;

  /// Jurnal
  ///
  /// In uz, this message translates to:
  /// **'Boshlangʻich holat'**
  String get agJOpening;

  /// Jurnal
  ///
  /// In uz, this message translates to:
  /// **'Tuzatish'**
  String get agJCorrection;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Kelishuv PDF'**
  String get agPdfShare;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'{version}-versiya · {date} dan'**
  String agPdfSubtitle(int version, String date);

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'9 ta asosiy savol boʻyicha oddiy tilda yozilgan kelishuv.'**
  String get agPdfIntro;

  /// PDF
  ///
  /// In uz, this message translates to:
  /// **'Shaxsiy hisob uchun yozuv, yuridik kafolat yoki maslahat emas.'**
  String get agPdfNote;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nomi (masalan, doʻkon ijarasi)'**
  String get agFieldTitle;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Sizning ismingiz'**
  String get agFieldMe;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Ikkinchi tomon'**
  String get agFieldOther;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Turi'**
  String get agFieldType;

  /// Ekran
  ///
  /// In uz, this message translates to:
  /// **'Ogʻzaki kelishuvni yozib olish'**
  String get agOralTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Hozir ogʻzaki davom etayotgan sheriklik, ijara yoki qarz'**
  String get agOralHint;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Kelishuv oʻtgan sanadan boshlangan boʻlishi mumkin. Shu kungacha holatni bitta yozuv qilib kiriting — tomonlar uni ham imzolab tasdiqlaydi.'**
  String get agOralIntro;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Qachondan beri'**
  String get agOralSince;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Shu kungacha holat'**
  String get agOralOpening;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Kim qancha qoʻshgan, qancha boʻlingan, qancha qarz qolgan.'**
  String get agOralOpeningHint;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Siz qoʻshgan'**
  String get agOralMine;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Ikkinchi tomon qoʻshgan'**
  String get agOralTheirs;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Izoh (masalan, 3 oyda 2 marta foyda boʻlingan)'**
  String get agOralNote;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Yozib olish va 9 savolga oʻtish'**
  String get agOralSave;

  /// Kelishuv vazifalari bo'limi
  ///
  /// In uz, this message translates to:
  /// **'Vazifalar'**
  String get acDutiesTitle;

  /// Vazifa bo'yicha xabar tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Bajara olmayapman'**
  String get acDutyReport;

  /// Xabar dialogi sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Vazifani bajara olmayapman'**
  String get acDutyReportTitle;

  /// Xabar: sabab maydoni
  ///
  /// In uz, this message translates to:
  /// **'Sabab'**
  String get acDutyReason;

  /// Xabar: yechim maydoni
  ///
  /// In uz, this message translates to:
  /// **'Oʻrniga yechim (ixtiyoriy)'**
  String get acDutyFix;

  /// Xabar: tomon tanlash
  ///
  /// In uz, this message translates to:
  /// **'Kim xabar bermoqda'**
  String get acDutyWho;

  /// Bandni ko'rsatish dialogi sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Shartnoma bandi'**
  String get acDutyClauseTitle;

  /// Band matni va ohang
  ///
  /// In uz, this message translates to:
  /// **'{clause}\n\nBu ayb emas — kelishilgan qoidaga qaytamiz.'**
  String acDutyClauseBody(Object clause);

  /// Hodisalar ro'yxati sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Oxirgi koʻrikdan keyingi hodisalar'**
  String get acIncidentsTitle;

  /// Hodisa qatori
  ///
  /// In uz, this message translates to:
  /// **'{reason} — {fix}'**
  String acIncidentLine(Object reason, Object fix);

  /// Hodisa qatori (yechimsiz)
  ///
  /// In uz, this message translates to:
  /// **'{reason}'**
  String acIncidentNoFix(Object reason);

  /// Ko'rik bo'limi sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Oylik ochiq hisob koʻrigi'**
  String get acReviewTitle;

  /// Keyingi ko'rik sanasi
  ///
  /// In uz, this message translates to:
  /// **'Keyingi koʻrik: {date}'**
  String acReviewNext(Object date);

  /// Ko'rik muddati o'tgan yoki keldi
  ///
  /// In uz, this message translates to:
  /// **'Koʻrik vaqti keldi'**
  String get acReviewDue;

  /// Ochiq ko'rik holati
  ///
  /// In uz, this message translates to:
  /// **'Koʻrik ochiq. Kesim sanasi: {date}'**
  String acReviewOpenInfo(Object date);

  /// Yangi ko'rik tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Koʻrikni boshlash'**
  String get acReviewStart;

  /// Ochiq ko'rikka o'tish
  ///
  /// In uz, this message translates to:
  /// **'Koʻrikka oʻtish'**
  String get acReviewContinue;

  /// Bayonnomalar soni
  ///
  /// In uz, this message translates to:
  /// **'Bayonnomalar: {count}'**
  String acReviewMinutesCount(int count);

  /// Ko'rik ekrani sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Koʻrik'**
  String get acReviewScreenTitle;

  /// Ko'rik kesimi
  ///
  /// In uz, this message translates to:
  /// **'Kesim sanasi: {date}'**
  String acReviewCutoff(Object date);

  /// Ko'rik davr yozuvlari
  ///
  /// In uz, this message translates to:
  /// **'Davr yozuvlari'**
  String get acReviewPeriodTitle;

  /// Bo'sh davr
  ///
  /// In uz, this message translates to:
  /// **'Bu davrda yozuv yoʻq.'**
  String get acReviewPeriodEmpty;

  /// Ko'rik jami
  ///
  /// In uz, this message translates to:
  /// **'Kirim: {income} · Chiqim: {expense}'**
  String acReviewTotals(Object income, Object expense);

  /// Zanjir tekshiruvi — toza
  ///
  /// In uz, this message translates to:
  /// **'Zanjir butun ({count} ta yozuv)'**
  String acReviewChainOk(int count);

  /// Zanjir tekshiruvi — buzilgan
  ///
  /// In uz, this message translates to:
  /// **'Zanjir buzilgan: #{seq}'**
  String acReviewChainBroken(int seq);

  /// Ko'rikdagi hodisalar
  ///
  /// In uz, this message translates to:
  /// **'Hodisalar'**
  String get acReviewIncidents;

  /// Ko'rik: roziman tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Koʻrdim, roziman'**
  String get acReviewAgree;

  /// Ko'rik: e'tiroz tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Eʼtirozim bor'**
  String get acReviewObject;

  /// E'tiroz dialogi
  ///
  /// In uz, this message translates to:
  /// **'Eʼtiroz'**
  String get acReviewObjectTitle;

  /// E'tiroz izohi maydoni
  ///
  /// In uz, this message translates to:
  /// **'Nimaga rozi emassiz?'**
  String get acReviewObjectHint;

  /// Tomon javobi — roziman
  ///
  /// In uz, this message translates to:
  /// **'{party}: roziman'**
  String acReviewVerdictAgree(Object party);

  /// Tomon javobi — e'tiroz
  ///
  /// In uz, this message translates to:
  /// **'{party}: eʼtiroz — {note}'**
  String acReviewVerdictObject(Object party, Object note);

  /// Ko'rik yakuniga tayyorgarlik
  ///
  /// In uz, this message translates to:
  /// **'Hamma tomon javob bergach, bayonnomani yakunlang.'**
  String get acReviewWaiting;

  /// Ko'rikni yakunlash tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Bayonnomani yakunlash'**
  String get acReviewComplete;

  /// Ko'rik yakunlandi xabari
  ///
  /// In uz, this message translates to:
  /// **'Koʻrik yakunlandi. Bayonnoma saqlandi.'**
  String get acReviewDone;

  /// Davr qulfi haqida izoh
  ///
  /// In uz, this message translates to:
  /// **'Bu sanagacha boʻlgan moliyaviy yozuvlar muzlatiladi; faqat tuzatuvchi yozuv qoʻshiladi.'**
  String get acReviewLockedNote;

  /// Bayonnoma PDF tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Bayonnomani ulashish (PDF)'**
  String get acReviewMinutesShare;

  /// Ko'rik davr yozuvlari bo'limi
  ///
  /// In uz, this message translates to:
  /// **'Hisob yozuvlari'**
  String get acReviewLedgerTitle;

  /// Nizolar bo'limi sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Nizolar'**
  String get acDisputesTitle;

  /// Nizo yo'q
  ///
  /// In uz, this message translates to:
  /// **'Ochiq nizo yoʻq.'**
  String get acDisputeNone;

  /// Nizo ochish tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Nizo ochish'**
  String get acDisputeOpen;

  /// Nizo mavzusi
  ///
  /// In uz, this message translates to:
  /// **'Mavzu'**
  String get acDisputeTopic;

  /// Nizo tegishli bandi
  ///
  /// In uz, this message translates to:
  /// **'Tegishli band (ixtiyoriy)'**
  String get acDisputeClause;

  /// Nizo talabi
  ///
  /// In uz, this message translates to:
  /// **'Sizning talabingiz'**
  String get acDisputeClaim;

  /// Boshqa tomon talabi
  ///
  /// In uz, this message translates to:
  /// **'Talab qoʻshish'**
  String get acDisputeAddClaim;

  /// Nizo holati — ochiq
  ///
  /// In uz, this message translates to:
  /// **'Ochiq'**
  String get acDisputeStatusOpen;

  /// Nizo holati — hal qilingan
  ///
  /// In uz, this message translates to:
  /// **'Hal qilingan'**
  String get acDisputeStatusDecided;

  /// Nizo ekrani sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Nizo'**
  String get acDisputeScreenTitle;

  /// Talablar ro'yxati
  ///
  /// In uz, this message translates to:
  /// **'Tomonlar talablari'**
  String get acDisputeClaimsTitle;

  /// Qaror bo'limi
  ///
  /// In uz, this message translates to:
  /// **'Hakam qarori'**
  String get acDisputeDecisionTitle;

  /// Qaror maydoni
  ///
  /// In uz, this message translates to:
  /// **'Qaror matni'**
  String get acDisputeDecisionHint;

  /// Qarorni saqlash tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Qarorni yozish'**
  String get acDisputeDecide;

  /// Hakam papkasi PDF tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Hakam uchun ish papkasi (PDF)'**
  String get acDisputePdf;

  /// Nizo holati banneri
  ///
  /// In uz, this message translates to:
  /// **'Kelishuv nizoda: taqsimot toʻxtatilgan.'**
  String get acDisputeInDispute;

  /// Qaror yozildi xabari
  ///
  /// In uz, this message translates to:
  /// **'Qaror yozildi. Kelishuv yana faol.'**
  String get acDisputeDecidedNote;

  /// Yangilash bo'limi
  ///
  /// In uz, this message translates to:
  /// **'Yillik yangilash'**
  String get acRenewalTitle;

  /// Yangilash sanasi
  ///
  /// In uz, this message translates to:
  /// **'Yangilash sanasi: {date}. Eslatma 30 kun oldin keladi.'**
  String acRenewalDue(Object date);

  /// O'zgarishsiz tasdiqlash tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Oʻzgarishsiz tasdiqlash'**
  String get acRenewalUnchanged;

  /// Qayta imzo haqida izoh
  ///
  /// In uz, this message translates to:
  /// **'Yangi versiyani hamma qayta imzolashi kerak.'**
  String get acRenewalNeedsSign;

  /// Yangilash bildirishnomasi sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Kelishuvni yangilash vaqti'**
  String get acRenewalNotifTitle;

  /// Yangilash bildirishnomasi matni
  ///
  /// In uz, this message translates to:
  /// **'«{title}» 30 kundan keyin yangilanadi. Birga qayta oʻqing.'**
  String acRenewalNotifBody(Object title);

  /// Bildirishnoma kanali
  ///
  /// In uz, this message translates to:
  /// **'Kelishuv eslatmalari'**
  String get acRenewalChannel;

  /// Katta foyda dialogi
  ///
  /// In uz, this message translates to:
  /// **'Katta foyda'**
  String get acSpikeTitle;

  /// Katta foyda tabrigi (SPEC 2F.7)
  ///
  /// In uz, this message translates to:
  /// **'Barakali foyda — tabriklaymiz! Endi kelishuvni birga qayta oʻqib chiqaylik.'**
  String get acSpikeMessage;

  /// Katta foyda summasi
  ///
  /// In uz, this message translates to:
  /// **'Davr foydasi: {amount}'**
  String acSpikeAmount(Object amount);

  /// Tomon tasdiqlashi
  ///
  /// In uz, this message translates to:
  /// **'{party} 4–5-bandni qayta oʻqidi'**
  String acSpikeRead(Object party);

  /// Navbatdan tashqari ko'rik taklifi
  ///
  /// In uz, this message translates to:
  /// **'Navbatdan tashqari koʻrik'**
  String get acSpikeReviewOffer;

  /// Taqsimot tugmasi (tasdiqdan keyin)
  ///
  /// In uz, this message translates to:
  /// **'Taqsimlash'**
  String get acSpikeDistribute;

  /// Katta foyda dialogini yopish
  ///
  /// In uz, this message translates to:
  /// **'Hozircha emas'**
  String get acSpikeCancel;

  /// Bosh ekran kartasi
  ///
  /// In uz, this message translates to:
  /// **'Yaqinlashayotgan koʻrik / yangilash'**
  String get acHomeTitle;

  /// Bosh ekran kartasi matni
  ///
  /// In uz, this message translates to:
  /// **'{count} ta kelishuvda koʻrik yoki yangilash vaqti yaqin.'**
  String acHomeBody(int count);

  /// Kartada nizolar soni
  ///
  /// In uz, this message translates to:
  /// **'Ochiq nizo: {count}'**
  String acHomeDisputes(int count);

  /// Markaz — keyingi ko'rik
  ///
  /// In uz, this message translates to:
  /// **'Keyingi koʻrik: {date}'**
  String acCenterNextReview(Object date);

  /// Markaz — hodisalar
  ///
  /// In uz, this message translates to:
  /// **'Ochiq hodisa: {count}'**
  String acCenterOpenIncidents(int count);

  /// Markaz — nizolar
  ///
  /// In uz, this message translates to:
  /// **'Nizo: {count}'**
  String acCenterDisputes(int count);

  /// Markaz bo'sh holati
  ///
  /// In uz, this message translates to:
  /// **'Koʻrik va yangilash sanalari bu yerda koʻrinadi.'**
  String get acCenterEmptyHint;

  /// Oilaviy shablon tanlash sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Shablon'**
  String get agFamilyTemplate;

  /// Oilaviy kelishuv izohi
  ///
  /// In uz, this message translates to:
  /// **'Oilaviy kelishuv buyruq emas — birga kelishuv. Guvoh va hakam shart emas; kattalarning tasdigʻi yetarli.'**
  String get agFamilyHint;

  /// Oilaviy shablon: uy ishi
  ///
  /// In uz, this message translates to:
  /// **'Uyda kim nima qiladi'**
  String get agTplChores;

  /// Uy ishi shabloni izohi
  ///
  /// In uz, this message translates to:
  /// **'Har kimning uy ishi aniq; bajarilmasa — ayblamasdan xabar bering.'**
  String get agTplChoresHint;

  /// Oilaviy shablon: pul
  ///
  /// In uz, this message translates to:
  /// **'Pul qayerda turadi va kim yuritadi'**
  String get agTplMoney;

  /// Pul shabloni izohi
  ///
  /// In uz, this message translates to:
  /// **'Umumiy pul qayerda, kim yuritadi va qanday koʻrinadi.'**
  String get agTplMoneyHint;

  /// Oilaviy shablon: havas
  ///
  /// In uz, this message translates to:
  /// **'Havas chegarasi'**
  String get agTplHavas;

  /// Havas shabloni izohi
  ///
  /// In uz, this message translates to:
  /// **'Oilada havas xarajatlari chegarasi (Havas boʻlimi bilan bogʻlanadi).'**
  String get agTplHavasHint;

  /// Oilaviy shablon: kengash
  ///
  /// In uz, this message translates to:
  /// **'Oila kengashi qachon oʻtadi'**
  String get agTplCouncil;

  /// Kengash shabloni izohi
  ///
  /// In uz, this message translates to:
  /// **'Oylik kengash kuni va qanday qarorlar qabul qilinadi.'**
  String get agTplCouncilHint;

  /// Jurnal: vazifa hodisasi
  ///
  /// In uz, this message translates to:
  /// **'Vazifa bajarilmadi'**
  String get agJDutyIncident;

  /// Jurnal: ko'rik ochildi
  ///
  /// In uz, this message translates to:
  /// **'Koʻrik ochildi'**
  String get agJReviewOpened;

  /// Jurnal: ko'rik javobi
  ///
  /// In uz, this message translates to:
  /// **'Koʻrik javobi'**
  String get agJReviewAck;

  /// Jurnal: bayonnoma
  ///
  /// In uz, this message translates to:
  /// **'Koʻrik bayonnomasi'**
  String get agJAccountReview;

  /// Jurnal: katta foyda tasdig'i
  ///
  /// In uz, this message translates to:
  /// **'«Katta foyda» tasdigʻi'**
  String get agJProfitSpikeAck;

  /// Jurnal: nizo
  ///
  /// In uz, this message translates to:
  /// **'Nizo'**
  String get agJDisputeOpened;

  /// Jurnal: hakam qarori
  ///
  /// In uz, this message translates to:
  /// **'Hakam qarori'**
  String get agJArbiterDecision;

  /// Xato: davr qulflangan
  ///
  /// In uz, this message translates to:
  /// **'Bu sanagacha yozuvlar koʻrik bayonnomasi bilan qulflangan.'**
  String get agErrReviewLocked;

  /// Xato: ko'rik ochiq
  ///
  /// In uz, this message translates to:
  /// **'Koʻrik ochiq. Avval uni yakunlang.'**
  String get agErrReviewOpen;

  /// Xato: ko'rik ochiq emas
  ///
  /// In uz, this message translates to:
  /// **'Bu koʻrik ochiq emas.'**
  String get agErrNoReview;

  /// Xato: javoblar to'liq emas
  ///
  /// In uz, this message translates to:
  /// **'Hamma tomon javob bersin.'**
  String get agErrReviewIncomplete;

  /// Xato: qayta javob
  ///
  /// In uz, this message translates to:
  /// **'Bu tomon allaqachon javob bergan.'**
  String get agErrReviewAcked;

  /// Xato: e'tiroz izohi yo'q
  ///
  /// In uz, this message translates to:
  /// **'Eʼtiroz uchun izoh yozing.'**
  String get agErrObjection;

  /// Xato: sabab yo'q
  ///
  /// In uz, this message translates to:
  /// **'Sababni yozing.'**
  String get agErrReasonRequired;

  /// Xato: vazifa topilmadi
  ///
  /// In uz, this message translates to:
  /// **'Vazifa topilmadi.'**
  String get agErrDutyNotFound;

  /// Xato: tomon topilmadi
  ///
  /// In uz, this message translates to:
  /// **'Tomon topilmadi.'**
  String get agErrPartyNotFound;

  /// Xato: nizo ochiq
  ///
  /// In uz, this message translates to:
  /// **'Kelishuv nizoda — avval hakam qarori kerak.'**
  String get agErrInDispute;

  /// Xato: nizo topilmadi
  ///
  /// In uz, this message translates to:
  /// **'Nizo topilmadi.'**
  String get agErrDisputeNotFound;

  /// Xato: nizo hal qilingan
  ///
  /// In uz, this message translates to:
  /// **'Bu nizo allaqachon hal qilingan.'**
  String get agErrDisputeDecided;

  /// Xato: nizo maydonlari
  ///
  /// In uz, this message translates to:
  /// **'Mavzu va talabni yozing.'**
  String get agErrClaimRequired;

  /// Xato: qaror matni yo'q
  ///
  /// In uz, this message translates to:
  /// **'Qaror matnini yozing.'**
  String get agErrDecisionRequired;

  /// Xato: katta foyda tasdig'i kerak
  ///
  /// In uz, this message translates to:
  /// **'Katta foyda: ikkala tomon 4–5-bandni qayta oʻqib tasdiqlasin.'**
  String get agErrSpikeAck;

  /// Xato: qayta tasdiq
  ///
  /// In uz, this message translates to:
  /// **'Bu tomon allaqachon tasdiqlagan.'**
  String get agErrAcked;

  /// PDF: sana ustuni
  ///
  /// In uz, this message translates to:
  /// **'Sana'**
  String get acPdfColDate;

  /// PDF: tur ustuni
  ///
  /// In uz, this message translates to:
  /// **'Tur'**
  String get acPdfColKind;

  /// PDF: tomon ustuni
  ///
  /// In uz, this message translates to:
  /// **'Tomon'**
  String get acPdfColParty;

  /// PDF: summa ustuni
  ///
  /// In uz, this message translates to:
  /// **'Summa'**
  String get acPdfColAmount;

  /// PDF: izoh ustuni
  ///
  /// In uz, this message translates to:
  /// **'Izoh'**
  String get acPdfColNote;

  /// Koʻrik: tomonlar javobi boʻlimi
  ///
  /// In uz, this message translates to:
  /// **'Tomonlar javobi'**
  String get acReviewAcksTitle;

  /// Hakam papkasi: kelishuv boʻlimi
  ///
  /// In uz, this message translates to:
  /// **'Kelishuv'**
  String get acPdfFolderAgreement;

  /// Hakam papkasi: versiyalar
  ///
  /// In uz, this message translates to:
  /// **'Versiyalar tarixi'**
  String get acPdfFolderVersions;

  /// Hakam papkasi: tomonlar
  ///
  /// In uz, this message translates to:
  /// **'Tomonlar'**
  String get acPdfFolderParties;

  /// Hakam papkasi: hisob yozuvlari
  ///
  /// In uz, this message translates to:
  /// **'Davr yozuvlari va zanjir tekshiruvi'**
  String get acPdfFolderLedger;

  /// Hakam papkasi: bayonnomalar
  ///
  /// In uz, this message translates to:
  /// **'Koʻrik bayonnomalari'**
  String get acPdfFolderMinutes;

  /// Hakam papkasi: hodisalar
  ///
  /// In uz, this message translates to:
  /// **'Vazifa hodisalari'**
  String get acPdfFolderIncidents;

  /// Hakam papkasi: talablar
  ///
  /// In uz, this message translates to:
  /// **'Tomonlarning talablari'**
  String get acPdfFolderClaims;

  /// Hakam papkasi: qarorlar
  ///
  /// In uz, this message translates to:
  /// **'Hakam qarorlari'**
  String get acPdfFolderDecision;

  /// Hakam papkasi: yaxlitlik
  ///
  /// In uz, this message translates to:
  /// **'Zanjir yaxlitligi'**
  String get acPdfFolderIntegrity;

  /// Hakam qarori yo'q
  ///
  /// In uz, this message translates to:
  /// **'Hakam qarori hali yoʻq.'**
  String get acPdfNoDecision;

  /// Ro'yxat boʻsh
  ///
  /// In uz, this message translates to:
  /// **'Yoʻq'**
  String get acPdfNone;

  /// Bayonnoma qatori
  ///
  /// In uz, this message translates to:
  /// **'{date} · {id} · zanjir boshi {head}'**
  String acPdfMinutesLine(Object date, Object id, Object head);

  /// Bayonnomadagi e'tiroz
  ///
  /// In uz, this message translates to:
  /// **'Eʼtiroz: {note}'**
  String acPdfObjection(Object note);

  /// Talab qatori
  ///
  /// In uz, this message translates to:
  /// **'{party}: {claim}'**
  String acPdfClaimLine(Object party, Object claim);

  /// Qaror qatori
  ///
  /// In uz, this message translates to:
  /// **'{date} · {decision}'**
  String acPdfDecisionLine(Object date, Object decision);

  /// PDF: kesim sanasi
  ///
  /// In uz, this message translates to:
  /// **'Kesim: {date}'**
  String acPdfCutoffLine(Object date);

  /// PDF: hodisa qatori
  ///
  /// In uz, this message translates to:
  /// **'{date} · {party}: {reason}'**
  String acPdfIncidentLine(Object date, Object party, Object reason);

  /// Taklif savoli: chiqish
  ///
  /// In uz, this message translates to:
  /// **'Pulni istagan vaqtda qaytarib olsa boʻladimi?'**
  String get offerQExit;

  /// Taklif savoli: ruxsat
  ///
  /// In uz, this message translates to:
  /// **'Odamlardan pul yigʻishga davlat ruxsati bormi?'**
  String get offerQLicense;

  /// Taklif savoli: o'z ko'zi bilan
  ///
  /// In uz, this message translates to:
  /// **'Ishni oʻz koʻzingiz bilan koʻrdingizmi (ombor, mol, hujjat)?'**
  String get offerQVerified;

  /// Bayroq: chiqish qiyin
  ///
  /// In uz, this message translates to:
  /// **'Pulni qaytarib olish qiyin — kirish oson, chiqish qiyin boʻlsa, qoching.'**
  String get offerFlagExit;

  /// Bayroq: ruxsat yo'q
  ///
  /// In uz, this message translates to:
  /// **'Davlat ruxsati yoʻq — odamlardan pul yigʻish qonuniy boʻlmasligi mumkin.'**
  String get offerFlagLicense;

  /// Bayroq: tekshirishga ruxsat yo'q
  ///
  /// In uz, this message translates to:
  /// **'Ishni koʻrsatishmadi. Halol taklif egasi ishini koʻrsatishdan qochmaydi.'**
  String get offerFlagVerified;

  /// Tekshiruv ro'yxati sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Pul qoʻyishdan oldin oʻz koʻzingiz bilan koʻring'**
  String get offerVerifyTitle;

  /// Tekshiruv: mol
  ///
  /// In uz, this message translates to:
  /// **'Ombor va mol: nima sotiladi, qayerda turadi?'**
  String get offerVerifyGoods;

  /// Tekshiruv: shartnoma
  ///
  /// In uz, this message translates to:
  /// **'Shartnoma: pul nimaga ishlatiladi, zarar kim zimmasida?'**
  String get offerVerifyDocs;

  /// Tekshiruv: ruxsat
  ///
  /// In uz, this message translates to:
  /// **'Odamlardan pul yigʻishga davlat ruxsati'**
  String get offerVerifyLicense;

  /// Tekshiruv: to'lov manbai
  ///
  /// In uz, this message translates to:
  /// **'Toʻlovlar qayerdan: mol sotuvidanmi yoki yangi kirganlarning pulidanmi?'**
  String get offerVerifySource;

  /// Tekshiruv: qaytarish
  ///
  /// In uz, this message translates to:
  /// **'Pulni qaytarib olish tartibi'**
  String get offerVerifyExit;

  /// Tekshiruv izohi
  ///
  /// In uz, this message translates to:
  /// **'Ishi halol odam bu iltimosdan quvonadi. Rad etish yoki shoshirishning oʻzi xavf belgisi.'**
  String get offerVerifyHint;

  /// Oylik stavka maydoni
  ///
  /// In uz, this message translates to:
  /// **'Vaʼda qilingan foyda, oyiga % (ixtiyoriy)'**
  String get offerRate;

  /// Yillik ko'paytma ogohlantirishi
  ///
  /// In uz, this message translates to:
  /// **'Oyiga {rate} % — yiliga oddiy hisobda {simple} barobar, murakkab hisobda {compound} barobar. Bunday daromadni halol savdo yoki ishlab chiqarish barqaror bera olmaydi.'**
  String offerRateYearly(Object rate, Object simple, Object compound);

  /// Summa maydoni
  ///
  /// In uz, this message translates to:
  /// **'Qancha pul qoʻymoqchisiz? (ixtiyoriy)'**
  String get offerAmount;

  /// Belgilar bo'limi
  ///
  /// In uz, this message translates to:
  /// **'Besh xavf belgisi'**
  String get offerSignsTitle;

  /// Belgi yo'q
  ///
  /// In uz, this message translates to:
  /// **'Xavf belgisi topilmadi. Baribir ishni oʻz koʻzingiz bilan koʻring.'**
  String get offerSignsNone;

  /// Bitta belgi
  ///
  /// In uz, this message translates to:
  /// **'Bitta belgi bor — hushyor torting.'**
  String get offerSignsCaution;

  /// Ikki va ko'p belgi
  ///
  /// In uz, this message translates to:
  /// **'Ikki va undan koʻp belgi — qoching.'**
  String get offerSignsFlee;

  /// Belgi 1
  ///
  /// In uz, this message translates to:
  /// **'Katta foyda kafolatlanmoqda: halol foydaning kafolati boʻlmaydi, unda tavakkal bor.'**
  String get offerSignGuaranteed;

  /// Belgi 2
  ///
  /// In uz, this message translates to:
  /// **'Shoshirishmoqda: oʻylab olishingizdan qoʻrqishadi.'**
  String get offerSignUrgency;

  /// Belgi 3
  ///
  /// In uz, this message translates to:
  /// **'Daromad moldan emas, yangi odam olib kelishdan.'**
  String get offerSignRecruit;

  /// Belgi 4
  ///
  /// In uz, this message translates to:
  /// **'Ishning oʻzi koʻrinmaydi: mol, hujjat yoki ruxsat yoʻq, faqat idora.'**
  String get offerSignNoBusiness;

  /// Belgi 5
  ///
  /// In uz, this message translates to:
  /// **'Kirish oson, chiqish qiyin.'**
  String get offerSignHardExit;

  /// Toifa: ribo
  ///
  /// In uz, this message translates to:
  /// **'Ribo: zarar boʻlishilmaydigan kafolatli foyda.'**
  String get offerCatRibo;

  /// Toifa: g'arar
  ///
  /// In uz, this message translates to:
  /// **'Gʻarar: noaniq bitim — nima sotilayotgani, pul qayerda ishlayotgani nomaʼlum.'**
  String get offerCatGharar;

  /// Toifa: qimor
  ///
  /// In uz, this message translates to:
  /// **'Qimor: yutuq faqat boshqaning yutqazishidan — toʻlov yangi kirganlarning pulidan.'**
  String get offerCatQimor;

  /// Piramida bo'limi
  ///
  /// In uz, this message translates to:
  /// **'Piramida qanday choʻkadi?'**
  String get offerPyramidTitle;

  /// Piramida: k
  ///
  /// In uz, this message translates to:
  /// **'Har kishi necha odam olib keladi'**
  String get offerPyramidRecruits;

  /// Piramida: N
  ///
  /// In uz, this message translates to:
  /// **'Shahar aholisi'**
  String get offerPyramidPopulation;

  /// Piramida natijasi
  ///
  /// In uz, this message translates to:
  /// **'{levels}-qavatda odam tugaydi. Eng pastki qavatda {share} % odam boʻladi — choʻkkan kuni ular pulini yoʻqotadi. Siz qaysi qavatda boʻlasiz?'**
  String offerPyramidResult(int levels, Object share);

  /// Piramida: yem
  ///
  /// In uz, this message translates to:
  /// **'Birinchi kirganlarga toʻlov — boshqalarni jalb qilish uchun: u yangi kirganlarning pulidan toʻlanadi.'**
  String get offerPyramidBait;

  /// Qaror bo'limi
  ///
  /// In uz, this message translates to:
  /// **'Qaror'**
  String get offerDecisionTitle;

  /// Maslahatchi maydoni
  ///
  /// In uz, this message translates to:
  /// **'Kim bilan maslahatlashdingiz?'**
  String get offerAdvisor;

  /// Maslahat izohi
  ///
  /// In uz, this message translates to:
  /// **'Maslahat soʻrash — zaiflik emas. Bir kecha uxlab koʻring: bir soat vaqt ajratish yillik mehnatni asraydi.'**
  String get offerAdviceNote;

  /// Qaror: rad
  ///
  /// In uz, this message translates to:
  /// **'Rad etdim'**
  String get offerDecline;

  /// Qaror: keyinga
  ///
  /// In uz, this message translates to:
  /// **'Keyinga qoldiraman'**
  String get offerPostpone;

  /// Qaror: qabul
  ///
  /// In uz, this message translates to:
  /// **'Pul qoʻyaman'**
  String get offerAccept;

  /// 24 soat cheklovi
  ///
  /// In uz, this message translates to:
  /// **'«Pul qoʻyaman» {time} dan keyin ochiladi.'**
  String offerAcceptOpensAt(Object time);

  /// Tarix: rad
  ///
  /// In uz, this message translates to:
  /// **'Rad etildi'**
  String get offerDecisionDeclined;

  /// Tarix: keyinga
  ///
  /// In uz, this message translates to:
  /// **'Keyinga qoldirildi'**
  String get offerDecisionPostponed;

  /// Tarix: qabul
  ///
  /// In uz, this message translates to:
  /// **'Pul qoʻyildi'**
  String get offerDecisionAccepted;

  /// Qaror saqlandi
  ///
  /// In uz, this message translates to:
  /// **'Qaror yozildi.'**
  String get offerDecisionSaved;

  /// Xato: maslahatchi
  ///
  /// In uz, this message translates to:
  /// **'Avval kim bilan maslahatlashganingizni yozing.'**
  String get offerErrAdvisor;

  /// Xato: 24 soat
  ///
  /// In uz, this message translates to:
  /// **'Tekshiruvdan keyin 24 soat oʻtmaguncha bu qaror ochilmaydi.'**
  String get offerErrCoolingOff;

  /// Xato: qaror bor
  ///
  /// In uz, this message translates to:
  /// **'Bu taklif boʻyicha qaror allaqachon qabul qilingan.'**
  String get offerErrDecided;

  /// Xato: foiz
  ///
  /// In uz, this message translates to:
  /// **'Foizni toʻgʻri yozing (masalan, 35 yoki 2,5).'**
  String get offerErrRate;

  /// Katta summa ekrani
  ///
  /// In uz, this message translates to:
  /// **'Katta summa tushdi'**
  String get lumpTitle;

  /// Katta summa izohi
  ///
  /// In uz, this message translates to:
  /// **'Katta summa qoʻlga kirdimi (yillar davomidagi jamgʻarma, meros yoki mulk sotuvi)? Avval oilaning olti oylik zaxirasini toʻldiring, qolganini hunarga ishlating.'**
  String get lumpHint;

  /// Summa
  ///
  /// In uz, this message translates to:
  /// **'Summa'**
  String get lumpAmount;

  /// Kurs maydoni
  ///
  /// In uz, this message translates to:
  /// **'Kurs: 1 {currency} necha soʻm'**
  String lumpRate(Object currency);

  /// Zaxiraga
  ///
  /// In uz, this message translates to:
  /// **'Oilaviy zaxiraga (6 oy): {amount}'**
  String lumpReserve(Object amount);

  /// Sarmoyaga
  ///
  /// In uz, this message translates to:
  /// **'Hunarga ishlatish mumkin: {amount}'**
  String lumpInvest(Object amount);

  /// Zaxira izohi
  ///
  /// In uz, this message translates to:
  /// **'Bu pulni savdoga ham, sheriklikka ham qoʻshmaysiz.'**
  String get lumpWallNote;

  /// Zaxira to'la
  ///
  /// In uz, this message translates to:
  /// **'Oilaviy zaxira allaqachon toʻla — hammasini hunarga ishlatsa boʻladi.'**
  String get lumpReserveFull;

  /// Maqsad yo'q
  ///
  /// In uz, this message translates to:
  /// **'Avval 6 oylik zarur xarajatni belgilang — shunda zaxira qancha boʻlishi kerakligi maʼlum boʻladi.'**
  String get lumpNoTarget;

  /// Qorovulga qo'yish tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Zaxiraga qoʻyish'**
  String get lumpDeposit;

  /// Qo'yildi
  ///
  /// In uz, this message translates to:
  /// **'Zaxiraga qoʻyildi.'**
  String get lumpDeposited;

  /// G'oyalarga o'tish
  ///
  /// In uz, this message translates to:
  /// **'Hunardan ishga oʻtish'**
  String get lumpIdeas;

  /// Kelajagim ekranidagi tugma
  ///
  /// In uz, this message translates to:
  /// **'Katta summa tushdimi?'**
  String get lumpOpen;

  /// G'oya shabloni
  ///
  /// In uz, this message translates to:
  /// **'Shablon: payvandlash ustaxonasi'**
  String get ideaTplWorkshop;

  /// CAPEX: payvand
  ///
  /// In uz, this message translates to:
  /// **'Payvand apparati'**
  String get ideaTplWelder;

  /// CAPEX: kesish
  ///
  /// In uz, this message translates to:
  /// **'Kesish asbobi (bolgarka)'**
  String get ideaTplGrinder;

  /// CAPEX: ijara
  ///
  /// In uz, this message translates to:
  /// **'Ustaxona ijarasi (birinchi oy)'**
  String get ideaTplRent;

  /// CAPEX: metall
  ///
  /// In uz, this message translates to:
  /// **'Metall (birinchi buyurtmalar uchun)'**
  String get ideaTplMetal;

  /// CAPEX: himoya
  ///
  /// In uz, this message translates to:
  /// **'Himoya kiyimi va niqob'**
  String get ideaTplSafety;

  /// Talab savoli
  ///
  /// In uz, this message translates to:
  /// **'Talab bormi? Kim buyurtma beradi, atrofda qancha uy qurilmoqda yoki yangilanmoqda?'**
  String get ideaDemandQ;

  /// Shablon tavsiyalari
  ///
  /// In uz, this message translates to:
  /// **'Kerak boʻladiganlar — bosing va narxini yozing:'**
  String get ideaTplSuggest;

  /// «Ilova haqida» ekrani
  ///
  /// In uz, this message translates to:
  /// **'Ilova haqida'**
  String get aboutTitle;

  /// Sozlamalar: Ilova haqida
  ///
  /// In uz, this message translates to:
  /// **'Versiya, muallif va huquqlar'**
  String get settingsAboutHint;

  /// Versiya
  ///
  /// In uz, this message translates to:
  /// **'Versiya {version} ({build})'**
  String aboutVersion(String version, int build);

  /// Muallif
  ///
  /// In uz, this message translates to:
  /// **'Muallif: {author}'**
  String aboutAuthor(String author);

  /// Mualliflik huquqi
  ///
  /// In uz, this message translates to:
  /// **'© {year} {author}. Barcha huquqlar himoyalangan.'**
  String aboutCopyright(String year, String author);

  /// Huquqlar izohi
  ///
  /// In uz, this message translates to:
  /// **'Ilovani nusxalash, oʻzgartirish, tarqatish yoki muallifning yozma ruxsatisiz nashr qilish taqiqlanadi.'**
  String get aboutRights;

  /// Maxfiylik
  ///
  /// In uz, this message translates to:
  /// **'Maʼlumotlaringiz faqat shu qurilmada, shifrlangan holda saqlanadi. Ilova internetga ulanmaydi.'**
  String get aboutPrivacy;

  /// Litsenziyalar tugmasi
  ///
  /// In uz, this message translates to:
  /// **'Ochiq kodli kutubxonalar litsenziyalari'**
  String get aboutLicenses;

  /// Demo lentasi
  ///
  /// In uz, this message translates to:
  /// **'DEMO'**
  String get demoBanner;

  /// Demo: pastki yozuv
  ///
  /// In uz, this message translates to:
  /// **'Demo versiya · © {year} {author} · nashr qilish va tarqatish taqiqlanadi'**
  String demoNotice(String year, String author);

  /// Demo muddati
  ///
  /// In uz, this message translates to:
  /// **'Demo versiya: {date} gacha ishlaydi'**
  String demoUntil(String date);

  /// Demo tugadi: sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Demo muddati tugadi'**
  String get demoExpiredTitle;

  /// Demo tugadi: matn
  ///
  /// In uz, this message translates to:
  /// **'Bu demo versiya {date} gacha ishlashi kerak edi. Toʻliq versiya uchun muallif bilan bogʻlaning: {author}.'**
  String demoExpiredBody(String date, String author);

  /// 8-qonun ekrani sarlavhasi
  ///
  /// In uz, this message translates to:
  /// **'Bilimga sarmoya'**
  String get lnTitle;

  /// 8-qonun ekrani izohi
  ///
  /// In uz, this message translates to:
  /// **'Bir soatingiz qancha turishini biling va uni qimmatlashtiradigan bilimni aniq maqsad bilan oʻrganing.'**
  String get lnHint;

  /// Soat qiymati bo'limi
  ///
  /// In uz, this message translates to:
  /// **'Bir soatim qancha turadi?'**
  String get lnHourlyTitle;

  /// Soat qiymati yo'q
  ///
  /// In uz, this message translates to:
  /// **'Hali hisoblanmagan. Oylik daromad va ish soatlaringizni kiriting.'**
  String get lnHourlyEmpty;

  /// Soat qiymati
  ///
  /// In uz, this message translates to:
  /// **'Bir soatingiz: {amount}'**
  String lnHourlyValue(String amount);

  /// Ikki barobar soat qiymati
  ///
  /// In uz, this message translates to:
  /// **'Ikki barobar maqsad: {amount}'**
  String lnHourlyDoubled(String amount);

  /// Chegaraning band qismi
  ///
  /// In uz, this message translates to:
  /// **'Kunlik chegaraning {percent} % i band'**
  String lnHourlyLoad(String percent);

  /// Soat chegarasidagi daromad
  ///
  /// In uz, this message translates to:
  /// **'Faqat soat qoʻshib erishiladigan eng katta oylik daromad: {amount}'**
  String lnHourlyCeiling(String amount);

  /// Soat bilan ikki barobar qilib bo'lmaydi
  ///
  /// In uz, this message translates to:
  /// **'Daromadni faqat soatni koʻpaytirib ikki barobar qilib boʻlmaydi — kun bunga yetmaydi. Soatning oʻzini qimmatlashtiring.'**
  String get lnHourlyNoDouble;

  /// Soat bilan ikki barobar qilish mumkin
  ///
  /// In uz, this message translates to:
  /// **'Soat qoʻshish mumkin, lekin dam olish va oilaga vaqt qolishini oʻylang. Soatni qimmatlashtirish uzoqroq xizmat qiladi.'**
  String get lnHourlyCanDouble;

  /// Soat qiymati o'zgarishi
  ///
  /// In uz, this message translates to:
  /// **'Avvalgi hisob: {old} → hozir {now}'**
  String lnHourlyChange(String old, String now);

  /// Soat qiymati izohi
  ///
  /// In uz, this message translates to:
  /// **'Soat qoʻshish bilan daromad chegaradan oshmaydi. Soatning oʻzini qimmatlashtirish — bilim va mahorat ishi.'**
  String get lnHourlyExplain;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Hisoblash'**
  String get lnHourlyCalc;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Qayta hisoblash'**
  String get lnHourlyRecalc;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Oylik daromad'**
  String get lnIncome;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Oʻtgan oy daromadi taklif qilindi'**
  String get lnIncomeSuggested;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Kuniga necha soat ishlaysiz'**
  String get lnHoursPerDay;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Oyiga necha kun ishlaysiz'**
  String get lnDaysPerMonth;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Kunlik jismoniy chegara (soat)'**
  String get lnMaxHours;

  /// Chegara izohi
  ///
  /// In uz, this message translates to:
  /// **'Dam olish, oila va sogʻliq uchun vaqt qolishi kerak. Chegarani oʻzingiz belgilang.'**
  String get lnMaxHoursHint;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Soat 0,5 dan 24 gacha, kunlar 1 dan 31 gacha boʻlsin.'**
  String get lnErrHours;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Summa yoki vaqt manfiy boʻlmaydi.'**
  String get lnErrAmount;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Oʻqish maqsadlari'**
  String get lnGoalsTitle;

  /// Maqsad yo'q
  ///
  /// In uz, this message translates to:
  /// **'Soatingizni qimmatlashtiradigan bitta bilimni tanlang.'**
  String get lnGoalsEmpty;

  /// Maqsad uchun soat qiymati kerak
  ///
  /// In uz, this message translates to:
  /// **'Avval bir soatingiz qancha turishini hisoblang.'**
  String get lnGoalsNeedHourly;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Yangi maqsad'**
  String get lnGoalNew;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Qaysi bilim yoki mahorat?'**
  String get lnGoalTitleField;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nega aynan shu? Qaysi ishni yaxshiroq qila olasiz?'**
  String get lnGoalWhy;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Maqsad soat qiymati'**
  String get lnGoalTarget;

  /// Maslahat
  ///
  /// In uz, this message translates to:
  /// **'Maslahat: bir vaqtda bitta bilimga eʼtibor qarating.'**
  String get lnGoalFocus;

  /// Boshlang'ich va maqsad soat qiymati
  ///
  /// In uz, this message translates to:
  /// **'Soatiga {from} → {to}'**
  String lnGoalRange(String from, String to);

  /// Yo'llar soni
  ///
  /// In uz, this message translates to:
  /// **'{count, plural, =0{Yoʻl qoʻshilmagan} other{{count} ta yoʻl}}'**
  String lnGoalItems(int count);

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Faol'**
  String get lnGoalStatusActive;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Erishildi'**
  String get lnGoalStatusDone;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Toʻxtatildi'**
  String get lnGoalStatusDropped;

  /// Amal
  ///
  /// In uz, this message translates to:
  /// **'Maqsadga erishdim'**
  String get lnGoalMarkDone;

  /// Amal
  ///
  /// In uz, this message translates to:
  /// **'Toʻxtataman'**
  String get lnGoalDrop;

  /// Amal
  ///
  /// In uz, this message translates to:
  /// **'Qayta faollashtirish'**
  String get lnGoalReopen;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Oʻqish yoʻllari'**
  String get lnItemsTitle;

  /// Yo'l yo'q
  ///
  /// In uz, this message translates to:
  /// **'Kitob, ustoz, kurs yoki amaliyotdan birini qoʻshing.'**
  String get lnItemsEmpty;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Yoʻl qoʻshish'**
  String get lnItemAdd;

  /// Yo'l turi
  ///
  /// In uz, this message translates to:
  /// **'Kitob'**
  String get lnKindBook;

  /// Yo'l turi
  ///
  /// In uz, this message translates to:
  /// **'Ustoz'**
  String get lnKindMentor;

  /// Yo'l turi
  ///
  /// In uz, this message translates to:
  /// **'Kurs'**
  String get lnKindCourse;

  /// Yo'l turi
  ///
  /// In uz, this message translates to:
  /// **'Amaliyot'**
  String get lnKindPractice;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nomi'**
  String get lnItemTitle;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Buni oʻrgangach nimani qila olaman?'**
  String get lnItemPurpose;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Natija aniq boʻlsa, oʻqish ham samarali boʻladi.'**
  String get lnItemPurposeHint;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Narxi'**
  String get lnItemCost;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Oʻqishga ketadigan vaqt (soat)'**
  String get lnItemStudyHours;

  /// Ogohlantirish
  ///
  /// In uz, this message translates to:
  /// **'Oʻqishni qarzga olmang: jamgʻarmadan yoki joriy daromaddan toʻlang.'**
  String get lnItemNoDebt;

  /// Yo'l maqsadi
  ///
  /// In uz, this message translates to:
  /// **'Natija: {purpose}'**
  String lnItemPurposeLabel(String purpose);

  /// Erishilgan natija
  ///
  /// In uz, this message translates to:
  /// **'Erishildi: {outcome}'**
  String lnItemOutcomeLabel(String outcome);

  /// O'qish vaqti
  ///
  /// In uz, this message translates to:
  /// **'{hours} soat'**
  String lnItemHours(String hours);

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Rejada'**
  String get lnItemStatusPlanned;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Oʻqiyapman'**
  String get lnItemStatusInProgress;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Tugatdim'**
  String get lnItemStatusDone;

  /// Holat
  ///
  /// In uz, this message translates to:
  /// **'Tashladim'**
  String get lnItemStatusDropped;

  /// Amal
  ///
  /// In uz, this message translates to:
  /// **'Boshlash'**
  String get lnItemStart;

  /// Amal
  ///
  /// In uz, this message translates to:
  /// **'Tugatdim'**
  String get lnItemFinish;

  /// Amal
  ///
  /// In uz, this message translates to:
  /// **'Tashlash'**
  String get lnItemDrop;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nimani qila oladigan boʻldingiz?'**
  String get lnItemOutcome;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Nomini yozing.'**
  String get lnErrTitle;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'«Buni oʻrgangach nimani qila olaman?» savoliga javob yozing.'**
  String get lnErrPurpose;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Erishilgan natijani yozing.'**
  String get lnErrOutcome;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Avval soat qiymatini hisoblang.'**
  String get lnErrNoHourly;

  /// Xato
  ///
  /// In uz, this message translates to:
  /// **'Kimga va nimani oʻrgatganingizni yozing.'**
  String get lnErrTeaching;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Oʻqish qachon oʻzini qoplaydi? (taxmin)'**
  String get lnPaybackTitle;

  /// Sarmoya
  ///
  /// In uz, this message translates to:
  /// **'Narx {cost} + vaqt qiymati {time} = {total}'**
  String lnPaybackInvest(String cost, String time, String total);

  /// Oylik qo'shimcha daromad
  ///
  /// In uz, this message translates to:
  /// **'Soatingiz maqsadga yetsa, oyiga qoʻshimcha: {amount}'**
  String lnPaybackGain(String amount);

  /// Qoplanish oylari
  ///
  /// In uz, this message translates to:
  /// **'{months, plural, other{Shunda xarajat taxminan {months} oyda qoplanadi.}}'**
  String lnPaybackMonths(int months);

  /// Qoplanmaydi
  ///
  /// In uz, this message translates to:
  /// **'Bu maqsad bilan xarajat qoplanmaydi — maqsad soat qiymatini qayta koʻring.'**
  String get lnPaybackNever;

  /// Xarajat yo'q
  ///
  /// In uz, this message translates to:
  /// **'Pul va vaqt xarajati yozilmagan.'**
  String get lnPaybackFree;

  /// Taxmin izohi
  ///
  /// In uz, this message translates to:
  /// **'Bu vaʼda emas — sizning raqamlaringiz boʻyicha taxmin.'**
  String get lnPaybackNote;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Kursni tekshirish'**
  String get lnCourseCheck;

  /// Sarlavha
  ///
  /// In uz, this message translates to:
  /// **'Kurs tekshiruvi: bilim beradimi?'**
  String get lnCourseTitle;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Qisqa vaqtda maʼlum daromad kafolatlanadimi?'**
  String get lnCourseQIncome;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'«Faqat bugun», «joy kam» deb shoshirishadimi?'**
  String get lnCourseQPressure;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Daromad yangi oʻquvchi olib kelishdanmi?'**
  String get lnCourseQReferral;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'«Faqat shu yerda oʻrgatiladigan maxfiy usul» deb sotiladimi?'**
  String get lnCourseQSecret;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Dastur, amaliy topshiriqlar va oxirida nimani qila olishingiz oldindan koʻrsatildimi?'**
  String get lnCourseQCurriculum;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Oʻqituvchi shu ish bilan amalda shugʻullanadimi, ishini koʻrsata oladimi?'**
  String get lnCourseQTeacher;

  /// Savol
  ///
  /// In uz, this message translates to:
  /// **'Toʻlovni qaytarish shartlari yozma bormi?'**
  String get lnCourseQRefund;

  /// Natija
  ///
  /// In uz, this message translates to:
  /// **'Xavf belgisi topilmadi. Baribir dastur va natijani yozib qoʻying.'**
  String get lnCourseGreen;

  /// Natija
  ///
  /// In uz, this message translates to:
  /// **'Hushyor boʻling: toʻlashdan oldin aniqlashtiring.'**
  String get lnCourseYellow;

  /// Natija
  ///
  /// In uz, this message translates to:
  /// **'Ikki va undan ortiq xavf belgisi — bu kursga pul toʻlamang.'**
  String get lnCourseRed;

  /// Belgi izohi
  ///
  /// In uz, this message translates to:
  /// **'Daromad kafolati: halol taʼlim natijani oʻquvchining mehnatiga bogʻlaydi, kafolatlamaydi.'**
  String get lnCourseSignIncome;

  /// Belgi izohi
  ///
  /// In uz, this message translates to:
  /// **'Shoshirish: yaxshi kurs oʻylab koʻrishga vaqt beradi.'**
  String get lnCourseSignUrgency;

  /// Belgi izohi
  ///
  /// In uz, this message translates to:
  /// **'Daromad yangi oʻquvchilardan: bu bilim emas, odam yigʻish.'**
  String get lnCourseSignReferral;

  /// Belgi izohi
  ///
  /// In uz, this message translates to:
  /// **'Haqiqiy mahorat koʻrinmaydi: dastur, amaliyot yoki oʻqituvchining ishi yoʻq.'**
  String get lnCourseSignNoSkill;

  /// Belgi izohi
  ///
  /// In uz, this message translates to:
  /// **'Qaytarish sharti yoʻq: pul toʻlangach chiqish qiyin.'**
  String get lnCourseSignRefund;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Natijani saqlash'**
  String get lnCourseSave;

  /// Tasdiq
  ///
  /// In uz, this message translates to:
  /// **'Kursda xavf belgilari bor'**
  String get lnCourseRedConfirmTitle;

  /// Tasdiq
  ///
  /// In uz, this message translates to:
  /// **'Tekshiruv qizil natija berdi. Baribir oʻqishni boshlaysizmi?'**
  String get lnCourseRedConfirmBody;

  /// Tasdiq
  ///
  /// In uz, this message translates to:
  /// **'Ha, boshlayman'**
  String get lnCourseRedConfirmYes;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Oʻrgatganlarim'**
  String get lnTeachTitle;

  /// Izoh
  ///
  /// In uz, this message translates to:
  /// **'Bilganingizni boshqaga tushuntirsangiz, oʻzingiz ham chuqurroq oʻrganasiz.'**
  String get lnTeachHint;

  /// Tugma
  ///
  /// In uz, this message translates to:
  /// **'Yozib qoʻyish'**
  String get lnTeachAdd;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Kimga (ism yoki «hamkasb», «farzandim»)'**
  String get lnTeachLearner;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Nimani oʻrgatdingiz?'**
  String get lnTeachTopic;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Qancha vaqt (daqiqa, ixtiyoriy)'**
  String get lnTeachMinutes;

  /// Maydon
  ///
  /// In uz, this message translates to:
  /// **'Izoh (ixtiyoriy)'**
  String get lnTeachNote;

  /// Bo'sh
  ///
  /// In uz, this message translates to:
  /// **'Hali yozuv yoʻq.'**
  String get lnTeachEmpty;

  /// Bo'lim
  ///
  /// In uz, this message translates to:
  /// **'Bilim odam bilan qoladi'**
  String get lnKeepTitle;

  /// Ta'limiy matn
  ///
  /// In uz, this message translates to:
  /// **'Pul va mol yoʻqolishi mumkin, oʻrganilgan mahorat esa siz bilan qoladi. Narxlar oshganda yoki ish oʻzgarganda u yangi yoʻl topishga yordam beradi.'**
  String get lnKeepBody;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['ru', 'uz'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'ru':
      return AppLocalizationsRu();
    case 'uz':
      return AppLocalizationsUz();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}

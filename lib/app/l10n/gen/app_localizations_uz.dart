// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Uzbek (`uz`).
class AppLocalizationsUz extends AppLocalizations {
  AppLocalizationsUz([String locale = 'uz']) : super(locale);

  @override
  String get appTitle => 'Baraka Dastur';

  @override
  String get languageName => 'Oʻzbekcha';

  @override
  String get switchLanguageTooltip => 'Tilni almashtirish';

  @override
  String get switchThemeTooltip => 'Mavzuni almashtirish';

  @override
  String get placeholderNotice => 'Bu ekran keyingi vazifalarda toʻldiriladi.';

  @override
  String get homeTitle => 'Bosh sahifa';

  @override
  String get homeDescription =>
      'Bu yerda «Oʻzingizga toʻlangan» summa, «Kelajagim» balansi va haftalik vazifalar boʻladi.';

  @override
  String get homeSectionsHeader => 'Boʻlimlar';

  @override
  String get incomeNewTitle => 'Yangi daromad';

  @override
  String get incomeNewDescription =>
      'Bu yerda daromad bir necha bosishda kiritiladi.';

  @override
  String get vaultTitle => 'Kelajagim';

  @override
  String get vaultDescription =>
      'Bu yerda «Kelajagim» jamgʻarmasi balansi va odat ketma-ketligi boʻladi.';

  @override
  String get auditTitle => 'Oylik audit';

  @override
  String get auditDescription =>
      'Bu yerda «Pul qayerga ketdi?» degan savolga javob topiladi.';

  @override
  String get contentTitle => 'Boblar';

  @override
  String get nativeBridgeTitle => 'Xavfsizlik koʻprigi';

  @override
  String get nativeBridgeChecking => 'Tekshirilmoqda…';

  @override
  String nativeBridgeOk(int apiVersion, int sdkInt) {
    return 'Ishlayapti · API v$apiVersion · Android SDK $sdkInt';
  }

  @override
  String get nativeBridgeUnavailable => 'Native qatlam bilan aloqa yoʻq';

  @override
  String get lockEnterPin => 'PIN kodni kiriting';

  @override
  String get lockGreeting => 'Daftaringiz qulflangan';

  @override
  String pinWrong(int attempts) {
    return 'Kod mos kelmadi. Kutish vaqtigacha yana $attempts ta urinish bor.';
  }

  @override
  String pinLockedOut(String time) {
    return 'Juda koʻp notoʻgʻri urinish boʻldi. $time dan keyin qayta urinib koʻring.';
  }

  @override
  String get pinVerifying => 'Tekshirilmoqda…';

  @override
  String get pinErrorGeneric => 'Nimadir xato ketdi. Qaytadan urinib koʻring.';

  @override
  String get pinKeyDelete => 'Oxirgi raqamni oʻchirish';

  @override
  String get pinKeyBiometric => 'Barmoq izi bilan kirish';

  @override
  String pinDigitsEntered(int count) {
    return '$count / 6 raqam kiritildi';
  }

  @override
  String get pinSetupTitle => 'PIN kod oʻrnatish';

  @override
  String get pinSetupEnter =>
      'Daftaringizni himoyalash uchun 6 xonali kod oʻylab toping';

  @override
  String get pinSetupConfirm => 'Kodni yana bir marta kiriting';

  @override
  String get pinSetupMismatch =>
      'Kodlar mos kelmadi. Keling, qaytadan boshlaymiz.';

  @override
  String get pinTooSimple => 'Bu kodni topish oson. Boshqa raqamlarni tanlang.';

  @override
  String get pinSetupNote =>
      'Kodning oʻzi hech qayerda saqlanmaydi. Uni unutmang — tiklash imkoni yoʻq.';

  @override
  String get pinSetupSaving => 'Saqlanmoqda…';

  @override
  String get biometricOfferTitle => 'Barmoq izi bilan kirish';

  @override
  String get biometricOfferBody =>
      'Har safar kod kiritmasdan, barmoq izi yoki qurilma qulfi bilan kirishingiz mumkin. Buni istalgan vaqtda oʻchirsa boʻladi.';

  @override
  String get biometricEnable => 'Yoqish';

  @override
  String get biometricLater => 'Hozircha kerak emas';

  @override
  String get biometricPromptTitle => 'Baraka Dastur';

  @override
  String get biometricPromptSubtitle => 'Daftaringizni ochish uchun tasdiqlang';

  @override
  String get biometricPromptCancel => 'Kod bilan kirish';

  @override
  String get biometricLockedOut =>
      'Barmoq izi vaqtincha bloklangan. Kod bilan kiring.';

  @override
  String get integrityTitle => 'Qurilmada xavf belgilari bor';

  @override
  String integrityBody(String risks) {
    return 'Ilova ishlayveradi, lekin bunday qurilmada maʼlumotlaringiz xavfsizligini toʻliq kafolatlab boʻlmaydi. Aniqlangan: $risks.';
  }

  @override
  String get integrityRiskRooted => 'root huquqlari';

  @override
  String get integrityRiskEmulator => 'emulyator';

  @override
  String get integrityRiskDebugger => 'ulangan debugger';

  @override
  String get integrityRiskSignature => 'ilova imzosi mos emas';

  @override
  String get integrityRiskDebuggable => 'ilova oʻzgartirilgan boʻlishi mumkin';

  @override
  String get integrityDismiss => 'Tushunarli';

  @override
  String get homeAddIncome => 'Daromad';

  @override
  String get incomeAmountHint => 'Summani kiriting';

  @override
  String get incomeRecentAmounts => 'Oxirgi summalar';

  @override
  String get incomeSourceLabel => 'Manba';

  @override
  String get incomeSourceDailyWork => 'Kunlik ish';

  @override
  String get incomeSourceOrder => 'Buyurtma';

  @override
  String get incomeSourceSalary => 'Oylik';

  @override
  String get incomeSourceOther => 'Boshqa';

  @override
  String get channelLabel => 'Toʻlov turi';

  @override
  String get channelCash => 'Naqd';

  @override
  String get channelCard => 'Karta';

  @override
  String get incomeSave => 'Saqlash';

  @override
  String get incomeSaved => 'Daromad yozildi. Barakali boʻlsin!';

  @override
  String get keypadDelete => 'Oxirgi raqamni oʻchirish';

  @override
  String get shareOfferTitle => 'Avval oʻzingizga';

  @override
  String shareOfferBody(String amount) {
    return 'Shundan $amount — kelajagingiz uchun.';
  }

  @override
  String get shareOfferHint =>
      'Oz boʻlsa ham har gal ajratsangiz, odatga aylanadi.';

  @override
  String get shareAllocate => 'Ajratish';

  @override
  String get shareOtherAmount => 'Boshqa summa';

  @override
  String get shareSkip => 'Bu safar emas';

  @override
  String get shareSkipped => 'Mayli, keyingi safar. Daftar sizni kutadi.';

  @override
  String shareDone(String amount) {
    return 'Kelajagingizga $amount qoʻshildi.';
  }

  @override
  String vaultHabitWeeks(int count) {
    return '$count hafta';
  }

  @override
  String get vaultHabitCaption => 'ketma-ket oʻzingizga toʻladingiz';

  @override
  String vaultHabitTotal(int count) {
    return 'Jami $count hafta ajratilgan';
  }

  @override
  String get vaultThisWeekDone => 'Bu hafta ajratildi — barakalla!';

  @override
  String get vaultThisWeekPending =>
      'Bu hafta hali ajratilmadi. Oz summa ham hisobga oʻtadi.';

  @override
  String get vaultBalanceLabel => 'Kelajagim jamgʻarmasida';

  @override
  String vaultRuleSummaryPercent(String percent) {
    return 'Ulush: har daromaddan $percent %';
  }

  @override
  String vaultRuleSummaryFixed(String amount) {
    return 'Ulush: oyiga $amount';
  }

  @override
  String get vaultRuleProgressiveTag => 'progressiv';

  @override
  String get vaultRuleEdit => 'Ulushni sozlash';

  @override
  String get vaultWithdraw => 'Pul olish';

  @override
  String get vaultHistory => 'Tarix';

  @override
  String get vaultHistoryEmpty =>
      'Hali yozuv yoʻq. Birinchi daromaddan boshlaymiz.';

  @override
  String get vaultReasonIncomeShare => 'Daromad ulushi';

  @override
  String get vaultReasonInitial => 'Boshlangʻich jamgʻarma';

  @override
  String get vaultReasonManual => 'Qoʻshildi';

  @override
  String vaultReasonWithdrawal(String note) {
    return 'Olindi: $note';
  }

  @override
  String get vaultInitialTitle => 'Avval yigʻilgan pul';

  @override
  String get vaultInitialBody =>
      'Ilovadan oldin yigʻib qoʻygan pulingiz bormi? Uni bir marta kiritib qoʻying — hisob toʻliq boʻladi.';

  @override
  String get vaultInitialAction => 'Kiritish';

  @override
  String get vaultInitialSaved => 'Boshlangʻich jamgʻarma yozildi.';

  @override
  String get vaultProgressionTitle => 'Barakalla!';

  @override
  String vaultProgressionBody(int weeks, String percent) {
    return '$weeks hafta ketma-ket oʻzingizga toʻladingiz. Ulushni $percent % ga oshirasizmi?';
  }

  @override
  String get vaultProgressionAccept => 'Oshirish';

  @override
  String get vaultProgressionDecline => 'Hozircha yoʻq';

  @override
  String get ruleTitle => 'Ulush sozlamalari';

  @override
  String get rulePercent5 => '5 % — boshlangʻich';

  @override
  String get rulePercent10 => '10 % — maqsad (daromadning oʻndan biri)';

  @override
  String get ruleFixed => 'Qatʼiy summa — oyiga';

  @override
  String ruleFixedAmount(String amount) {
    return 'Oylik summa: $amount';
  }

  @override
  String get ruleFixedChoose => 'Summani tanlang';

  @override
  String get ruleProgressive => 'Progressiv rejim';

  @override
  String get ruleProgressiveHint =>
      '4 hafta ketma-ket ajratsangiz, ulushni 1 % ga oshirishni taklif qilamiz (10 % gacha).';

  @override
  String get ruleSave => 'Saqlash';

  @override
  String get ruleSaved => 'Ulush yangilandi.';

  @override
  String get withdrawTitle => 'Kelajagimdan pul olish';

  @override
  String get withdrawReminder =>
      'Bu pul — kelajakdagi oʻzingizniki. Uni faqat chinakam zarurat uchun oling.';

  @override
  String withdrawAvailable(String amount) {
    return 'Mavjud: $amount';
  }

  @override
  String get withdrawAmountLabel => 'Qancha olasiz? (soʻm)';

  @override
  String get withdrawReasonLabel => 'Nima uchun? (majburiy)';

  @override
  String get withdrawReasonHint => 'Masalan: davolanish, uy taʼmiri';

  @override
  String get withdrawContinue => 'Davom etish';

  @override
  String get withdrawPauseTitle => 'Bir oz oʻylab koʻraylik';

  @override
  String withdrawPauseBody(String amount) {
    return '$amount kelajagingizdan olinadi. Bu haqiqatan zarurmi?';
  }

  @override
  String withdrawPauseWait(int seconds) {
    return 'Ha, olaman ($seconds)';
  }

  @override
  String get withdrawPauseConfirm => 'Ha, olaman';

  @override
  String get withdrawPauseCancel => 'Fikrimdan qaytdim';

  @override
  String withdrawDone(String amount) {
    return '$amount olindi. Imkon boʻlganda oʻrnini toʻldiramiz.';
  }

  @override
  String get withdrawErrorAmount => 'Summa mavjud balansdan oshmasin.';

  @override
  String get pinConfirmTitle => 'PIN kodni qayta kiriting';

  @override
  String get cancel => 'Bekor qilish';

  @override
  String get amountDialogTitle => 'Summa';

  @override
  String get amountDialogDone => 'Tayyor';

  @override
  String get genericError => 'Nimadir xato ketdi. Qaytadan urinib koʻring.';

  @override
  String get homePaidToSelf => 'Oʻzingizga toʻlangan (shu oy)';

  @override
  String get homeVaultBalance => 'Kelajagim';

  @override
  String homeStreak(int count) {
    return '$count hafta ketma-ket';
  }

  @override
  String get homeMonthResult => 'Oy yakuni';

  @override
  String get homeMonthResultPlus => 'Qoʻlingizda qolishi kerak';

  @override
  String get homeMonthResultMinus => 'Chiqim kirimdan koʻp yozilgan';

  @override
  String get homeWeeklyTasks => 'Shu haftaning vazifalari';

  @override
  String get homeAddExpense => 'Xarajat';

  @override
  String homeAuditDue(String month) {
    return '$month uchun oylik audit — «Pul qayerga ketdi?»';
  }

  @override
  String homeAuditDone(String month) {
    return 'Oxirgi audit: $month';
  }

  @override
  String get sectionExpenses => 'Xarajatlar';

  @override
  String get sectionObligations => 'Majburiyatlar';

  @override
  String get sectionNasiya => 'Nasiya daftari';

  @override
  String get sectionWhoseMoney => 'Kimning puli?';

  @override
  String get sectionMembers => 'Oila aʼzolari';

  @override
  String get sectionSettings => 'Sozlamalar';

  @override
  String get catRent => 'Ijara';

  @override
  String get catCredit => 'Kredit';

  @override
  String get catGroceries => 'Oziq-ovqat';

  @override
  String get catUtilities => 'Kommunal';

  @override
  String get catPhone => 'Telefon';

  @override
  String get catFuel => 'Benzin';

  @override
  String get catTransport => 'Yoʻlkira';

  @override
  String get catDailySmall => 'Mayda kundalik xarajatlar';

  @override
  String get catChildren => 'Bola';

  @override
  String get catSadaqa => 'Sadaqa';

  @override
  String get catOther => 'Boshqa';

  @override
  String get expenseNewTitle => 'Yangi xarajat';

  @override
  String get expenseCategory => 'Kategoriya';

  @override
  String get expenseSaved =>
      'Xarajat yozildi. Har bir soʻmni yozish — pulga egalikning boshi.';

  @override
  String get expensesTitle => 'Shu oyning xarajatlari';

  @override
  String get expensesEmpty => 'Bu oy hali xarajat yozilmagan.';

  @override
  String expensesTotal(String amount) {
    return 'Jami: $amount';
  }

  @override
  String get memberLabel => 'Kim';

  @override
  String get delete => 'Oʻchirish';

  @override
  String get save => 'Saqlash';

  @override
  String get obligationsEmpty =>
      'Doimiy toʻlovlarni kiriting: ijara, kredit, kommunal. Toʻlovdan bir kun oldin eslatamiz.';

  @override
  String get obligationAdd => 'Majburiyat qoʻshish';

  @override
  String get obligationEdit => 'Majburiyatni tahrirlash';

  @override
  String get obligationTitleLabel => 'Nomi';

  @override
  String get obligationKindLabel => 'Turi';

  @override
  String get obligationDayLabel => 'Har oy nechanchi kuni?';

  @override
  String obligationDay(int day) {
    return 'Har oy $day-sana';
  }

  @override
  String obligationsMonthly(String amount) {
    return 'Oyiga jami: $amount';
  }

  @override
  String get kindRent => 'Ijara';

  @override
  String get kindCredit => 'Kredit';

  @override
  String get kindUtility => 'Kommunal';

  @override
  String get kindPhone => 'Telefon';

  @override
  String get kindFuel => 'Benzin';

  @override
  String get kindOther => 'Boshqa';

  @override
  String get reminderChannel => 'Toʻlov eslatmalari';

  @override
  String reminderTitle(String title) {
    return 'Ertaga toʻlov: $title';
  }

  @override
  String reminderBody(String title) {
    return 'Eslatma: ertaga «$title» toʻlov kuni. Oldindan tayyorlab qoʻysangiz, koʻngil xotirjam boʻladi.';
  }

  @override
  String get notificationsOff =>
      'Bildirishnomalar oʻchirilgan — eslatmalar kelmaydi.';

  @override
  String get notificationsEnable => 'Yoqish';

  @override
  String get nasiyaEmpty =>
      'Doʻkondan nasiyaga olgan narsalaringizni shu yerga yozing — kimga qancha qarzingiz borligi koʻrinib turadi.';

  @override
  String get nasiyaAdd => 'Nasiya qoʻshish';

  @override
  String get nasiyaShopLabel => 'Doʻkon yoki kimga';

  @override
  String nasiyaTotal(String amount) {
    return 'Jami nasiya: $amount';
  }

  @override
  String nasiyaRemaining(String amount) {
    return 'Qoldiq: $amount';
  }

  @override
  String nasiyaDue(String date) {
    return 'Muddati: $date';
  }

  @override
  String get nasiyaPay => 'Toʻlov';

  @override
  String get nasiyaPaid => 'Yopildi — barakalla!';

  @override
  String get nasiyaDueLabel => 'Qachongacha (ixtiyoriy)';

  @override
  String get nasiyaAmountLabel => 'Summa';

  @override
  String auditPeriod(String start, String end) {
    return 'Davr: $start — $end';
  }

  @override
  String get auditStepIncome => 'Daromad';

  @override
  String get auditStepObligations => 'Majburiyatlar';

  @override
  String get auditStepExpenses => 'Xarajatlar';

  @override
  String get auditStepResult => 'Natija';

  @override
  String get auditIncomeHint =>
      'Oʻtgan oyda qancha daromad boʻldi? Yozilmaganini qoʻshing.';

  @override
  String get auditAddIncome => 'Yozilmagan daromad qoʻshish';

  @override
  String get auditObligationsHint =>
      'Bu toʻlovlar oyida toʻlangan deb hisoblanadi. Xarajat sifatida yozilgan qismi ikki marta sanalmaydi.';

  @override
  String auditObligationLine(String title, String amount, String recorded) {
    return '$title: $amount (yozilgan: $recorded)';
  }

  @override
  String get auditExpensesHint =>
      'Har bir kategoriya boʻyicha esingizda qolganini qoʻshing.';

  @override
  String auditAddTo(String category) {
    return '${category}ga qoʻshish';
  }

  @override
  String get auditIncome => 'Daromad';

  @override
  String get auditObligations => 'Majburiyatlar';

  @override
  String get auditExpenses => 'Kiritilgan xarajatlar';

  @override
  String get auditSavings => 'Jamgʻarma';

  @override
  String get auditUnexplained => 'Izohsiz qolgan summa';

  @override
  String get auditUnexplainedHint =>
      'Bu pul qayerga ketgani nomaʼlum. Koʻpincha u mayda kundalik xarajatlar — somsa, ichimlik, yoʻl-yoʻlakay xaridlar.';

  @override
  String get auditNegativeHint =>
      'Chiqim kirimdan koʻp yozilgan. Ehtimol, daromadning bir qismi kiritilmagan.';

  @override
  String get auditMarkSmall => 'Mayda kundalik xarajat deb belgilash';

  @override
  String get auditDistribute => 'Kategoriyalarga taqsimlash';

  @override
  String get auditFinish => 'Auditni yakunlash';

  @override
  String get auditFinished =>
      'Audit yakunlandi. Pul qayerga ketganini bilish — uni boshqarishning boshi.';

  @override
  String get next => 'Keyingi';

  @override
  String get back => 'Orqaga';

  @override
  String whoseIntro(String month) {
    return '$month: daromadingiz kimlarga ketdi';
  }

  @override
  String get whoseEmpty => 'Bu oy uchun hali maʼlumot yoʻq.';

  @override
  String get ownerLandlord => 'Uy egasiniki';

  @override
  String get ownerBank => 'Bankniki';

  @override
  String get ownerShop => 'Doʻkondorniki';

  @override
  String get ownerUtilities => 'Davlatniki (kommunal)';

  @override
  String get ownerFuel => 'Yoqilgʻiniki';

  @override
  String get ownerSelf => 'Oʻzingizniki';

  @override
  String get ownerSadaqa => 'Sadaqa';

  @override
  String get ownerOther => 'Boshqalar';

  @override
  String get ownerUnexplained => 'Izohsiz';

  @override
  String whosePercent(String percent) {
    return '$percent %';
  }

  @override
  String get memberOwnerDefault => 'Men';

  @override
  String get memberOwnerTag => 'egasi';

  @override
  String get memberChildTag => 'bola';

  @override
  String get memberAdd => 'Aʼzo qoʻshish';

  @override
  String get memberName => 'Ismi';

  @override
  String get memberIsChild => 'Bola';

  @override
  String get membersHint =>
      'Byudjetni birga toʻldiring — «Yolgʻiz yozmang». Har yozuvda kim kiritgani koʻrinadi.';

  @override
  String get settingsMonthStart => 'Oylik kuni';

  @override
  String settingsMonthStartHint(int day) {
    return 'Oylik davr shu kundan boshlanadi: $day-sana';
  }

  @override
  String get contentDisclaimer =>
      'Taʼlimiy material. Fatvo yoki moliyaviy maslahat emas.';

  @override
  String get contentAdvisor => 'Maslahatchi';

  @override
  String get contentLoadError =>
      'Boblarni yuklab boʻlmadi. Ilovaning keyingi yangilanishida tuzatiladi.';

  @override
  String chapterLocked(String date) {
    return '$date kuni ochiladi';
  }

  @override
  String chapterLockedTasks(int count) {
    return 'Oldingi bobdan yana $count ta vazifa bajarilsa ochiladi';
  }

  @override
  String get chapterOpen => 'Ochiq';

  @override
  String lawLabel(int number) {
    return '$number-qonun';
  }

  @override
  String get daftarPageTitle => 'Daftar sahifasi';

  @override
  String get daftarPageHint =>
      'Qonunni oʻz qoʻlingiz bilan, oʻz soʻzlaringiz bilan yozing. Qoʻl bilan yozilgan narsa esda qoladi.';

  @override
  String get daftarPageSaved => 'Daftaringizga yozildi.';

  @override
  String get daftarPageWritten => 'Yozilgan';

  @override
  String get weeklyTasksTitle => 'Shu haftaning vazifalari';

  @override
  String weeklyTasksProgress(int done) {
    return '$done / 3 bajarildi';
  }

  @override
  String get taskAuto => 'ilova oʻzi belgiladi';

  @override
  String get religiousPending =>
      'Ulamo tekshiruvida — faqat test rejimida koʻrinadi';

  @override
  String religiousSource(String source) {
    return 'Manba: $source';
  }

  @override
  String get weeklyChannel => 'Haftalik bob';

  @override
  String get weeklyNotificationTitle => 'Bugun juma — haftalik yakun';

  @override
  String get weeklyNotificationBody =>
      'Yangi bob ochilgan boʻlishi mumkin. Oʻtgan haftaning vazifalarini birga koʻrib chiqaylik.';

  @override
  String get catSnacks => 'Ichimlik va gazak';

  @override
  String get catCafe => 'Choyxona va kafe';

  @override
  String get necessityLabel => 'Toifa';

  @override
  String get necessityZarur => 'Zarur';

  @override
  String get necessityKerak => 'Kerak';

  @override
  String get necessityHavas => 'Havas';

  @override
  String get necessityNone => 'Toifadan tashqari';

  @override
  String get necessitySadaqaNote =>
      'Sadaqa havas emas va «oqib ketish» hisobiga kirmaydi.';

  @override
  String get expenseFlagsLabel => 'Belgilar';

  @override
  String get flagGift => 'Sovgʻa — hisobga kirmaydi';

  @override
  String get flagOstentation => 'Obroʻ uchun';

  @override
  String get flagDebt => 'Qarzga olingan pul bilan';

  @override
  String get debtHavasFlag => 'Qarz bilan qilingan havas';

  @override
  String get habitLabel => 'Odat';

  @override
  String get habitNone => 'Yoʻq';

  @override
  String get quickTitle => 'Tez yozish';

  @override
  String get quickEmpty =>
      'Tez-tez qiladigan xarajatingizni (somsa, choy, benzin) shablon qiling — keyin bir bosishda yoziladi.';

  @override
  String get repeatLast => 'Oxirgisini takrorlash';

  @override
  String repeatLastDone(String amount) {
    return 'Takrorlandi: $amount';
  }

  @override
  String templateRecorded(String title, String amount) {
    return '$title yozildi — $amount';
  }

  @override
  String get undo => 'Bekor qilish';

  @override
  String get templatesTitle => 'Shablonlar';

  @override
  String get templateAdd => 'Shablon qoʻshish';

  @override
  String get templateTitleLabel => 'Nomi (masalan, Somsa)';

  @override
  String get templateFromForm => 'Shablon sifatida ham saqlash';

  @override
  String get categoriesTitle => 'Kategoriyalar va toifalar';

  @override
  String get categoriesHint =>
      'Har kategoriyaning standart toifasi bor. Oʻzgartirsangiz, yangi xarajatlarga qoʻllanadi; kim va qachon oʻzgartirgani saqlanadi.';

  @override
  String get categoryHistory => 'Oʻzgarishlar tarixi';

  @override
  String get categoryHistoryEmpty => 'Hali oʻzgartirilmagan';

  @override
  String categoryHistoryItem(String date, String from, String to, String who) {
    return '$date · $from → $to · $who';
  }

  @override
  String get whoChanges => 'Kim oʻzgartiryapti?';

  @override
  String get rollupTitle => 'Mayda xarajatlar jamlanganda';

  @override
  String get rollupWindow => 'Oxirgi 30 kun boʻyicha prognoz';

  @override
  String rollupLine(String week, String month, String year) {
    return 'haftasiga $week · oyiga $month · yiliga $year';
  }

  @override
  String rollupShare(String obligation, String percent) {
    return 'Oyiga — «$obligation»ning $percent%i';
  }

  @override
  String get havasTitle => 'Havas va odatlar';

  @override
  String get havasRule =>
      'Havasni oʻldirma, navbatga qoʻy. Chegara oiladagi barcha kattalar rozi boʻlgandagina faol boʻladi; bloklash yoʻq.';

  @override
  String get havasNoLimit => 'Havas uchun oylik chegara hali kelishilmagan.';

  @override
  String havasSpent(String amount) {
    return 'Shu oy havasga: $amount';
  }

  @override
  String havasOfLimit(String spent, String limit) {
    return '$spent / $limit';
  }

  @override
  String havasOk(String amount) {
    return 'Yana $amount qoldi';
  }

  @override
  String havasNear(String percent) {
    return 'Chegaraga yaqinlashdingiz ($percent%).';
  }

  @override
  String havasOver(String amount) {
    return 'Chegaradan $amount oshdi. Taqiq yoʻq — keyingi oyni birga rejalashtiring.';
  }

  @override
  String get havasPropose => 'Chegara taklif qilish';

  @override
  String get havasProposeTitle => 'Havas uchun oylik chegara';

  @override
  String havasPending(String amount) {
    return 'Taklif: $amount — barcha kattalar roziligi kutilmoqda';
  }

  @override
  String get havasConsent => 'Rozi boʻlish';

  @override
  String get havasConsented => 'Rozi';

  @override
  String get havasAgreed => 'Chegara kelishildi — endi faol.';

  @override
  String havasConsentSaved(String name) {
    return '$name rozi boʻldi';
  }

  @override
  String get havasWithdraw => 'Taklifni bekor qilish';

  @override
  String memberPinPrompt(String name) {
    return '$name, shaxsiy PINʼingiz';
  }

  @override
  String get analysisTitle => 'Isrof va saxovat (shu oy)';

  @override
  String get analysisOstentation => 'Obroʻ xarajatlari';

  @override
  String get analysisDebtHavas => 'Qarz bilan qilingan havas';

  @override
  String get analysisSadaqa => 'Sadaqa — isrof emas';

  @override
  String get analysisGifts => 'Sovgʻalar — hisobga kirmadi';

  @override
  String get treatsTitle => 'Juma shirinligi';

  @override
  String get treatsHint =>
      'Har kungi mayda havasni haftalik oilaviy quvonchga aylantiring.';

  @override
  String get treatAdd => 'Ritual qoʻshish';

  @override
  String get treatTitleDefault => 'Juma shirinligi';

  @override
  String treatLine(String weekday, String amount) {
    return '$weekday · $amount';
  }

  @override
  String get treatChannel => 'Shirinlik kuni';

  @override
  String treatNotifTitle(String title) {
    return 'Bugun — $title';
  }

  @override
  String get treatNotifBody =>
      'Rejadagi quvonch kuni. Oila bilan baham koʻring!';

  @override
  String get titleLabel => 'Nomi';

  @override
  String get habitsTitle => 'Odatlar';

  @override
  String get habitsHint =>
      'Faqat statistika: qancha ketayotganini koʻrasiz, xolos.';

  @override
  String get habitAdd => 'Odat qoʻshish';

  @override
  String habitLine(String month, String year) {
    return 'oyiga $month · yiliga $year';
  }

  @override
  String get habitArchive => 'Kuzatishni toʻxtatish';

  @override
  String get widgetTitle => 'Tez yozish';

  @override
  String get widgetLocked => 'Summalar ilova ochiq paytda koʻrinadi';

  @override
  String get widgetEmpty => 'Ilovada shablon qoʻshing';

  @override
  String widgetRecorded(int count) {
    return 'Vidjetdan $count ta xarajat yozildi';
  }

  @override
  String get vaultReasonRescue => 'Qutqarilgan pul';

  @override
  String get subscriptionsTitle => 'Obunalar va avtotoʻlovlar';

  @override
  String get subscriptionsHint =>
      'Har biri yiliga qancha turishini koʻring va soʻrang: kerakmi?';

  @override
  String get subscriptionsEmpty =>
      'Hali obuna yoʻq. Telefon tarifi, kino, musiqa, ilova obunalarini qoʻshing.';

  @override
  String get subscriptionAdd => 'Obuna qoʻshish';

  @override
  String get cycleMonthly => 'Har oy';

  @override
  String get cycleYearly => 'Har yil';

  @override
  String subscriptionLine(String price, String yearly) {
    return '$price · yiliga $yearly';
  }

  @override
  String subscriptionLastUsed(String date) {
    return 'Oxirgi marta ishlatilgan: $date';
  }

  @override
  String subscriptionForgotten(int days) {
    return '$days kundan beri «ishlatdim» belgilanmagan — kerakmi?';
  }

  @override
  String get subscriptionUsed => 'Ishlatdim';

  @override
  String get subscriptionCancel => 'Bekor qildim';

  @override
  String subscriptionCancelConfirm(String title, String yearly) {
    return '«$title» bekor qilindimi? Yiliga $yearly qutqariladi.';
  }

  @override
  String subscriptionCancelledLine(String yearly) {
    return 'Bekor qilingan · yiliga $yearly tejaladi';
  }

  @override
  String get subscriptionsCancelledHeader => 'Bekor qilinganlar';

  @override
  String subscriptionsAnnualTotal(String amount) {
    return 'Faol obunalar yiliga: $amount';
  }

  @override
  String get subscriptionUsedSaved => 'Belgilandi';

  @override
  String get envelopesTitle => 'Konvertlar';

  @override
  String get envelopesHint =>
      'Haftalik konvert: naqd pulni konvertga soling. Karta bilan toʻlangan xarajat ham shu konvertdan ayiriladi.';

  @override
  String get envelopesEmpty =>
      'Konvert yoʻq. «Bozor», «Yoʻlkira», «Havas» kabi haftalik konvert oching.';

  @override
  String get envelopeAdd => 'Konvert ochish';

  @override
  String get envelopeCashMode => 'Naqd konvert';

  @override
  String get envelopeCategories => 'Qaysi xarajatlar shu konvertdan?';

  @override
  String get envelopeLimitTitle => 'Haftalik limit';

  @override
  String envelopeLine(String spent, String limit, String left) {
    return '$spent / $limit · qoldi $left';
  }

  @override
  String envelopePutCash(String amount) {
    return 'Bu hafta konvertga $amount soling';
  }

  @override
  String envelopeOver(String amount) {
    return 'Konvertdan $amount oshdi';
  }

  @override
  String envelopeCloseTitle(String title, String week) {
    return '«$title»: oʻtgan hafta ($week) yakuni';
  }

  @override
  String get envelopeClosePrompt => 'Konvertda qancha naqd qoldi?';

  @override
  String get envelopeCloseAction => 'Qoldiqni kiritish';

  @override
  String envelopeClosed(String amount) {
    return 'Qoldiq $amount — «Qutqarilgan pul»ga qoʻshildi';
  }

  @override
  String get rescueTitle => 'Qutqarilgan pul';

  @override
  String get rescueThisWeek => 'Bu hafta qutqarildi';

  @override
  String get rescueThisMonth => 'Shu oy qutqarildi';

  @override
  String get rescueQuestion => 'Bu hafta qancha qutqardingiz?';

  @override
  String get rescueHavas => 'Havas kamaydi (bazaviy oyga nisbatan)';

  @override
  String get rescueSubscriptions => 'Bekor qilingan obunalar';

  @override
  String get rescueEnvelopes => 'Konvert qoldiqlari';

  @override
  String get rescueTransferredLine => 'Kelajagimga oʻtkazilgan';

  @override
  String get rescueNoBaseline =>
      'Havasni taqqoslash uchun bazaviy oy yoʻq — birinchi oylik auditdan keyin hisoblanadi.';

  @override
  String rescueBaseline(String month) {
    return 'Bazaviy oy: $month';
  }

  @override
  String get rescueBaselinePick => 'Bazaviy oyni tanlash';

  @override
  String get rescueSpentMore =>
      'Bu davrda havasga bazaviy oydan koʻproq ketdi. Hechqisi yoʻq — har hafta yangi imkoniyat.';

  @override
  String rescueTransfer(String amount) {
    return 'Kelajagimga oʻtkazish — $amount';
  }

  @override
  String rescueTransferDone(String amount) {
    return '$amount Kelajagimga oʻtkazildi';
  }

  @override
  String get rescueFormula =>
      'Qutqarilgan = havas kamayishi + bekor qilingan obunalar + konvert qoldiqlari. Koʻproq sarflangan boʻlsa — 0.';

  @override
  String get notNow => 'Hali yoʻq';

  @override
  String get reserveTitle => 'Favqulodda zaxira';

  @override
  String get reserveHint =>
      'Qora kunda qarz eshigiga yugurmaslik uchun. Hech qayerga sarflanmaydi va «oʻsmadi» deb baholanmaydi.';

  @override
  String reserveMonths(String months) {
    return '$months / 6 oy';
  }

  @override
  String reserveTarget(String target, String monthly) {
    return 'Maqsad: $target (oylik zarur + kerak $monthly × 6)';
  }

  @override
  String get reserveFromEstimate => 'Siz kiritgan taxminiy summa boʻyicha';

  @override
  String get reserveMilestone3 => 'Birinchi bosqich — 3 oy bajarildi';

  @override
  String get reserveFull => 'Toʻliq zaxira — 6 oy. Barakalla!';

  @override
  String get reserveNeedsEstimate =>
      'Maqsadni hisoblash uchun 3 oylik maʼlumot yetarli emas. Bir oyda zarur va kerak xarajatlarga taxminan qancha ketadi?';

  @override
  String get reserveEstimateAction => 'Taxminiy summani kiritish';

  @override
  String get reserveEstimateTitle => 'Oylik zarur + kerak (taxminan)';

  @override
  String get growthTitle => 'Oʻsadigan pul';

  @override
  String get growthHint =>
      'Inflyatsiyadan oldinda yurish uchun — faqat halol (ribosiz) yoʻnalishlarda.';

  @override
  String get growthDeposit => 'Kapital kiritish';

  @override
  String get growthDepositTitle => 'Oʻsadigan pulga';

  @override
  String get gateTitle => 'Avval tayyorgarlik, keyin sarmoya';

  @override
  String get gateHint =>
      'Oʻsadigan pul va sheriklik ikki shart bajarilganda ochiladi. Taqiq yoʻq — tushuntirish bor.';

  @override
  String gateReserve(String months) {
    return 'Favqulodda zaxira — 6 oylik ($months / 6)';
  }

  @override
  String get gateDebt => 'Foizli qarz yoʻq yoki qarzdan chiqish rejasi bor';

  @override
  String get gateOpen => 'Darvoza ochiq';

  @override
  String get gateBypass => 'Baribir kiritish';

  @override
  String get gateBypassTitle => 'Ongli qaror';

  @override
  String get gateBypassWarning =>
      'Zaxirangiz hali toʻliq emas. Qora kun kelsa, oʻsadigan puldagi mablagʻ tez qaytmasligi mumkin va qarzga yugurishga toʻgʻri keladi. Baribir davom etasizmi?';

  @override
  String get gateBypassConfirm => 'Ha, tushunaman';

  @override
  String get gateBypassed => 'Darvoza ongli ravishda chetlab oʻtilgan';

  @override
  String get withdrawFrom => 'Qayerdan?';

  @override
  String get withdrawEmergency => 'Bu haqiqatan favqulodda holat';

  @override
  String get withdrawEmergencyHint => 'Favqulodda zaxira faqat qora kun uchun.';

  @override
  String get refillTitle => 'Qayta toʻldirish rejasi';

  @override
  String refillPlan(String monthly, int months) {
    return 'Har oy $monthly — $months oyda favqulodda zaxira tiklanadi.';
  }

  @override
  String get ok => 'Tushunarli';

  @override
  String get pricesTitle => 'Narx daftari';

  @override
  String get pricesHint =>
      'Narxni yillar davomida yozib borgan odam narx-navo qanchalik oʻzgarganini aniq koʻradi. Oʻzingiz uchun muhim mahsulotlar narxini vaqti-vaqti bilan yozing — shaxsiy inflyatsiyangizni koʻrasiz.';

  @override
  String get pricesEmpty =>
      'Savat boʻsh. Goʻsht, non, un, benzin kabi mahsulot qoʻshing.';

  @override
  String get priceItemAdd => 'Mahsulot qoʻshish';

  @override
  String get priceUnitLabel => 'Birlik (kg, dona, litr)';

  @override
  String get priceQuantityLabel => 'Oyiga qancha (masalan, 4 yoki 1,5)';

  @override
  String get priceAdd => 'Narx yozish';

  @override
  String priceAddTitle(String name, String unit) {
    return '$name — bugungi narx (1 $unit)';
  }

  @override
  String get priceSaved => 'Narx yozildi';

  @override
  String priceLast(String price, String date) {
    return '$price · $date';
  }

  @override
  String priceChange(String fromDate, String from, String to, String change) {
    return '$fromDate: $from → bugun $to ($change)';
  }

  @override
  String inflationYear(String change) {
    return 'Shaxsiy inflyatsiya (1 yil): $change';
  }

  @override
  String inflationSince(String date, String change) {
    return '$date dan beri: $change';
  }

  @override
  String get inflationUnknown =>
      'Indeks uchun bir xil mahsulotning ikki xil vaqtdagi narxi kerak.';

  @override
  String priceStreak(int weeks) {
    return '$weeks hafta ketma-ket narx yozildi';
  }

  @override
  String get priceReminderTitle => 'Narx daftari';

  @override
  String get priceReminderBody =>
      'Bu hafta bozordagi narxlarni yozing — shaxsiy inflyatsiyangizni bilib borasiz.';

  @override
  String get mouseTitle => 'Inflyatsiya taʼsiri';

  @override
  String get mouseHint =>
      'Yotgan pulning qadrini narx-navo sezdirmasdan kamaytiradi. Bu qoʻrqitish emas, tushuntirish.';

  @override
  String get mouseNoPrices =>
      'Hisoblash uchun «Narx daftari»ga kamida bitta mahsulot narxini yozing.';

  @override
  String mouseBalance(String amount) {
    return 'Favqulodda zaxirangiz: $amount';
  }

  @override
  String mouseToday(String qty, String unit, String name) {
    return 'Bugungi narxda: $qty $unit $name';
  }

  @override
  String mouseYearAgo(String qty, String unit) {
    return 'Bir yil oldingi narxda edi: $qty $unit';
  }

  @override
  String mouseFuture(String rate, int years, String qty, String unit) {
    return 'Narx yiliga $rate oshsa, $years yildan keyin: $qty $unit';
  }

  @override
  String get mouseNextReserve =>
      'Keyingi qadam: favqulodda zaxirani 6 oylik miqdorga yetkazing — u yotgan boʻlsa ham, qora kunda sizni qarzdan asraydi.';

  @override
  String get mouseNextGrowth =>
      'Keyingi qadam: zaxira toʻliq. Ortiqcha pulni oʻsadigan qismga — halol savdo va sheriklikka yoʻnaltiring.';

  @override
  String get mouseOpenVault => 'Kelajagimga oʻtish';

  @override
  String get incomeSourceTypeLabel => 'Foyda qayerdan? (ixtiyoriy)';

  @override
  String get incomeTypeTer => 'Ter — mehnat';

  @override
  String get incomeTypeMol => 'Mol — savdo';

  @override
  String get incomeTypeTavakkal => 'Tavakkal — sheriklik';

  @override
  String get incomeTypeRibo => 'Foiz (ribo)';

  @override
  String get incomeRiboNote =>
      'Uchalasidan biri (ter, mol, tavakkal) boʻlmasa — bu ribo. Bunday daromad alohida koʻrsatiladi.';

  @override
  String auditRiboIncome(String amount) {
    return 'Foizli daromad (alohida): $amount';
  }

  @override
  String get debtsTitle => 'Qarzlar';

  @override
  String get debtsHint =>
      'Qarz — teshik emas, yara. Hech bir qarz tashlab ketilmaydi: bank, doʻkon, qarindosh, doʻst.';

  @override
  String debtsTotal(String amount) {
    return 'Jami qarz: $amount';
  }

  @override
  String debtsLoad(String payments, String percent) {
    return 'Oylik qarz yuki: $payments — daromadning $percent%i';
  }

  @override
  String debtsLoadUnknown(String payments) {
    return 'Oylik qarz yuki: $payments (daromad hali yozilmagan)';
  }

  @override
  String get debtsEmpty => 'Qarz yoʻq. Alhamdulillah!';

  @override
  String get debtsBorrowed => 'Olgan qarzlarim';

  @override
  String get debtsLent => 'Bergan qarzlarim';

  @override
  String debtsLentTotal(String amount) {
    return 'Menga qaytishi kerak: $amount';
  }

  @override
  String get debtsGoals => 'Maqsadlarimiz';

  @override
  String get debtAdd => 'Qarz qoʻshish';

  @override
  String get debtLend => 'Qarz berdim';

  @override
  String get goalAdd => 'Maqsad qoʻshish';

  @override
  String get goalTargetTitle => 'Maqsad summasi';

  @override
  String get creditorBank => 'Bank';

  @override
  String get creditorShop => 'Doʻkon (nasiya)';

  @override
  String get creditorRelative => 'Qarindosh';

  @override
  String get creditorFriend => 'Doʻst';

  @override
  String get creditorOther => 'Boshqa';

  @override
  String get debtInterestFlag => 'Foizli (ribo)';

  @override
  String debtNext(String amount, String date) {
    return 'Navbatdagi: $amount · $date';
  }

  @override
  String debtRemaining(String amount) {
    return 'Qoldi: $amount';
  }

  @override
  String get checkTitle => 'Toʻxta va oʻyla';

  @override
  String get checkHint => 'Bu taqiq emas — ongli qaror uchun uchta savol.';

  @override
  String get checkNecessity => 'Bu zaruratmi yoki hashamatmi?';

  @override
  String get checkNeed => 'Zarurat';

  @override
  String get checkLuxury => 'Hashamat';

  @override
  String get checkAlternative => 'Foizsiz muqobil bormi?';

  @override
  String get altReserve => 'Favqulodda zaxira';

  @override
  String get altRelative => 'Qarindoshdan foizsiz';

  @override
  String get altSell => 'Buyum sotish';

  @override
  String get altNone => 'Yoʻq';

  @override
  String checkLoad(String percent) {
    return 'Shu qarz bilan oylik qarz yuki daromadning $percent%iga yetadi';
  }

  @override
  String get debtCreditorLabel => 'Kimdan?';

  @override
  String get debtCreditorName => 'Ismi yoki nomi';

  @override
  String get debtAmountLabel => 'Asosiy summa';

  @override
  String get debtReasonLabel => 'Sababi (toʻy, mashina, roʻzgʻor…)';

  @override
  String get debtScheduleLabel => 'Toʻlov rejasi';

  @override
  String get scheduleManual => 'Oʻzim yozaman';

  @override
  String get scheduleAnnuity => 'Teng toʻlov (bank)';

  @override
  String get scheduleDifferentiated => 'Kamayib boruvchi (bank)';

  @override
  String get scheduleFixedMarkup => 'Qatʼiy ustama';

  @override
  String get debtTermLabel => 'Muddat (oy)';

  @override
  String get debtRateLabel => 'Yillik stavka, %';

  @override
  String get debtMarkupLabel => 'Ustama summasi';

  @override
  String get debtEarlyTerms =>
      'Muddatidan oldin toʻlash shartlari (jarima, komissiya)';

  @override
  String get debtRibaWarning =>
      'Bu qarzda foiz yoki ustama bor — bu ribo. Foizsiz muqobil topishga harakat qiling. Kalkulyator faqat taxminiy natija beradi.';

  @override
  String get manualRowAdd => 'Qator qoʻshish';

  @override
  String get manualRowAmount => 'Toʻlov summasi';

  @override
  String planMustCover(String planned, String principal) {
    return 'Reja jami asosiy summaga teng boʻlishi kerak: $planned / $principal';
  }

  @override
  String get scheduleRequired =>
      'Toʻlash niyati — rejasiz qarzni saqlab boʻlmaydi.';

  @override
  String get costTitle => 'Qarzning haqiqiy narxi';

  @override
  String get costPrincipal => 'Asosiy summa';

  @override
  String get costTotal => 'Jami toʻlanadi';

  @override
  String get costOver => 'Ortiqcha toʻlov';

  @override
  String costOpportunity(String goal, String percent) {
    return 'Bu ortiqcha toʻlov «$goal»ning $percent%i';
  }

  @override
  String get debtSaveAction => 'Qarzni saqlash';

  @override
  String get debtPay => 'Toʻlov qildim';

  @override
  String get debtPayTitle => 'Toʻlov summasi';

  @override
  String get debtPrepayment => 'Qoʻshimcha (muddatidan oldin) toʻlov';

  @override
  String get debtPaymentsHeader => 'Toʻlovlar tarixi';

  @override
  String get debtPlanPaid => 'toʻlangan';

  @override
  String get debtReceipt => 'Qarz tilxati';

  @override
  String get receiptHint =>
      'Ikkinchi tomon va guvohlar shu telefonda ismini yozib, imzo chizadi. Bu shaxsiy hisob uchun yozuv, yuridik kafolat emas.';

  @override
  String get roleLender => 'Qarz beruvchi';

  @override
  String get roleBorrower => 'Qarz oluvchi';

  @override
  String get roleWitness => 'Guvoh';

  @override
  String get witnessAdd => 'Guvoh qoʻshish';

  @override
  String get signAction => 'Imzolash';

  @override
  String get signed => 'Imzolangan';

  @override
  String signTitle(String role) {
    return '$role: ismingiz va imzongiz';
  }

  @override
  String get signHere => 'Shu yerga barmoq bilan imzo chizing';

  @override
  String get signClear => 'Tozalash';

  @override
  String get receiptShare => 'PDF yaratish va ulashish';

  @override
  String get receiptPdfTitle => 'Qarz tilxati';

  @override
  String get receiptPdfParties => 'Tomonlar va shartlar';

  @override
  String get receiptPdfAmount => 'Summa';

  @override
  String get receiptPdfDate => 'Sana';

  @override
  String get receiptPdfReason => 'Sabab';

  @override
  String get receiptPdfMarkup => 'Foiz / ustama';

  @override
  String get receiptPdfNoMarkup => 'Yoʻq — qarzi hasana';

  @override
  String get receiptPdfPayment => 'Toʻlov';

  @override
  String get receiptPdfSignatures => 'Imzolar';

  @override
  String get receiptPdfNote =>
      'Bu hujjat shaxsiy hisob uchun yozuv, yuridik kafolat emas.';

  @override
  String get lendTitle => 'Qarz berdim (qarzi hasana)';

  @override
  String get lendHint => 'Bergan qarzda foiz boʻlmaydi.';

  @override
  String get lendDebtor => 'Kimga?';

  @override
  String lendDue(String date) {
    return 'Qaytarish muddati: $date';
  }

  @override
  String get lendReceive => 'Qaytardi';

  @override
  String get dueTitle => 'Muddati yaqin';

  @override
  String dueReceivable(String name, String amount, String date) {
    return '$name — $amount, muddat $date. Xushmuomalalik bilan eslatib qoʻysangiz boʻladi.';
  }

  @override
  String dueDebt(String name, String amount, String date) {
    return '${name}ga toʻlov: $amount · $date';
  }

  @override
  String get recoveryTitle => 'Qarzdan chiqish rejimi';

  @override
  String get recoveryOfferBody =>
      'Daromadni 70 / 20 / 10 ga boʻling: roʻzgʻor, qarzni tezroq uzish va baribir «Kelajagim». Qarzdan reja bilan chiqiladi.';

  @override
  String get recoveryEnable => 'Rejimni yoqish';

  @override
  String recoveryActive(String needs, String debt, String savings) {
    return 'Yoqilgan: roʻzgʻor $needs % · qarz $debt % · «Kelajagim» $savings %';
  }

  @override
  String get recoverySettings => 'Sozlash';

  @override
  String get recoveryExplain =>
      'Qarz — oʻtmishga toʻlov, jamgʻarma — kelajakka toʻlov. Jamgʻarmasiz qarzdan chiqqan odam birinchi tashvishda yana qarz oladi.';

  @override
  String get recoveryNeeds =>
      'Roʻzgʻor, % (majburiy qarz toʻlovlari shu ichida)';

  @override
  String get recoveryDebt => 'Qarzni tezroq uzish, %';

  @override
  String get recoverySavings => '«Kelajagim», %';

  @override
  String get recoverySavingsZero =>
      'Jamgʻarma ulushi 0 boʻlmaydi — kamida 1 %.';

  @override
  String recoveryTotalError(int total) {
    return 'Jami 100 % boʻlishi kerak (hozir $total %).';
  }

  @override
  String recoveryBudgetTitle(String income) {
    return 'Oylik taqsimot (oʻrtacha daromad $income)';
  }

  @override
  String recoveryBudgetNeeds(String amount) {
    return 'Roʻzgʻor: $amount';
  }

  @override
  String recoveryBudgetMandatory(String amount) {
    return 'shundan majburiy qarz toʻlovlari: $amount';
  }

  @override
  String recoveryBudgetHousehold(String amount) {
    return 'roʻzgʻorga qoladi: $amount';
  }

  @override
  String recoveryBudgetDebt(String amount) {
    return 'Qoʻshimcha qarz toʻlovi: $amount';
  }

  @override
  String recoveryBudgetSavings(String amount) {
    return '«Kelajagim»: $amount';
  }

  @override
  String get recoveryMandatoryOver =>
      'Majburiy toʻlovlar roʻzgʻor ulushidan oshib ketdi — ulushlarni qayta koʻrib chiqing.';

  @override
  String get recoveryNoIncome =>
      'Daromad hali yozilmagan — summalar daromad kiritilgach chiqadi.';

  @override
  String get recoverySaveEnable => 'Saqlash va yoqish';

  @override
  String get recoveryDisable => 'Rejimdan chiqish';

  @override
  String get recoveryStandard => 'Standart 70 / 20 / 10';

  @override
  String get freedShareTitle => 'Alhamdulillah, qarzsiz!';

  @override
  String freedShareBody(String percent) {
    return 'Hamma qarz yopildi — rejim odatiyga qaytdi. Boʻshagan $percent % ni favqulodda zaxira va oʻsadigan pulga yoʻnaltiramizmi?';
  }

  @override
  String get freedShareAccept => 'Ha, «Kelajagim»ga';

  @override
  String get payoffTitle => 'Qarzdan chiqish rejasi';

  @override
  String get payoffEstimate =>
      'Taxminiy hisob: bank grafigi, jarima va komissiya shartnomaga bogʻliq.';

  @override
  String payoffMonthly(String amount) {
    return 'Har oy qoʻshimcha: $amount';
  }

  @override
  String payoffLump(String amount) {
    return 'Bir martalik: $amount';
  }

  @override
  String get payoffMonthlyTitle => 'Har oy qoʻshimcha toʻlov';

  @override
  String get payoffLumpTitle => 'Bir martalik qoʻshimcha toʻlov';

  @override
  String get payoffSources => 'Qoʻshimcha toʻlov manbalari';

  @override
  String payoffSourceShare(String percent, String amount) {
    return 'Ulush ($percent %): oyiga $amount';
  }

  @override
  String get payoffSourceShareOff =>
      'Ulush: «Qarzdan chiqish» rejimi yoqilganda daromadning 20 %i';

  @override
  String payoffSourceRescue(String amount) {
    return 'Qutqarilgan pul (bu hafta): $amount';
  }

  @override
  String payoffSourceSold(String amount) {
    return 'Sotilgan buyumlar: $amount';
  }

  @override
  String get payoffApply => 'Qarzga';

  @override
  String payoffApplied(String amount, String name) {
    return '$amount «$name» qarziga qoʻshimcha toʻlov qilindi.';
  }

  @override
  String get payoffOrder => 'Yopish tartibi';

  @override
  String get payoffOrderHint =>
      'Avval foizli (eng qimmati), keyin foizsiz — muddati yaqini. Tartibni oʻzgartirish mumkin.';

  @override
  String get payoffOrderReset => 'Standart tartib';

  @override
  String get payoffUp => 'Yuqoriga';

  @override
  String get payoffDown => 'Pastga';

  @override
  String payoffDebtFree(String base, String plan) {
    return 'Qarzsiz kun: $base → $plan';
  }

  @override
  String payoffEarly(int months) {
    return '$months oy erta';
  }

  @override
  String payoffSaved(String amount) {
    return '$amount tejaladi';
  }

  @override
  String get payoffSameEnd => 'Muddat oʻzgarmaydi';

  @override
  String payoffFees(String amount) {
    return 'Jarima / komissiya: $amount';
  }

  @override
  String get payoffBaseline => 'Odatiy';

  @override
  String get payoffAccelerated => 'Qoʻshimcha bilan';

  @override
  String get payoffShowTable => 'Grafiklarni koʻrish';

  @override
  String payoffMonths(int months) {
    return '$months oy';
  }

  @override
  String get payoffFeeLabel => 'Muddatidan oldin toʻlash jarimasi, %';

  @override
  String payoffFeeValue(String percent) {
    return 'Jarima: $percent %';
  }

  @override
  String get payoffNoFee => 'Jarima yoʻq';

  @override
  String debtFreeOn(String date) {
    return 'Qarzsiz kun: $date';
  }

  @override
  String get contributorsTitle => 'Yelkadoshlar';

  @override
  String get contributorsHint =>
      'Qarzni oila bilan birga toʻlash: kim qancha toʻlayotganini yozib boring.';

  @override
  String get contributorAdd => 'Yelkadosh qoʻshish';

  @override
  String get contributorShareTitle => 'Oylik ulushi (ixtiyoriy)';

  @override
  String contributorLine(String share, String paid) {
    return 'Oyiga $share · toʻlagan $paid';
  }

  @override
  String contributorPaid(String paid) {
    return 'Toʻlagan: $paid';
  }

  @override
  String get whoPaid => 'Kim toʻladi?';

  @override
  String get whoPaidFamily => 'Oilaning oʻzi';

  @override
  String debtFeeNote(String amount) {
    return 'jarima $amount';
  }

  @override
  String get debtClosedTitle => 'Alhamdulillah! Qarz yopildi';

  @override
  String debtClosedBody(String name) {
    return '«$name» qarzi toʻliq uzildi. Bitta majburiyatdan ozod boʻldingiz.';
  }

  @override
  String debtClosedFreed(String amount) {
    return 'Endi har oy $amount boʻshaydi. Uni «Kelajagim»ga yoʻnaltiramizmi?';
  }

  @override
  String get debtClosedRedirected => '«Kelajagim» ulushi oshirildi.';

  @override
  String get debtClosedNoIncome =>
      'Daromad yozilmagani uchun ulush avtomatik oshirilmaydi — «Kelajagim» sozlamasida oʻzingiz oshiring.';

  @override
  String get debtClosedDone => 'Rahmat';

  @override
  String get modeReturned =>
      'Barcha qarzlar yopildi — «Qarzdan chiqish» rejimi odatiyga qaytdi.';

  @override
  String get sellablesTitle => 'Sotiladigan buyumlar';

  @override
  String get sellablesHint =>
      'Uyda 6 oydan beri ishlatilmayotgan qimmatbaho buyumlar. Sotilgan puli bir bosishda qarzga yoʻnaltiriladi.';

  @override
  String get sellableAdd => 'Buyum qoʻshish';

  @override
  String get sellableName => 'Buyum nomi';

  @override
  String get sellableEstimate => 'Taxminiy narxi';

  @override
  String sellableListed(String amount) {
    return 'Sotuvda · taxminan $amount';
  }

  @override
  String sellableSold(String amount) {
    return 'Sotildi: $amount';
  }

  @override
  String sellableAppliedTo(String amount, String name) {
    return 'Sotildi: $amount · «$name» qarziga';
  }

  @override
  String get sellableMarkSold => 'Sotildi';

  @override
  String get sellableSoldPrice => 'Sotilgan narxi';

  @override
  String get sellableChooseDebt => 'Qaysi qarzga?';

  @override
  String get sellablesEmpty => 'Hali buyum yoʻq.';

  @override
  String homeDebtFree(String date) {
    return 'Qarzsiz kun: $date';
  }

  @override
  String homeDebtFreeBody(String amount, int months) {
    return 'Qolgan qarz: $amount · $months oy';
  }

  @override
  String homeDebtFreePlan(String date) {
    return 'Reja boʻyicha: $date';
  }

  @override
  String get homeRecoveryOffer =>
      '«Qarzdan chiqish» rejimini yoqing — 70 / 20 / 10';

  @override
  String get ceremoniesTitle => 'Marosimlar';

  @override
  String get ceremoniesHint =>
      'Toʻy va marosimni oldindan, qarzsiz rejalash: stsenariylarni taqqoslang, oila bilan maslahatlashing.';

  @override
  String get ceremoniesEmpty => 'Hali reja yoʻq.';

  @override
  String get ceremonyAdd => 'Reja tuzish';

  @override
  String get ceremonyNameLabel => 'Nomi (masalan, oʻgʻlimning toʻyi)';

  @override
  String get ceremonyTypeTitle => 'Marosim turi';

  @override
  String get ceremonyTypeToy => 'Toʻy';

  @override
  String get ceremonyTypeBeshik => 'Beshik toʻy';

  @override
  String get ceremonyTypeSunnat => 'Sunnat toʻy';

  @override
  String get ceremonyTypeMaraka => 'Maʼraka';

  @override
  String get ceremonyTypeOther => 'Boshqa';

  @override
  String get ceremonyStatusDraft => 'Qoralama';

  @override
  String get ceremonyStatusDiscussed => 'Oilada muhokama qilindi';

  @override
  String get ceremonyStatusConfirmed => 'Tasdiqlandi';

  @override
  String get ceremonyFirstScenario => 'Asosiy';

  @override
  String ceremonyDate(String date) {
    return 'Sana: $date';
  }

  @override
  String get ceremonyDateNone => 'Sanasi belgilanmagan';

  @override
  String ceremonyGuests(int count) {
    return '$count kishi';
  }

  @override
  String get ceremonyGuestsTitle => 'Mehmonlar soni';

  @override
  String get scenarioAdd => 'Stsenariy qoʻshish';

  @override
  String get scenarioName =>
      'Stsenariy nomi (masalan, 1 kunlik, 100 kishi, ixcham)';

  @override
  String get scenarioCompare => 'Stsenariylar taqqoslashi';

  @override
  String get scenarioSelect => 'Tanlash';

  @override
  String get scenarioSelected => 'Tanlangan';

  @override
  String get scenarioRemove => 'Oʻchirish';

  @override
  String scenarioTotal(String amount) {
    return 'Jami: $amount';
  }

  @override
  String scenarioDebt(String amount) {
    return 'Qarz: $amount';
  }

  @override
  String get scenarioNoDebt => 'Qarzsiz';

  @override
  String scenarioPayoff(int months, String date) {
    return 'Qarz $months oyda uziladi ($date gacha)';
  }

  @override
  String scenarioPayoffInterest(String amount) {
    return 'ortiqcha toʻlov $amount';
  }

  @override
  String get scenarioPayoffNever =>
      'Bu toʻlov bilan qarz hech qachon tugamaydi';

  @override
  String get scenarioPayoffUnknown =>
      'Toʻlash muddati uchun «qarzni oyiga» summasini kiriting';

  @override
  String scenarioGoal(String goal, String percent) {
    return 'Bu pulga: «$goal» — $percent %';
  }

  @override
  String get lineAdd => 'Qator qoʻshish';

  @override
  String get lineTitle => 'Nomi (osh, xonanda, sarpo…)';

  @override
  String get lineOneTime => 'Bir martalik';

  @override
  String get linePerGuest => 'Kishi boshiga';

  @override
  String linePerGuestValue(String price, int guests, String total) {
    return '$price × $guests = $total';
  }

  @override
  String get lineAmountTitle => 'Summa';

  @override
  String get linePriceTitle => 'Kishi boshiga narx';

  @override
  String get lineSourceTitle => 'Qayerdan moliyalanadi?';

  @override
  String get fundingSavings => 'Jamgʻarma';

  @override
  String get fundingFamily => 'Oila hissasi';

  @override
  String get fundingGifts => 'Kutilayotgan toʻyona';

  @override
  String get fundingDebt => 'Qarz';

  @override
  String ceremonyDebtTerms(String amount) {
    return 'Qarzni oyiga: $amount';
  }

  @override
  String get ceremonyDebtTermsUnset => 'Qarzni oyiga qancha toʻlay olasiz?';

  @override
  String get ceremonyDebtMonthlyTitle => 'Qarzni oyiga toʻlash';

  @override
  String get discussionTitle => 'Buni qarzsiz qanday oʻtkazamiz?';

  @override
  String get discussionHint =>
      'Rejada qarz bor. Tasdiqlashdan oldin oila birga oʻtirib, shu savollarni muhokama qiladi va har bir katta aʼzo belgi qoʻyadi.';

  @override
  String get discussionQ1 => 'Mehmonlar sonini kamaytirsak boʻladimi?';

  @override
  String get discussionQ2 => 'Bir kunlik, ixcham marosim yetarli emasmi?';

  @override
  String get discussionQ3 =>
      'Qaysi xarajatni jamgʻarma yoki oila hissasidan qoplay olamiz?';

  @override
  String get discussionQ4 => 'Qarzni kim, qachon va qanday toʻlaydi?';

  @override
  String get discussionQ5 =>
      'Shu pulga yosh oila uchun nima qilish mumkin edi?';

  @override
  String get discussionMark => 'Muhokama qildim';

  @override
  String get discussionMarked => 'Belgilandi';

  @override
  String get discussionDone => 'Oila muhokama qildi — endi tasdiqlash mumkin.';

  @override
  String discussionMarkedSnack(String name) {
    return '$name belgi qoʻydi.';
  }

  @override
  String get ceremonyConfirm => 'Rejani tasdiqlash';

  @override
  String get ceremonyConfirmedSnack => 'Reja tasdiqlandi.';

  @override
  String get ceremonyConfirmBlocked =>
      'Rejada qarz bor — avval oilaviy muhokama.';

  @override
  String get ceremonyReopen => 'Qayta ochish';

  @override
  String get ceremonyLocked =>
      'Reja tasdiqlangan. Oʻzgartirish uchun qayta oching.';

  @override
  String get giftTitle => 'Toʻyona oʻrniga jamgʻarma';

  @override
  String get giftHint =>
      'Yosh oila uchun maqsad: mehmonlar dabdaba oʻrniga shu jamgʻarmaga hissa qoʻshadi. Hissalar qoʻlda yoziladi.';

  @override
  String get giftCreate => 'Maqsad ochish';

  @override
  String get giftGoalName => 'Maqsad nomi (masalan, yosh oilaga uy)';

  @override
  String get giftTargetTitle => 'Maqsad summasi';

  @override
  String giftProgress(String collected, String target) {
    return 'Yigʻildi: $collected / $target';
  }

  @override
  String get giftAddContribution => 'Hissa yozish';

  @override
  String get giftContributorName => 'Kim qoʻshdi?';

  @override
  String get giftShare => 'Ulashish';

  @override
  String giftShareText(
    String title,
    String goal,
    String target,
    String collected,
  ) {
    return '$title: toʻyona oʻrniga yosh oilaning «$goal» maqsadiga hissa qoʻshing. Maqsad: $target, yigʻildi: $collected.';
  }

  @override
  String get pressure1 =>
      'El uch kun gapiradi, toʻrtinchi kuni oʻz dardi bilan ovora boʻladi.';

  @override
  String get pressure2 =>
      'Yosh oilaga eng katta sovgʻa — qarzsiz boshlangan hayot.';

  @override
  String get pressure3 =>
      'Bir kunlik dabdaba uchun yillab qarz toʻlash — oʻzingiz zimmangizga olgan ogʻir yuk.';

  @override
  String get roleParty => 'Sherik';

  @override
  String get pnTitle => 'Sheriklik';

  @override
  String get pnHint =>
      'Bir odamning puli bekor yotadi, boshqasining hunari pulsizlikdan bekor turadi. Sheriklik — sadaqa ham, qarz ham emas: tavakkal boʻlishiladi.';

  @override
  String get pnEmpty => 'Hali sheriklik yoʻq.';

  @override
  String get pnNew => 'Shartnoma tuzish';

  @override
  String get pnTypeMudaraba => 'Mudoraba';

  @override
  String get pnTypeMusharaka => 'Musharaka';

  @override
  String get pnTypeMudarabaHint =>
      'Kapital bir tomondan, mehnat ikkinchi tomondan. Moliyaviy zarar kapital egasida, mehnat egasi mehnatidan ayriladi.';

  @override
  String get pnTypeMusharakaHint =>
      'Har ikki tomon kapital kiritadi. Zarar kiritilgan kapitalga mutanosib boʻlinadi.';

  @override
  String get pnStatusDraft => 'Imzolanmagan';

  @override
  String get pnStatusSigned => 'Imzolangan';

  @override
  String get pnStatusActive => 'Faol';

  @override
  String get pnStatusClosed => 'Yopilgan';

  @override
  String get pnRoleProvider => 'Kapital egasi';

  @override
  String get pnRoleWorker => 'Mehnat egasi';

  @override
  String get pnRoleBoth => 'Kapital va mehnat';

  @override
  String get pnPeriodMonthly => 'Har oy';

  @override
  String get pnPeriodQuarterly => 'Har chorak';

  @override
  String get pnPeriodYearly => 'Har yil';

  @override
  String get pnCapitalCash => 'Pul';

  @override
  String get pnCapitalEquipment => 'Uskuna';

  @override
  String get pnStepType => 'Tur';

  @override
  String get pnStepParties => 'Tomonlar';

  @override
  String get pnStepCapital => 'Kapital';

  @override
  String get pnStepProfit => 'Foyda va zarar';

  @override
  String get pnStepTerms => 'Shartlar';

  @override
  String get pnStepReview => 'Koʻrib chiqish';

  @override
  String get pnName => 'Nomi (masalan, tikuvchilik sexi)';

  @override
  String get pnMyRole => 'Mening rolim';

  @override
  String get pnMyName => 'Mening ismim';

  @override
  String get pnPartnerName => 'Sherigim ismi';

  @override
  String get pnPartnerRole => 'Sherigim roli';

  @override
  String pnCapitalOf(String name, String amount) {
    return '$name: $amount';
  }

  @override
  String get pnCapitalAdd => 'Kapital qoʻshish';

  @override
  String get pnCapitalTitle => 'Nomi (masalan, tikuv mashinasi)';

  @override
  String get pnCapitalAmount => 'Narxi yoki summasi';

  @override
  String get pnCapitalNone => 'Kapital kiritmaydi (mehnat)';

  @override
  String get pnProfitMethod => 'Foyda qanday boʻlinadi?';

  @override
  String get pnProfitPercent => 'Sof foydaning foizi';

  @override
  String get pnProfitFixed => 'Qatʼiy summa (oyiga …)';

  @override
  String get pnProfitGuaranteed => 'Zarar boʻlsa ham vaʼda qilingan foyda';

  @override
  String get pnNotPartnership =>
      'Bu sheriklik emas — ribo yoki qarz. Sheriklikda foyda faqat sof foydaning foizi boʻladi: foyda boʻlmasa — hech kim olmaydi, zarar boʻlsa — qoidaga koʻra boʻlinadi.';

  @override
  String get pnMyShare => 'Mening ulushim, %';

  @override
  String pnPartnerShare(String percent) {
    return 'Sherigim ulushi: $percent %';
  }

  @override
  String get pnLossRuleMudaraba =>
      'Zarar: moliyaviy zarar kapital egasida; mehnat egasi mehnatidan ayriladi. Istisno — beparvolik yoki shart buzilishi (izoh bilan).';

  @override
  String pnLossRuleMusharaka(String shares) {
    return 'Zarar kapitalga mutanosib: $shares.';
  }

  @override
  String get pnTermMonths => 'Muddat (oy)';

  @override
  String get pnReportPeriod => 'Hisobot davriyligi';

  @override
  String get pnEndTerms => 'Muddat tugaganda nima boʻladi?';

  @override
  String get pnEndTermsDefault =>
      'Hisob-kitob qilinadi: kapital va uskunalar egasiga qaytadi, oxirgi foyda ulushlar boʻyicha boʻlinadi.';

  @override
  String get pnDisputeTerms => 'Nizolar qanday hal qilinadi?';

  @override
  String get pnDisputeTermsDefault =>
      'Avval oʻzaro maslahat, soʻng guvohlar va ishonchli oqsoqol ishtirokida.';

  @override
  String get pnWitnesses => 'Guvohlar';

  @override
  String get pnWitnessAdd => 'Guvoh qoʻshish';

  @override
  String get pnNext => 'Keyingi';

  @override
  String get pnBack => 'Orqaga';

  @override
  String get pnCreate => 'Shartnomani yaratish';

  @override
  String get pnTemplatePending =>
      'Shablon yurist va ulamo tomonidan hali tekshirilmagan — shaxsiy hisob uchun yozuv, yuridik kafolat emas.';

  @override
  String pnContractVersion(int version) {
    return 'Shartnoma, $version-versiya';
  }

  @override
  String get pnResign => 'Shartnoma oʻzgardi — hamma qayta imzolashi kerak.';

  @override
  String get pnAmend => 'Shartnomani oʻzgartirish';

  @override
  String get pnAmendTerm => 'Yangi muddat (oy)';

  @override
  String get pnPdf => 'PDF yaratish va ulashish';

  @override
  String get pnPdfTitle => 'Sheriklik shartnomasi';

  @override
  String get pnPdfParties => 'Tomonlar va kapital';

  @override
  String get pnPdfTerms => 'Shartlar';

  @override
  String get pnPdfShare => 'Foyda ulushi';

  @override
  String get pnPdfCapital => 'Kapital';

  @override
  String get pnPdfRole => 'Rol';

  @override
  String get pnPdfName => 'Ism';

  @override
  String get pnPdfType => 'Turi';

  @override
  String get pnPdfLoss => 'Zarar qoidasi';

  @override
  String get pnPdfNote =>
      'Sheriklik — sadaqa ham, qarz ham emas: foyda faqat sof foydaning foizi, oldindan vaʼda qilingan daromad yoʻq. Shaxsiy hisob uchun yozuv, yuridik kafolat emas.';

  @override
  String get pnPdfVersion => 'Versiya';

  @override
  String get pnLossCalc => 'Zarar boʻlsa kim koʻtaradi?';

  @override
  String pnLossAmount(String amount) {
    return 'Zarar summasi: $amount';
  }

  @override
  String get pnNegligence =>
      'Mehnat egasining beparvoligi yoki shart buzilishi';

  @override
  String get pnNegligenceNote => 'Izoh (nima boʻldi?)';

  @override
  String get pnNegligenceNoteRequired => 'Beparvolik izohsiz qabul qilinmaydi.';

  @override
  String get pnActivate => 'Sheriklikni boshlash';

  @override
  String get pnActivated => 'Sheriklik faol.';

  @override
  String get pnSignFirst => 'Boshlashdan oldin shartnomani hamma imzolaydi.';

  @override
  String get pnGateTitle => 'Kapital kiritish — tayyorgarlik darvozasi';

  @override
  String get pnGateClosed =>
      'Darvoza yopiq: avval 6 oylik favqulodda zaxira va qarz rejasi. Baribir kiritsangiz — bu ongli qaror sifatida yoziladi.';

  @override
  String get pnGateOpen => 'Darvoza ochiq — kapital kiritishga tayyorsiz.';

  @override
  String get pnGateBypass => 'Baribir boshlash';

  @override
  String get pnNotDebtTitle => 'Bu qarz emas';

  @override
  String get pnNotDebtBody =>
      'Mudorabada siz olgan kapital qarz emas: uni qaytarish majburiyati yoʻq, zarar kapital egasida (beparvolik bundan mustasno). Foyda kelishilgan ulushda boʻlinadi. Buni oila bilan maslahatlashing.';

  @override
  String get pnNotDebtAck => 'Tushundim';

  @override
  String get pnConsentTitle => 'Oilaviy rozilik';

  @override
  String get pnConsent => 'Roziman';

  @override
  String get pnConsented => 'Rozi';

  @override
  String get pnBuyoutTitle => 'Ulushni bosqichma-bosqich sotib olish';

  @override
  String get pnBuyoutHint =>
      'Mehnat egasi foyda ulushidan oz-ozdan toʻlab, kapital egasining ulushini sotib oladi va oxirida mustaqil boʻladi.';

  @override
  String pnBuyoutMonthly(String amount) {
    return 'Oyiga: $amount';
  }

  @override
  String get pnBuyoutSet => 'Oylik toʻlovni belgilash';

  @override
  String pnBuyoutRemaining(String amount, String percent) {
    return 'Kapital egasining qolgan ulushi: $amount ($percent %)';
  }

  @override
  String pnBuyoutEnd(String date, int months) {
    return 'Toʻliq sotib olinadi: $date ($months oy)';
  }

  @override
  String get pnBuyoutPay => 'Toʻlov yozish';

  @override
  String get pnBuyoutHistory => 'Buyout toʻlovlari';

  @override
  String get pnBuyoutNone => 'Hali toʻlov yoʻq.';

  @override
  String pnBuyoutPaidRow(String amount, String date) {
    return '$amount — $date';
  }

  @override
  String get pnClose => 'Sheriklikni yopish';

  @override
  String get pnErrorShares => 'Ulushlar yigʻindisi 100 % boʻlishi kerak.';

  @override
  String get agAlreadySigned => 'Bu tomon allaqachon imzolagan.';

  @override
  String get expenseDeleted => 'Xarajat oʻchirildi.';

  @override
  String get pnAlreadySigned => 'Bu tomon allaqachon imzolagan.';

  @override
  String get pnErrorCapital => 'Musharakada har ikki tomon kapital kiritadi.';

  @override
  String get pnErrorRoles =>
      'Mudorabada kapital bir tomondan, mehnat ikkinchi tomondan boʻladi.';

  @override
  String get pnErrorNoCapital =>
      'Kapital egasi kiritadigan pul yoki uskunani qoʻshing.';

  @override
  String get ledgerTitle => 'Kassa daftari';

  @override
  String get ledgerHint =>
      'Biznes puli uy pulidan alohida: uy byudjetiga faqat taqsimlangan ulushingiz tushadi.';

  @override
  String get ledgerReadOnly =>
      'Daftarni mehnat egasi yuritadi; siz uni faqat koʻrasiz va davr hisobotini olasiz.';

  @override
  String ledgerOpenPeriod(String start) {
    return 'Ochiq davr: $start — bugun';
  }

  @override
  String ledgerIncome(String amount) {
    return 'Kirim: $amount';
  }

  @override
  String ledgerExpense(String amount) {
    return 'Xarajat: $amount';
  }

  @override
  String ledgerNet(String amount) {
    return 'Sof foyda: $amount';
  }

  @override
  String ledgerLoss(String amount) {
    return 'Zarar: $amount';
  }

  @override
  String get ledgerAdd => 'Yozuv qoʻshish';

  @override
  String get ledgerKindIncome => 'Kirim (buyurtma)';

  @override
  String get ledgerKindExpense => 'Xarajat';

  @override
  String get ledgerKindForce => 'Fors-major';

  @override
  String get ledgerKindCorrection => 'Tuzatish';

  @override
  String get ledgerEntryTitle => 'Nima uchun? (buyurtma, mato, ish haqi…)';

  @override
  String get ledgerNote => 'Izoh (dalil, tafsilot)';

  @override
  String get ledgerAttach => 'Chek rasmi';

  @override
  String get ledgerAttached => 'Rasm biriktirildi';

  @override
  String get ledgerCorrectionMinus => 'Foydani kamaytiradi';

  @override
  String get ledgerLocked => 'Yopilgan davr — oʻzgarmaydi';

  @override
  String get ledgerClose => 'Davrni yopish va taqsimlash';

  @override
  String get ledgerCloseConfirm =>
      'Davr yopilgach yozuvlar oʻzgarmaydi; tuzatish faqat keyingi davrda yangi yozuv bilan. Yopamizmi?';

  @override
  String get ledgerClosedTitle => 'Yopilgan davrlar';

  @override
  String ledgerPeriod(String start, String end) {
    return '$start — $end';
  }

  @override
  String ledgerShareLine(String name, String amount) {
    return '$name: $amount';
  }

  @override
  String ledgerBuyoutLine(String amount) {
    return 'Buyout: $amount';
  }

  @override
  String get ledgerReport => 'Hisobot PDF';

  @override
  String get ledgerEmpty => 'Hali yozuv yoʻq.';

  @override
  String ledgerClosedSnack(String amount) {
    return 'Davr yopildi. Ulushingiz uy daromadiga yozildi: $amount';
  }

  @override
  String get ledgerClosedPlain => 'Davr yopildi.';

  @override
  String get ledgerReportTitle => 'Sheriklik davr hisoboti';

  @override
  String get ledgerReportDistribution => 'Taqsimot';

  @override
  String get ledgerReportEntries => 'Yozuvlar';

  @override
  String get ledgerReportBuyout => 'Kapital egasining qolgan ulushi';

  @override
  String get ledgerReportNote =>
      'Hisobot sherikka shaffoflik uchun: kirim, xarajat, foyda va taqsimot shu daftar yozuvlaridan.';

  @override
  String get ledgerOpenButton => 'Kassa daftari';

  @override
  String get ideasTitle => 'Hunardan ishga';

  @override
  String get ideasHint =>
      'Oiladagi bekor yotgan hunarlar — tikuvchilik, pazandachilik, taʼmirlash, til bilish… Hisob-kitobni uch marta qiling.';

  @override
  String get skillsTitle => 'Hunarlar';

  @override
  String get skillAdd => 'Hunar qoʻshish';

  @override
  String get skillName => 'Hunar (masalan, tikuvchilik)';

  @override
  String get ideasList => 'Gʻoyalar';

  @override
  String get ideaAdd => 'Gʻoya hisobi';

  @override
  String get ideaName => 'Gʻoya (masalan, uyda tikuv sexi)';

  @override
  String get ideaCapex => 'Boshlangʻich xarajat (CAPEX)';

  @override
  String get ideaCapexAdd => 'Band qoʻshish';

  @override
  String get ideaCapexTitle => 'Nima? (overlok, bichish stoli, mato…)';

  @override
  String ideaCapexTotal(String amount) {
    return 'Jami: $amount';
  }

  @override
  String ideaIncome(String amount) {
    return 'Oylik kirim (oʻrtacha): $amount';
  }

  @override
  String ideaExpense(String amount) {
    return 'Oylik xarajat: $amount';
  }

  @override
  String get ideaIncomeTitle => 'Oʻrtacha oylik kirim';

  @override
  String get ideaExpenseTitle => 'Oylik xarajat';

  @override
  String get ideaShare => 'Sheriklikda mening ulushim, %';

  @override
  String get ideaSave => 'Hisoblash va saqlash';

  @override
  String get scenarioPessimistic => 'Pessimistik';

  @override
  String get scenarioBase => 'Oʻrtacha';

  @override
  String get scenarioOptimistic => 'Optimistik';

  @override
  String ideaScenarioLine(String income, String expense, String net) {
    return 'Kirim $income · xarajat $expense · foyda $net';
  }

  @override
  String ideaMyNet(String amount) {
    return 'Ulushdan keyin: $amount';
  }

  @override
  String ideaPayback(int months) {
    return 'Qoplanadi: $months oyda';
  }

  @override
  String get ideaNoPayback => 'Qoplanmaydi — xarajat yoki narxni qayta koʻring';

  @override
  String get ideaToContract => 'Shartnoma qoralamasi';

  @override
  String get offerTitle => 'Taklifni tekshirish';

  @override
  String get offerHint =>
      'Tavakkalsiz foyda vaʼda qilinsa — u yerda yo ribo, yo firibgarlik bor.';

  @override
  String get offerName => 'Taklif (masalan, «signal guruhi»)';

  @override
  String get offerQGuaranteed =>
      'Foyda oldindan vaʼda qilinganmi (zarar boʻlsa ham)?';

  @override
  String get offerQLoss => 'Zarar boʻlsa, u boʻlishiladimi?';

  @override
  String get offerQReal => 'Orqasida real mol yoki ish bormi?';

  @override
  String get offerQRecruit => 'Yangi odam jalb qilish talab qilinadimi?';

  @override
  String get offerQPressure => '«Hozir qaror qiling» deb shoshiltirishyaptimi?';

  @override
  String get offerQContract => 'Yozma shartnoma bormi?';

  @override
  String get offerYes => 'Ha';

  @override
  String get offerNo => 'Yoʻq';

  @override
  String get offerUnknown => 'Bilmayman';

  @override
  String get offerCheck => 'Baholash';

  @override
  String get offerGreen =>
      'Yashil: jiddiy xavf belgisi topilmadi. Baribir shartnomani oʻqing va maslahatlashing.';

  @override
  String get offerYellow =>
      'Sariq: aniqlashtiring — quyidagi belgilar shubhali.';

  @override
  String get offerRed =>
      'Qizil: bu yo ribo, yo firibgarlik belgisi. Pul bermang.';

  @override
  String get offerFlagGuaranteed =>
      'Tavakkalsiz foyda vaʼdasi — sheriklik emas: yo ribo, yo firibgarlik.';

  @override
  String get offerFlagLoss =>
      'Zarar boʻlishilmasa — bu sheriklik emas, qarz yoki ribo.';

  @override
  String get offerFlagReal =>
      'Real mol yoki ish boʻlmasa, «foyda» yangi kelganlar pulidan toʻlanadi.';

  @override
  String get offerFlagRecruit =>
      'Yangi aʼzo jalb qilish talabi — piramida belgisi.';

  @override
  String get offerFlagPressure =>
      'Shoshiltirish — oʻylashga vaqt bermaslik usuli.';

  @override
  String get offerFlagContract =>
      'Yozma shartnomasiz kelishuvni himoya qilib boʻlmaydi.';

  @override
  String offerFlagUnknown(String question) {
    return 'Javobini bilmaysiz — avval aniqlashtiring: $question';
  }

  @override
  String get offerHistory => 'Avvalgi tekshiruvlar';

  @override
  String get offerVerdictGreen => 'Yashil';

  @override
  String get offerVerdictYellow => 'Sariq';

  @override
  String get offerVerdictRed => 'Qizil';

  @override
  String get homeOfferCheckBody =>
      'Kimdir tavakkalsiz foyda vaʼda qildimi? Bir daqiqada tekshiring.';

  @override
  String get ledgerNetLabel => 'Sof foyda';

  @override
  String get ledgerLossLabel => 'Zarar';

  @override
  String get ledgerBuyoutLabel => 'Buyout toʻlovi';

  @override
  String ledgerNextPeriod(String start) {
    return 'Keyingi davr: $start dan';
  }

  @override
  String get obWelcome => 'Assalomu alaykum! Baraka Dasturga xush kelibsiz';

  @override
  String get obLanguage => 'Til';

  @override
  String get obLanguageHint => 'Keyin sozlamalarda ham oʻzgartirish mumkin.';

  @override
  String get obRestore => 'Zaxira nusxadan tiklash';

  @override
  String get obFamily => 'Oila aʼzolari';

  @override
  String get obFamilyHint =>
      'Har yozuvda «kim?» belgisi boʻladi. Yolgʻiz yuritsangiz — faqat ismingizni yozing.';

  @override
  String get obOwnerName => 'Ismingiz';

  @override
  String get obAddMember => 'Aʼzo qoʻshish';

  @override
  String get obMemberAdult => 'Katta';

  @override
  String get obMemberChild => 'Bola';

  @override
  String get obIncome => 'Daromadingiz qanday keladi?';

  @override
  String get obIncomeHint =>
      'Shunga qarab bosh ekran va eslatmalar moslashadi.';

  @override
  String get obIncomeDaily => 'Kunlik naqd';

  @override
  String get obIncomeDailyHint =>
      'Taksi, bozor, usta — har kuni kechqurun «bugun qancha?» deb eslatamiz.';

  @override
  String get obIncomeOrders => 'Buyurtma boʻyicha';

  @override
  String get obIncomeOrdersHint =>
      'Tikuv, pazandachilik, taʼmirlash — har shanba haftalik eslatma.';

  @override
  String get obIncomeSalary => 'Oylik maosh';

  @override
  String get obIncomeSalaryHint =>
      'Maosh kuni eslatamiz va oylik davr shu kundan boshlanadi.';

  @override
  String get obSalaryDay => 'Maosh kuni';

  @override
  String get obDebt => 'Hozir qarzingiz bormi?';

  @override
  String get obDebtHint =>
      'Bank, doʻkon nasiyasi, qarindosh yoki doʻst — hammasi hisobga olinadi. Bu sir ilovadan chiqmaydi.';

  @override
  String get obDebtYes => 'Ha, bor';

  @override
  String get obDebtNo => 'Yoʻq';

  @override
  String get obDebtRecovery =>
      'Qarzlarni yozgach, «Qarzdan chiqish» rejimini taklif qilamiz: daromadning 70 % i roʻzgʻorga, 20 % i qarzni tezroq uzishga, 10 % i baribir «Kelajagim»ga.';

  @override
  String get obNext => 'Davom etish';

  @override
  String get obFinish => 'Boshlash';

  @override
  String obStep(int step, int total) {
    return '$step / $total';
  }

  @override
  String get reminderIncomeTitle => 'Daromadni yozdingizmi?';

  @override
  String get reminderIncomeDaily =>
      'Bugun qancha topdingiz? Bir daqiqada yozing — ulush ham ajraladi.';

  @override
  String get reminderIncomeWeekly => 'Bu haftadagi buyurtmalar puli yozildimi?';

  @override
  String get reminderIncomeMonthly =>
      'Bugun maosh kuni. Avval oʻzingizga toʻlang — «Kelajagim» ulushini ajrating.';

  @override
  String get settingsIncomeKind => 'Daromad turi';

  @override
  String get backupTitle => 'Zaxira nusxa';

  @override
  String get backupHint =>
      'Butun daftar siz tanlagan parol bilan shifrlangan faylga yoziladi. Telefon almashsa yoki ilova oʻchirilsa — shu fayl va parol bilan tiklaysiz. Parolni unutmang: uni hech kim tiklay olmaydi.';

  @override
  String get backupPassword => 'Parol (kamida 8 belgi)';

  @override
  String get backupPasswordRepeat => 'Parolni takrorlang';

  @override
  String get backupPasswordMismatch => 'Parollar mos emas.';

  @override
  String get backupExport => 'Nusxa yaratish va saqlash';

  @override
  String get backupImport => 'Fayldan tiklash';

  @override
  String get backupImportConfirm =>
      'Hozirgi maʼlumotlar toʻliq nusxadagisi bilan almashtiriladi. Davom etamizmi?';

  @override
  String get backupImportPassword => 'Nusxa paroli';

  @override
  String backupRestored(int count) {
    return 'Tiklandi: $count ta yozuv.';
  }

  @override
  String get backupBadPassword => 'Parol notoʻgʻri yoki fayl buzilgan.';

  @override
  String get backupBadFormat => 'Bu Baraka Dastur zaxira nusxasi emas.';

  @override
  String get backupVersion =>
      'Nusxa ilovaning boshqa versiyasida yaratilgan — ilovani yangilang.';

  @override
  String get backupWorking => 'Shifrlanmoqda…';

  @override
  String get homeAddIncomeDaily => 'Bugungi tushum';

  @override
  String get homeAddIncomeOrders => 'Buyurtma puli';

  @override
  String get homeAddIncomeSalary => 'Maosh';

  @override
  String get reminderIncomeChannel => 'Daromad eslatmalari';

  @override
  String get settingsBackupHint =>
      'Parol bilan shifrlangan fayl: saqlash va tiklash';

  @override
  String get backupRestoring => 'Tiklanmoqda…';

  @override
  String get backupExportTitle => 'Nusxa yaratish';

  @override
  String get backupImportTitle => 'Nusxadan tiklash';

  @override
  String get backupImportHint =>
      'Faylni tanlang va nusxa yaratilgandagi parolni kiriting.';

  @override
  String get obMemberRemove => 'Olib tashlash';

  @override
  String showMore(int count) {
    return 'Yana koʻrsatish ($count)';
  }

  @override
  String get settingsIncomeKindUnset => 'Tanlang';

  @override
  String get roleArbiter => 'Hakam';

  @override
  String get receiptErrName => 'Ismni yozing.';

  @override
  String get receiptErrSignature => 'Imzo chizilmagan.';

  @override
  String get agTitle => 'Kelishuvlar';

  @override
  String get agScreenTitle => 'Kelishuv';

  @override
  String get agIntro =>
      'Ogʻzaki kelishuv — qumga qurilgan uy. Yozish ishonchsizlik emas, ishonchni asrash vositasi.';

  @override
  String get agEmpty =>
      'Hali kelishuv yoʻq. Ijara, xizmat, oilaviy kelishuv yoki hozir ogʻzaki davom etayotganini yozib qoʻying.';

  @override
  String get agNew => 'Yangi kelishuv';

  @override
  String get agTypePartnership => 'Sheriklik';

  @override
  String get agTypeLoan => 'Qarz tilxati';

  @override
  String get agTypeRent => 'Ijara';

  @override
  String get agTypeService => 'Xizmat yoki ish';

  @override
  String get agTypeFamily => 'Oilaviy kelishuv';

  @override
  String get agTypeOther => 'Boshqa';

  @override
  String get agStatusDraft => 'Qoralama';

  @override
  String get agStatusSigned => 'Imzolangan';

  @override
  String get agStatusActive => 'Amalda';

  @override
  String get agStatusDispute => 'Nizoda';

  @override
  String get agStatusClosed => 'Yopilgan';

  @override
  String agVersion(int n) {
    return '$n-versiya';
  }

  @override
  String get agOralBadge => 'ogʻzakidan yozilgan';

  @override
  String agEffectiveFrom(String date) {
    return 'Kuchga kirgan sana: $date';
  }

  @override
  String get agLegacyHint =>
      'Bu hujjat 9 savolli tartibdan oldin imzolangan — imzolar oʻz kuchida. Keyingi versiyada savollarni toʻldiring.';

  @override
  String agProgress(int n) {
    return '$n / 9 savolga javob berildi';
  }

  @override
  String get agReadyHint => '9 savol tayyor — imzolash mumkin.';

  @override
  String get agSignLocked =>
      'Imzolash 9 savolning hammasiga javob berilgach (yoki izoh bilan «tegishli emas» deb belgilangach) ochiladi.';

  @override
  String get agAdvisorTip =>
      'Maslahat: noqulay bandlarni ham oldindan yozing — masalan, kimdir vazifasini bir hafta bajara olmasa nima boʻladi. Aniq yozilgan qoida keyingi tortishuvning oldini oladi.';

  @override
  String get agNeedsAnswer => 'Javob kerak';

  @override
  String get agAutoBadge => 'Hujjatdan avtomatik';

  @override
  String get agAutoHint =>
      'Bu savol asl hujjatdan olinadi — oʻzgartirish uchun shartnoma yoki qarz yozuvini tahrirlang.';

  @override
  String get agErrSigned =>
      'Imzolangan versiya oʻzgarmaydi — yangi versiya yarating.';

  @override
  String get agQ1 => 'Kim bilan kim?';

  @override
  String get agQ2 => 'Kim nima qoʻshyapti?';

  @override
  String get agQ3 => 'Kim nima qiladi?';

  @override
  String get agQ4 => 'Foyda qanday boʻlinadi?';

  @override
  String get agQ5 => 'Zarar koʻrilsa nima boʻladi?';

  @override
  String get agQ6 =>
      'Pul qayerda, hisobni kim yuritadi, ikkinchi tomon qachon koʻradi?';

  @override
  String get agQ7 => 'Qanday ajralib chiqiladi?';

  @override
  String get agQ8 => 'Kelisha olmasangiz, kim hakam?';

  @override
  String get agQ9 => 'Qachon yangilanadi?';

  @override
  String get agQ1Hint =>
      'Toʻliq ism-sharif, roli va aloqasi. Kamida ikki tomon.';

  @override
  String get agQ2Hint =>
      'Pul, mol, mehnat yoki tanish-bilish — har bir tomonda kamida bitta hissa.';

  @override
  String get agQ3Hint =>
      'Har vazifaga yagona masʼul va «bajarilmasa» bandi. Umumiy qoldirilgan ish koʻpincha hech kimning ishi boʻlmay qoladi.';

  @override
  String get agQ4Hint =>
      'Faqat foizda. Soʻmdagi qatʼiy summa sheriklikda taqiqlangan.';

  @override
  String get agQ5Hint =>
      'Mudarabada zarar kapital egasida, musharakada — kapitalga mutanosib.';

  @override
  String get agQ6Hint => 'Standart — oyiga bir marta ochiq hisob koʻrigi.';

  @override
  String get agQ7Hint =>
      'Oldindan ogohlantirish, ulushni baholash, toʻlash muddati va mol-mulkni boʻlish.';

  @override
  String get agQ8Hint =>
      'Ikkala tomon ishonadigan, tomonlardan biri boʻlmagan odam. Hakam ham roziligini imzolaydi.';

  @override
  String get agQ9Hint =>
      'Muddat va yillik yangilash sanasi; 30 kun oldin eslatamiz.';

  @override
  String agQuestionTitle(int n, String title) {
    return '$n. $title';
  }

  @override
  String get agNotApplicable => 'Tegishli emas';

  @override
  String get agNaReason => 'Nega tegishli emas (izoh majburiy)';

  @override
  String agNaSummary(String reason) {
    return 'Tegishli emas: $reason';
  }

  @override
  String get agPartyName => 'Toʻliq ism-sharif';

  @override
  String get agPartyRole => 'Roli';

  @override
  String get agPartyRelation => 'Aloqasi (qarindosh, qoʻshni…)';

  @override
  String get agPartyAdd => 'Tomon qoʻshish';

  @override
  String get agWho => 'Kim';

  @override
  String get agContribKind => 'Hissa turi';

  @override
  String get agContribMoney => 'Pul';

  @override
  String get agContribGoods => 'Mol yoki uskuna';

  @override
  String get agContribLabor => 'Mehnat';

  @override
  String get agContribNetwork => 'Tanish-bilish';

  @override
  String get agAmountSom => 'Summa (soʻm)';

  @override
  String get agDescription => 'Tavsif';

  @override
  String get agContribAdd => 'Hissa qoʻshish';

  @override
  String get agDutyHint => 'Masʼul — bitta tomon. «Hamma» tanlab boʻlmaydi.';

  @override
  String get agDutyTitle => 'Vazifa';

  @override
  String get agDutyOwner => 'Yagona masʼul';

  @override
  String get agDutyBreach =>
      'Bajarilmasa (masalan, 1 kun ichida xabar beradi va oʻrniga yechim topadi)';

  @override
  String get agDutyAdd => 'Vazifa qoʻshish';

  @override
  String get agProfitHint => 'Ulushlar foizda, yigʻindisi 100 %.';

  @override
  String agProfitShare(String name) {
    return '$name ulushi, %';
  }

  @override
  String get agProfitText => 'Yoki soʻz bilan (masalan, ijara haqi oyiga …)';

  @override
  String get agLossText => 'Zarar qanday taqsimlanadi';

  @override
  String get agLossMusharaka => 'Zarar kapitalga mutanosib taqsimlanadi.';

  @override
  String get agLossLoan =>
      'Qarzda foyda va zarar boʻlishilmaydi — faqat asosiy summa qaytariladi (foiz yoʻq).';

  @override
  String get agLoanSchedule => 'Qaytarish jadvali (qarz yozuvidan)';

  @override
  String get agLoanNoInterest => 'Foiz yoʻq';

  @override
  String get agCustodyWhere => 'Pul qayerda turadi';

  @override
  String get agCustodyKeeper => 'Hisobni kim yuritadi';

  @override
  String get agCustodyEvery => 'Ochiq hisob koʻrigi';

  @override
  String get agEveryWeek => 'Har hafta';

  @override
  String get agEvery2Weeks => 'Ikki haftada bir';

  @override
  String get agEveryMonth => 'Oyiga bir marta';

  @override
  String get agEveryQuarter => 'Uch oyda bir';

  @override
  String get agEveryYear => 'Yiliga bir marta';

  @override
  String agEveryDays(int days) {
    return 'Har $days kunda';
  }

  @override
  String get agReviewTooRare =>
      'Koʻrik oyiga bir martadan siyrak — kelishmovchilik yigʻilib qolmasin, tez-tez koʻring.';

  @override
  String get agExitNotice => 'Oldindan ogohlantirish (kun)';

  @override
  String get agExitValuation => 'Ulush qanday baholanadi';

  @override
  String get agExitPayout => 'Qachon va qanday toʻlanadi';

  @override
  String get agExitAssets => 'Mol-mulk qanday boʻlinadi';

  @override
  String get agArbiterHint => 'Hakam tomonlardan biri boʻla olmaydi.';

  @override
  String get agArbiterName => 'Hakamning ism-sharifi';

  @override
  String get agArbiterRole => 'Kim (masalan, mahalla oqsoqoli)';

  @override
  String get agWitnesses => 'Guvohlar (vergul bilan)';

  @override
  String get agTermMonths => 'Muddat (oy)';

  @override
  String get agReviewDate => 'Yillik yangilash sanasi';

  @override
  String agReviewOn(String date) {
    return 'Yangilash: $date';
  }

  @override
  String get agErrPartiesMin2 => 'Kamida ikki tomon (ismi bilan) kerak.';

  @override
  String get agErrContribution => 'Har bir tomonning hissasi yozilsin.';

  @override
  String get agErrDutyOwner => 'Har vazifaga bitta masʼul tanlang.';

  @override
  String get agErrDutyBreach => 'Har vazifaga «bajarilmasa» bandini yozing.';

  @override
  String get agErrShares => 'Ulushlar yigʻindisi 100 % boʻlsin.';

  @override
  String get agErrGuaranteed =>
      'Bu sheriklik emas — qatʼiy summa ribo yoki qarz boʻladi. Foyda faqat foizda.';

  @override
  String get agErrArbiterParty => 'Hakam tomonlardan biri boʻla olmaydi.';

  @override
  String get agErrNaReason => '«Tegishli emas» uchun izoh yozing.';

  @override
  String get agErrTitle => 'Nomini yozing.';

  @override
  String get agErrIncomplete => 'Avval 9 savolning hammasiga javob bering.';

  @override
  String get agErrFuture => 'Ogʻzaki kelishuv oʻtgan sanadan boshlanadi.';

  @override
  String get agErrNotSigned => 'Avval hamma imzolasin.';

  @override
  String get agSignatures => 'Imzolar';

  @override
  String get agPrepareSign => 'Imzolashga oʻtish';

  @override
  String get agSignInPartnership => 'Imzolar sheriklik shartnomasi ekranida';

  @override
  String get agActivate => 'Kuchga kiritish';

  @override
  String get agRenewUnchanged => 'Yillik yangilash: oʻzgarishsiz tasdiqlash';

  @override
  String get agUnchangedNote => 'Oʻzgarishsiz tasdiqlandi';

  @override
  String get agNewVersion => 'Yangi versiya (oʻzgartirish)';

  @override
  String get agJournal => 'Hisob jurnali';

  @override
  String agChainOk(int n) {
    return '$n ta yozuv · zanjir butun, hech biri oʻzgartirilmagan';
  }

  @override
  String agChainBroken(int n) {
    return 'Diqqat: $n-yozuvdan boshlab zanjir buzilgan — yozuv oʻzgartirilgan boʻlishi mumkin';
  }

  @override
  String get agChainHead => 'Zanjir boshi';

  @override
  String get agJContribution => 'Hissa';

  @override
  String get agJProfit => 'Foyda ulushi';

  @override
  String get agJLoss => 'Zarar ulushi';

  @override
  String get agJLoanPayment => 'Qarz toʻlovi';

  @override
  String get agJIncome => 'Kirim';

  @override
  String get agJExpense => 'Xarajat';

  @override
  String get agJForceMajeure => 'Fors-major';

  @override
  String get agJBuyout => 'Ulush sotib olish';

  @override
  String get agJOpening => 'Boshlangʻich holat';

  @override
  String get agJCorrection => 'Tuzatish';

  @override
  String get agPdfShare => 'Kelishuv PDF';

  @override
  String agPdfSubtitle(int version, String date) {
    return '$version-versiya · $date dan';
  }

  @override
  String get agPdfIntro =>
      '9 ta asosiy savol boʻyicha oddiy tilda yozilgan kelishuv.';

  @override
  String get agPdfNote =>
      'Shaxsiy hisob uchun yozuv, yuridik kafolat yoki maslahat emas.';

  @override
  String get agFieldTitle => 'Nomi (masalan, doʻkon ijarasi)';

  @override
  String get agFieldMe => 'Sizning ismingiz';

  @override
  String get agFieldOther => 'Ikkinchi tomon';

  @override
  String get agFieldType => 'Turi';

  @override
  String get agOralTitle => 'Ogʻzaki kelishuvni yozib olish';

  @override
  String get agOralHint =>
      'Hozir ogʻzaki davom etayotgan sheriklik, ijara yoki qarz';

  @override
  String get agOralIntro =>
      'Kelishuv oʻtgan sanadan boshlangan boʻlishi mumkin. Shu kungacha holatni bitta yozuv qilib kiriting — tomonlar uni ham imzolab tasdiqlaydi.';

  @override
  String get agOralSince => 'Qachondan beri';

  @override
  String get agOralOpening => 'Shu kungacha holat';

  @override
  String get agOralOpeningHint =>
      'Kim qancha qoʻshgan, qancha boʻlingan, qancha qarz qolgan.';

  @override
  String get agOralMine => 'Siz qoʻshgan';

  @override
  String get agOralTheirs => 'Ikkinchi tomon qoʻshgan';

  @override
  String get agOralNote => 'Izoh (masalan, 3 oyda 2 marta foyda boʻlingan)';

  @override
  String get agOralSave => 'Yozib olish va 9 savolga oʻtish';

  @override
  String get acDutiesTitle => 'Vazifalar';

  @override
  String get acDutyReport => 'Bajara olmayapman';

  @override
  String get acDutyReportTitle => 'Vazifani bajara olmayapman';

  @override
  String get acDutyReason => 'Sabab';

  @override
  String get acDutyFix => 'Oʻrniga yechim (ixtiyoriy)';

  @override
  String get acDutyWho => 'Kim xabar bermoqda';

  @override
  String get acDutyClauseTitle => 'Shartnoma bandi';

  @override
  String acDutyClauseBody(Object clause) {
    return '$clause\n\nBu ayb emas — kelishilgan qoidaga qaytamiz.';
  }

  @override
  String get acIncidentsTitle => 'Oxirgi koʻrikdan keyingi hodisalar';

  @override
  String acIncidentLine(Object reason, Object fix) {
    return '$reason — $fix';
  }

  @override
  String acIncidentNoFix(Object reason) {
    return '$reason';
  }

  @override
  String get acReviewTitle => 'Oylik ochiq hisob koʻrigi';

  @override
  String acReviewNext(Object date) {
    return 'Keyingi koʻrik: $date';
  }

  @override
  String get acReviewDue => 'Koʻrik vaqti keldi';

  @override
  String acReviewOpenInfo(Object date) {
    return 'Koʻrik ochiq. Kesim sanasi: $date';
  }

  @override
  String get acReviewStart => 'Koʻrikni boshlash';

  @override
  String get acReviewContinue => 'Koʻrikka oʻtish';

  @override
  String acReviewMinutesCount(int count) {
    return 'Bayonnomalar: $count';
  }

  @override
  String get acReviewScreenTitle => 'Koʻrik';

  @override
  String acReviewCutoff(Object date) {
    return 'Kesim sanasi: $date';
  }

  @override
  String get acReviewPeriodTitle => 'Davr yozuvlari';

  @override
  String get acReviewPeriodEmpty => 'Bu davrda yozuv yoʻq.';

  @override
  String acReviewTotals(Object income, Object expense) {
    return 'Kirim: $income · Chiqim: $expense';
  }

  @override
  String acReviewChainOk(int count) {
    return 'Zanjir butun ($count ta yozuv)';
  }

  @override
  String acReviewChainBroken(int seq) {
    return 'Zanjir buzilgan: #$seq';
  }

  @override
  String get acReviewIncidents => 'Hodisalar';

  @override
  String get acReviewAgree => 'Koʻrdim, roziman';

  @override
  String get acReviewObject => 'Eʼtirozim bor';

  @override
  String get acReviewObjectTitle => 'Eʼtiroz';

  @override
  String get acReviewObjectHint => 'Nimaga rozi emassiz?';

  @override
  String acReviewVerdictAgree(Object party) {
    return '$party: roziman';
  }

  @override
  String acReviewVerdictObject(Object party, Object note) {
    return '$party: eʼtiroz — $note';
  }

  @override
  String get acReviewWaiting =>
      'Hamma tomon javob bergach, bayonnomani yakunlang.';

  @override
  String get acReviewComplete => 'Bayonnomani yakunlash';

  @override
  String get acReviewDone => 'Koʻrik yakunlandi. Bayonnoma saqlandi.';

  @override
  String get acReviewLockedNote =>
      'Bu sanagacha boʻlgan moliyaviy yozuvlar muzlatiladi; faqat tuzatuvchi yozuv qoʻshiladi.';

  @override
  String get acReviewMinutesShare => 'Bayonnomani ulashish (PDF)';

  @override
  String get acReviewLedgerTitle => 'Hisob yozuvlari';

  @override
  String get acDisputesTitle => 'Nizolar';

  @override
  String get acDisputeNone => 'Ochiq nizo yoʻq.';

  @override
  String get acDisputeOpen => 'Nizo ochish';

  @override
  String get acDisputeTopic => 'Mavzu';

  @override
  String get acDisputeClause => 'Tegishli band (ixtiyoriy)';

  @override
  String get acDisputeClaim => 'Sizning talabingiz';

  @override
  String get acDisputeAddClaim => 'Talab qoʻshish';

  @override
  String get acDisputeStatusOpen => 'Ochiq';

  @override
  String get acDisputeStatusDecided => 'Hal qilingan';

  @override
  String get acDisputeScreenTitle => 'Nizo';

  @override
  String get acDisputeClaimsTitle => 'Tomonlar talablari';

  @override
  String get acDisputeDecisionTitle => 'Hakam qarori';

  @override
  String get acDisputeDecisionHint => 'Qaror matni';

  @override
  String get acDisputeDecide => 'Qarorni yozish';

  @override
  String get acDisputePdf => 'Hakam uchun ish papkasi (PDF)';

  @override
  String get acDisputeInDispute => 'Kelishuv nizoda: taqsimot toʻxtatilgan.';

  @override
  String get acDisputeDecidedNote => 'Qaror yozildi. Kelishuv yana faol.';

  @override
  String get acRenewalTitle => 'Yillik yangilash';

  @override
  String acRenewalDue(Object date) {
    return 'Yangilash sanasi: $date. Eslatma 30 kun oldin keladi.';
  }

  @override
  String get acRenewalUnchanged => 'Oʻzgarishsiz tasdiqlash';

  @override
  String get acRenewalNeedsSign =>
      'Yangi versiyani hamma qayta imzolashi kerak.';

  @override
  String get acRenewalNotifTitle => 'Kelishuvni yangilash vaqti';

  @override
  String acRenewalNotifBody(Object title) {
    return '«$title» 30 kundan keyin yangilanadi. Birga qayta oʻqing.';
  }

  @override
  String get acRenewalChannel => 'Kelishuv eslatmalari';

  @override
  String get acSpikeTitle => 'Katta foyda';

  @override
  String get acSpikeMessage =>
      'Barakali foyda — tabriklaymiz! Endi kelishuvni birga qayta oʻqib chiqaylik.';

  @override
  String acSpikeAmount(Object amount) {
    return 'Davr foydasi: $amount';
  }

  @override
  String acSpikeRead(Object party) {
    return '$party 4–5-bandni qayta oʻqidi';
  }

  @override
  String get acSpikeReviewOffer => 'Navbatdan tashqari koʻrik';

  @override
  String get acSpikeDistribute => 'Taqsimlash';

  @override
  String get acSpikeCancel => 'Hozircha emas';

  @override
  String get acHomeTitle => 'Yaqinlashayotgan koʻrik / yangilash';

  @override
  String acHomeBody(int count) {
    return '$count ta kelishuvda koʻrik yoki yangilash vaqti yaqin.';
  }

  @override
  String acHomeDisputes(int count) {
    return 'Ochiq nizo: $count';
  }

  @override
  String acCenterNextReview(Object date) {
    return 'Keyingi koʻrik: $date';
  }

  @override
  String acCenterOpenIncidents(int count) {
    return 'Ochiq hodisa: $count';
  }

  @override
  String acCenterDisputes(int count) {
    return 'Nizo: $count';
  }

  @override
  String get acCenterEmptyHint =>
      'Koʻrik va yangilash sanalari bu yerda koʻrinadi.';

  @override
  String get agFamilyTemplate => 'Shablon';

  @override
  String get agFamilyHint =>
      'Oilaviy kelishuv buyruq emas — birga kelishuv. Guvoh va hakam shart emas; kattalarning tasdigʻi yetarli.';

  @override
  String get agTplChores => 'Uyda kim nima qiladi';

  @override
  String get agTplChoresHint =>
      'Har kimning uy ishi aniq; bajarilmasa — ayblamasdan xabar bering.';

  @override
  String get agTplMoney => 'Pul qayerda turadi va kim yuritadi';

  @override
  String get agTplMoneyHint =>
      'Umumiy pul qayerda, kim yuritadi va qanday koʻrinadi.';

  @override
  String get agTplHavas => 'Havas chegarasi';

  @override
  String get agTplHavasHint =>
      'Oilada havas xarajatlari chegarasi (Havas boʻlimi bilan bogʻlanadi).';

  @override
  String get agTplCouncil => 'Oila kengashi qachon oʻtadi';

  @override
  String get agTplCouncilHint =>
      'Oylik kengash kuni va qanday qarorlar qabul qilinadi.';

  @override
  String get agJDutyIncident => 'Vazifa bajarilmadi';

  @override
  String get agJReviewOpened => 'Koʻrik ochildi';

  @override
  String get agJReviewAck => 'Koʻrik javobi';

  @override
  String get agJAccountReview => 'Koʻrik bayonnomasi';

  @override
  String get agJProfitSpikeAck => '«Katta foyda» tasdigʻi';

  @override
  String get agJDisputeOpened => 'Nizo';

  @override
  String get agJArbiterDecision => 'Hakam qarori';

  @override
  String get agErrReviewLocked =>
      'Bu sanagacha yozuvlar koʻrik bayonnomasi bilan qulflangan.';

  @override
  String get agErrReviewOpen => 'Koʻrik ochiq. Avval uni yakunlang.';

  @override
  String get agErrNoReview => 'Bu koʻrik ochiq emas.';

  @override
  String get agErrReviewIncomplete => 'Hamma tomon javob bersin.';

  @override
  String get agErrReviewAcked => 'Bu tomon allaqachon javob bergan.';

  @override
  String get agErrObjection => 'Eʼtiroz uchun izoh yozing.';

  @override
  String get agErrReasonRequired => 'Sababni yozing.';

  @override
  String get agErrDutyNotFound => 'Vazifa topilmadi.';

  @override
  String get agErrPartyNotFound => 'Tomon topilmadi.';

  @override
  String get agErrInDispute => 'Kelishuv nizoda — avval hakam qarori kerak.';

  @override
  String get agErrDisputeNotFound => 'Nizo topilmadi.';

  @override
  String get agErrDisputeDecided => 'Bu nizo allaqachon hal qilingan.';

  @override
  String get agErrClaimRequired => 'Mavzu va talabni yozing.';

  @override
  String get agErrDecisionRequired => 'Qaror matnini yozing.';

  @override
  String get agErrSpikeAck =>
      'Katta foyda: ikkala tomon 4–5-bandni qayta oʻqib tasdiqlasin.';

  @override
  String get agErrAcked => 'Bu tomon allaqachon tasdiqlagan.';

  @override
  String get acPdfColDate => 'Sana';

  @override
  String get acPdfColKind => 'Tur';

  @override
  String get acPdfColParty => 'Tomon';

  @override
  String get acPdfColAmount => 'Summa';

  @override
  String get acPdfColNote => 'Izoh';

  @override
  String get acReviewAcksTitle => 'Tomonlar javobi';

  @override
  String get acPdfFolderAgreement => 'Kelishuv';

  @override
  String get acPdfFolderVersions => 'Versiyalar tarixi';

  @override
  String get acPdfFolderParties => 'Tomonlar';

  @override
  String get acPdfFolderLedger => 'Davr yozuvlari va zanjir tekshiruvi';

  @override
  String get acPdfFolderMinutes => 'Koʻrik bayonnomalari';

  @override
  String get acPdfFolderIncidents => 'Vazifa hodisalari';

  @override
  String get acPdfFolderClaims => 'Tomonlarning talablari';

  @override
  String get acPdfFolderDecision => 'Hakam qarorlari';

  @override
  String get acPdfFolderIntegrity => 'Zanjir yaxlitligi';

  @override
  String get acPdfNoDecision => 'Hakam qarori hali yoʻq.';

  @override
  String get acPdfNone => 'Yoʻq';

  @override
  String acPdfMinutesLine(Object date, Object id, Object head) {
    return '$date · $id · zanjir boshi $head';
  }

  @override
  String acPdfObjection(Object note) {
    return 'Eʼtiroz: $note';
  }

  @override
  String acPdfClaimLine(Object party, Object claim) {
    return '$party: $claim';
  }

  @override
  String acPdfDecisionLine(Object date, Object decision) {
    return '$date · $decision';
  }

  @override
  String acPdfCutoffLine(Object date) {
    return 'Kesim: $date';
  }

  @override
  String acPdfIncidentLine(Object date, Object party, Object reason) {
    return '$date · $party: $reason';
  }

  @override
  String get offerQExit => 'Pulni istagan vaqtda qaytarib olsa boʻladimi?';

  @override
  String get offerQLicense => 'Odamlardan pul yigʻishga davlat ruxsati bormi?';

  @override
  String get offerQVerified =>
      'Ishni oʻz koʻzingiz bilan koʻrdingizmi (ombor, mol, hujjat)?';

  @override
  String get offerFlagExit =>
      'Pulni qaytarib olish qiyin — kirish oson, chiqish qiyin boʻlsa, qoching.';

  @override
  String get offerFlagLicense =>
      'Davlat ruxsati yoʻq — odamlardan pul yigʻish qonuniy boʻlmasligi mumkin.';

  @override
  String get offerFlagVerified =>
      'Ishni koʻrsatishmadi. Halol taklif egasi ishini koʻrsatishdan qochmaydi.';

  @override
  String get offerVerifyTitle =>
      'Pul qoʻyishdan oldin oʻz koʻzingiz bilan koʻring';

  @override
  String get offerVerifyGoods => 'Ombor va mol: nima sotiladi, qayerda turadi?';

  @override
  String get offerVerifyDocs =>
      'Shartnoma: pul nimaga ishlatiladi, zarar kim zimmasida?';

  @override
  String get offerVerifyLicense => 'Odamlardan pul yigʻishga davlat ruxsati';

  @override
  String get offerVerifySource =>
      'Toʻlovlar qayerdan: mol sotuvidanmi yoki yangi kirganlarning pulidanmi?';

  @override
  String get offerVerifyExit => 'Pulni qaytarib olish tartibi';

  @override
  String get offerVerifyHint =>
      'Ishi halol odam bu iltimosdan quvonadi. Rad etish yoki shoshirishning oʻzi xavf belgisi.';

  @override
  String get offerRate => 'Vaʼda qilingan foyda, oyiga % (ixtiyoriy)';

  @override
  String offerRateYearly(Object rate, Object simple, Object compound) {
    return 'Oyiga $rate % — yiliga oddiy hisobda $simple barobar, murakkab hisobda $compound barobar. Bunday daromadni halol savdo yoki ishlab chiqarish barqaror bera olmaydi.';
  }

  @override
  String get offerAmount => 'Qancha pul qoʻymoqchisiz? (ixtiyoriy)';

  @override
  String get offerSignsTitle => 'Besh xavf belgisi';

  @override
  String get offerSignsNone =>
      'Xavf belgisi topilmadi. Baribir ishni oʻz koʻzingiz bilan koʻring.';

  @override
  String get offerSignsCaution => 'Bitta belgi bor — hushyor torting.';

  @override
  String get offerSignsFlee => 'Ikki va undan koʻp belgi — qoching.';

  @override
  String get offerSignGuaranteed =>
      'Katta foyda kafolatlanmoqda: halol foydaning kafolati boʻlmaydi, unda tavakkal bor.';

  @override
  String get offerSignUrgency =>
      'Shoshirishmoqda: oʻylab olishingizdan qoʻrqishadi.';

  @override
  String get offerSignRecruit =>
      'Daromad moldan emas, yangi odam olib kelishdan.';

  @override
  String get offerSignNoBusiness =>
      'Ishning oʻzi koʻrinmaydi: mol, hujjat yoki ruxsat yoʻq, faqat idora.';

  @override
  String get offerSignHardExit => 'Kirish oson, chiqish qiyin.';

  @override
  String get offerCatRibo => 'Ribo: zarar boʻlishilmaydigan kafolatli foyda.';

  @override
  String get offerCatGharar =>
      'Gʻarar: noaniq bitim — nima sotilayotgani, pul qayerda ishlayotgani nomaʼlum.';

  @override
  String get offerCatQimor =>
      'Qimor: yutuq faqat boshqaning yutqazishidan — toʻlov yangi kirganlarning pulidan.';

  @override
  String get offerPyramidTitle => 'Piramida qanday choʻkadi?';

  @override
  String get offerPyramidRecruits => 'Har kishi necha odam olib keladi';

  @override
  String get offerPyramidPopulation => 'Shahar aholisi';

  @override
  String offerPyramidResult(int levels, Object share) {
    return '$levels-qavatda odam tugaydi. Eng pastki qavatda $share % odam boʻladi — choʻkkan kuni ular pulini yoʻqotadi. Siz qaysi qavatda boʻlasiz?';
  }

  @override
  String get offerPyramidBait =>
      'Birinchi kirganlarga toʻlov — boshqalarni jalb qilish uchun: u yangi kirganlarning pulidan toʻlanadi.';

  @override
  String get offerDecisionTitle => 'Qaror';

  @override
  String get offerAdvisor => 'Kim bilan maslahatlashdingiz?';

  @override
  String get offerAdviceNote =>
      'Maslahat soʻrash — zaiflik emas. Bir kecha uxlab koʻring: bir soat vaqt ajratish yillik mehnatni asraydi.';

  @override
  String get offerDecline => 'Rad etdim';

  @override
  String get offerPostpone => 'Keyinga qoldiraman';

  @override
  String get offerAccept => 'Pul qoʻyaman';

  @override
  String offerAcceptOpensAt(Object time) {
    return '«Pul qoʻyaman» $time dan keyin ochiladi.';
  }

  @override
  String get offerDecisionDeclined => 'Rad etildi';

  @override
  String get offerDecisionPostponed => 'Keyinga qoldirildi';

  @override
  String get offerDecisionAccepted => 'Pul qoʻyildi';

  @override
  String get offerDecisionSaved => 'Qaror yozildi.';

  @override
  String get offerErrAdvisor =>
      'Avval kim bilan maslahatlashganingizni yozing.';

  @override
  String get offerErrCoolingOff =>
      'Tekshiruvdan keyin 24 soat oʻtmaguncha bu qaror ochilmaydi.';

  @override
  String get offerErrDecided =>
      'Bu taklif boʻyicha qaror allaqachon qabul qilingan.';

  @override
  String get offerErrRate => 'Foizni toʻgʻri yozing (masalan, 35 yoki 2,5).';

  @override
  String get lumpTitle => 'Katta summa tushdi';

  @override
  String get lumpHint =>
      'Katta summa qoʻlga kirdimi (yillar davomidagi jamgʻarma, meros yoki mulk sotuvi)? Avval oilaning olti oylik zaxirasini toʻldiring, qolganini hunarga ishlating.';

  @override
  String get lumpAmount => 'Summa';

  @override
  String lumpRate(Object currency) {
    return 'Kurs: 1 $currency necha soʻm';
  }

  @override
  String lumpReserve(Object amount) {
    return 'Oilaviy zaxiraga (6 oy): $amount';
  }

  @override
  String lumpInvest(Object amount) {
    return 'Hunarga ishlatish mumkin: $amount';
  }

  @override
  String get lumpWallNote =>
      'Bu pulni savdoga ham, sheriklikka ham qoʻshmaysiz.';

  @override
  String get lumpReserveFull =>
      'Oilaviy zaxira allaqachon toʻla — hammasini hunarga ishlatsa boʻladi.';

  @override
  String get lumpNoTarget =>
      'Avval 6 oylik zarur xarajatni belgilang — shunda zaxira qancha boʻlishi kerakligi maʼlum boʻladi.';

  @override
  String get lumpDeposit => 'Zaxiraga qoʻyish';

  @override
  String get lumpDeposited => 'Zaxiraga qoʻyildi.';

  @override
  String get lumpIdeas => 'Hunardan ishga oʻtish';

  @override
  String get lumpOpen => 'Katta summa tushdimi?';

  @override
  String get ideaTplWorkshop => 'Shablon: payvandlash ustaxonasi';

  @override
  String get ideaTplWelder => 'Payvand apparati';

  @override
  String get ideaTplGrinder => 'Kesish asbobi (bolgarka)';

  @override
  String get ideaTplRent => 'Ustaxona ijarasi (birinchi oy)';

  @override
  String get ideaTplMetal => 'Metall (birinchi buyurtmalar uchun)';

  @override
  String get ideaTplSafety => 'Himoya kiyimi va niqob';

  @override
  String get ideaDemandQ =>
      'Talab bormi? Kim buyurtma beradi, atrofda qancha uy qurilmoqda yoki yangilanmoqda?';

  @override
  String get ideaTplSuggest =>
      'Kerak boʻladiganlar — bosing va narxini yozing:';

  @override
  String get aboutTitle => 'Ilova haqida';

  @override
  String get settingsAboutHint => 'Versiya, muallif va huquqlar';

  @override
  String aboutVersion(String version, int build) {
    return 'Versiya $version ($build)';
  }

  @override
  String aboutAuthor(String author) {
    return 'Muallif: $author';
  }

  @override
  String aboutCopyright(String year, String author) {
    return '© $year $author. Barcha huquqlar himoyalangan.';
  }

  @override
  String get aboutRights =>
      'Ilovani nusxalash, oʻzgartirish, tarqatish yoki muallifning yozma ruxsatisiz nashr qilish taqiqlanadi.';

  @override
  String get aboutPrivacy =>
      'Maʼlumotlaringiz faqat shu qurilmada, shifrlangan holda saqlanadi. Ilova internetga ulanmaydi.';

  @override
  String get aboutLicenses => 'Ochiq kodli kutubxonalar litsenziyalari';

  @override
  String get demoBanner => 'DEMO';

  @override
  String demoNotice(String year, String author) {
    return 'Demo versiya · © $year $author · nashr qilish va tarqatish taqiqlanadi';
  }

  @override
  String demoUntil(String date) {
    return 'Demo versiya: $date gacha ishlaydi';
  }

  @override
  String get demoExpiredTitle => 'Demo muddati tugadi';

  @override
  String demoExpiredBody(String date, String author) {
    return 'Bu demo versiya $date gacha ishlashi kerak edi. Toʻliq versiya uchun muallif bilan bogʻlaning: $author.';
  }

  @override
  String get lnTitle => 'Bilimga sarmoya';

  @override
  String get lnHint =>
      'Bir soatingiz qancha turishini biling va uni qimmatlashtiradigan bilimni aniq maqsad bilan oʻrganing.';

  @override
  String get lnHourlyTitle => 'Bir soatim qancha turadi?';

  @override
  String get lnHourlyEmpty =>
      'Hali hisoblanmagan. Oylik daromad va ish soatlaringizni kiriting.';

  @override
  String lnHourlyValue(String amount) {
    return 'Bir soatingiz: $amount';
  }

  @override
  String lnHourlyDoubled(String amount) {
    return 'Ikki barobar maqsad: $amount';
  }

  @override
  String lnHourlyLoad(String percent) {
    return 'Kunlik chegaraning $percent % i band';
  }

  @override
  String lnHourlyCeiling(String amount) {
    return 'Faqat soat qoʻshib erishiladigan eng katta oylik daromad: $amount';
  }

  @override
  String get lnHourlyNoDouble =>
      'Daromadni faqat soatni koʻpaytirib ikki barobar qilib boʻlmaydi — kun bunga yetmaydi. Soatning oʻzini qimmatlashtiring.';

  @override
  String get lnHourlyCanDouble =>
      'Soat qoʻshish mumkin, lekin dam olish va oilaga vaqt qolishini oʻylang. Soatni qimmatlashtirish uzoqroq xizmat qiladi.';

  @override
  String lnHourlyChange(String old, String now) {
    return 'Avvalgi hisob: $old → hozir $now';
  }

  @override
  String get lnHourlyExplain =>
      'Soat qoʻshish bilan daromad chegaradan oshmaydi. Soatning oʻzini qimmatlashtirish — bilim va mahorat ishi.';

  @override
  String get lnHourlyCalc => 'Hisoblash';

  @override
  String get lnHourlyRecalc => 'Qayta hisoblash';

  @override
  String get lnIncome => 'Oylik daromad';

  @override
  String get lnIncomeSuggested => 'Oʻtgan oy daromadi taklif qilindi';

  @override
  String get lnHoursPerDay => 'Kuniga necha soat ishlaysiz';

  @override
  String get lnDaysPerMonth => 'Oyiga necha kun ishlaysiz';

  @override
  String get lnMaxHours => 'Kunlik jismoniy chegara (soat)';

  @override
  String get lnMaxHoursHint =>
      'Dam olish, oila va sogʻliq uchun vaqt qolishi kerak. Chegarani oʻzingiz belgilang.';

  @override
  String get lnErrHours =>
      'Soat 0,5 dan 24 gacha, kunlar 1 dan 31 gacha boʻlsin.';

  @override
  String get lnErrAmount => 'Summa yoki vaqt manfiy boʻlmaydi.';

  @override
  String get lnGoalsTitle => 'Oʻqish maqsadlari';

  @override
  String get lnGoalsEmpty =>
      'Soatingizni qimmatlashtiradigan bitta bilimni tanlang.';

  @override
  String get lnGoalsNeedHourly =>
      'Avval bir soatingiz qancha turishini hisoblang.';

  @override
  String get lnGoalNew => 'Yangi maqsad';

  @override
  String get lnGoalTitleField => 'Qaysi bilim yoki mahorat?';

  @override
  String get lnGoalWhy => 'Nega aynan shu? Qaysi ishni yaxshiroq qila olasiz?';

  @override
  String get lnGoalTarget => 'Maqsad soat qiymati';

  @override
  String get lnGoalFocus =>
      'Maslahat: bir vaqtda bitta bilimga eʼtibor qarating.';

  @override
  String lnGoalRange(String from, String to) {
    return 'Soatiga $from → $to';
  }

  @override
  String lnGoalItems(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count ta yoʻl',
      zero: 'Yoʻl qoʻshilmagan',
    );
    return '$_temp0';
  }

  @override
  String get lnGoalStatusActive => 'Faol';

  @override
  String get lnGoalStatusDone => 'Erishildi';

  @override
  String get lnGoalStatusDropped => 'Toʻxtatildi';

  @override
  String get lnGoalMarkDone => 'Maqsadga erishdim';

  @override
  String get lnGoalDrop => 'Toʻxtataman';

  @override
  String get lnGoalReopen => 'Qayta faollashtirish';

  @override
  String get lnItemsTitle => 'Oʻqish yoʻllari';

  @override
  String get lnItemsEmpty =>
      'Kitob, ustoz, kurs yoki amaliyotdan birini qoʻshing.';

  @override
  String get lnItemAdd => 'Yoʻl qoʻshish';

  @override
  String get lnKindBook => 'Kitob';

  @override
  String get lnKindMentor => 'Ustoz';

  @override
  String get lnKindCourse => 'Kurs';

  @override
  String get lnKindPractice => 'Amaliyot';

  @override
  String get lnItemTitle => 'Nomi';

  @override
  String get lnItemPurpose => 'Buni oʻrgangach nimani qila olaman?';

  @override
  String get lnItemPurposeHint =>
      'Natija aniq boʻlsa, oʻqish ham samarali boʻladi.';

  @override
  String get lnItemCost => 'Narxi';

  @override
  String get lnItemStudyHours => 'Oʻqishga ketadigan vaqt (soat)';

  @override
  String get lnItemNoDebt =>
      'Oʻqishni qarzga olmang: jamgʻarmadan yoki joriy daromaddan toʻlang.';

  @override
  String lnItemPurposeLabel(String purpose) {
    return 'Natija: $purpose';
  }

  @override
  String lnItemOutcomeLabel(String outcome) {
    return 'Erishildi: $outcome';
  }

  @override
  String lnItemHours(String hours) {
    return '$hours soat';
  }

  @override
  String get lnItemStatusPlanned => 'Rejada';

  @override
  String get lnItemStatusInProgress => 'Oʻqiyapman';

  @override
  String get lnItemStatusDone => 'Tugatdim';

  @override
  String get lnItemStatusDropped => 'Tashladim';

  @override
  String get lnItemStart => 'Boshlash';

  @override
  String get lnItemFinish => 'Tugatdim';

  @override
  String get lnItemDrop => 'Tashlash';

  @override
  String get lnItemOutcome => 'Nimani qila oladigan boʻldingiz?';

  @override
  String get lnErrTitle => 'Nomini yozing.';

  @override
  String get lnErrPurpose =>
      '«Buni oʻrgangach nimani qila olaman?» savoliga javob yozing.';

  @override
  String get lnErrOutcome => 'Erishilgan natijani yozing.';

  @override
  String get lnErrNoHourly => 'Avval soat qiymatini hisoblang.';

  @override
  String get lnErrTeaching => 'Kimga va nimani oʻrgatganingizni yozing.';

  @override
  String get lnPaybackTitle => 'Oʻqish qachon oʻzini qoplaydi? (taxmin)';

  @override
  String lnPaybackInvest(String cost, String time, String total) {
    return 'Narx $cost + vaqt qiymati $time = $total';
  }

  @override
  String lnPaybackGain(String amount) {
    return 'Soatingiz maqsadga yetsa, oyiga qoʻshimcha: $amount';
  }

  @override
  String lnPaybackMonths(int months) {
    String _temp0 = intl.Intl.pluralLogic(
      months,
      locale: localeName,
      other: 'Shunda xarajat taxminan $months oyda qoplanadi.',
    );
    return '$_temp0';
  }

  @override
  String get lnPaybackNever =>
      'Bu maqsad bilan xarajat qoplanmaydi — maqsad soat qiymatini qayta koʻring.';

  @override
  String get lnPaybackFree => 'Pul va vaqt xarajati yozilmagan.';

  @override
  String get lnPaybackNote =>
      'Bu vaʼda emas — sizning raqamlaringiz boʻyicha taxmin.';

  @override
  String get lnCourseCheck => 'Kursni tekshirish';

  @override
  String get lnCourseTitle => 'Kurs tekshiruvi: bilim beradimi?';

  @override
  String get lnCourseQIncome => 'Qisqa vaqtda maʼlum daromad kafolatlanadimi?';

  @override
  String get lnCourseQPressure =>
      '«Faqat bugun», «joy kam» deb shoshirishadimi?';

  @override
  String get lnCourseQReferral => 'Daromad yangi oʻquvchi olib kelishdanmi?';

  @override
  String get lnCourseQSecret =>
      '«Faqat shu yerda oʻrgatiladigan maxfiy usul» deb sotiladimi?';

  @override
  String get lnCourseQCurriculum =>
      'Dastur, amaliy topshiriqlar va oxirida nimani qila olishingiz oldindan koʻrsatildimi?';

  @override
  String get lnCourseQTeacher =>
      'Oʻqituvchi shu ish bilan amalda shugʻullanadimi, ishini koʻrsata oladimi?';

  @override
  String get lnCourseQRefund => 'Toʻlovni qaytarish shartlari yozma bormi?';

  @override
  String get lnCourseGreen =>
      'Xavf belgisi topilmadi. Baribir dastur va natijani yozib qoʻying.';

  @override
  String get lnCourseYellow =>
      'Hushyor boʻling: toʻlashdan oldin aniqlashtiring.';

  @override
  String get lnCourseRed =>
      'Ikki va undan ortiq xavf belgisi — bu kursga pul toʻlamang.';

  @override
  String get lnCourseSignIncome =>
      'Daromad kafolati: halol taʼlim natijani oʻquvchining mehnatiga bogʻlaydi, kafolatlamaydi.';

  @override
  String get lnCourseSignUrgency =>
      'Shoshirish: yaxshi kurs oʻylab koʻrishga vaqt beradi.';

  @override
  String get lnCourseSignReferral =>
      'Daromad yangi oʻquvchilardan: bu bilim emas, odam yigʻish.';

  @override
  String get lnCourseSignNoSkill =>
      'Haqiqiy mahorat koʻrinmaydi: dastur, amaliyot yoki oʻqituvchining ishi yoʻq.';

  @override
  String get lnCourseSignRefund =>
      'Qaytarish sharti yoʻq: pul toʻlangach chiqish qiyin.';

  @override
  String get lnCourseSave => 'Natijani saqlash';

  @override
  String get lnCourseRedConfirmTitle => 'Kursda xavf belgilari bor';

  @override
  String get lnCourseRedConfirmBody =>
      'Tekshiruv qizil natija berdi. Baribir oʻqishni boshlaysizmi?';

  @override
  String get lnCourseRedConfirmYes => 'Ha, boshlayman';

  @override
  String get lnTeachTitle => 'Oʻrgatganlarim';

  @override
  String get lnTeachHint =>
      'Bilganingizni boshqaga tushuntirsangiz, oʻzingiz ham chuqurroq oʻrganasiz.';

  @override
  String get lnTeachAdd => 'Yozib qoʻyish';

  @override
  String get lnTeachLearner => 'Kimga (ism yoki «hamkasb», «farzandim»)';

  @override
  String get lnTeachTopic => 'Nimani oʻrgatdingiz?';

  @override
  String get lnTeachMinutes => 'Qancha vaqt (daqiqa, ixtiyoriy)';

  @override
  String get lnTeachNote => 'Izoh (ixtiyoriy)';

  @override
  String get lnTeachEmpty => 'Hali yozuv yoʻq.';

  @override
  String get lnKeepTitle => 'Bilim odam bilan qoladi';

  @override
  String get lnKeepBody =>
      'Pul va mol yoʻqolishi mumkin, oʻrganilgan mahorat esa siz bilan qoladi. Narxlar oshganda yoki ish oʻzgarganda u yangi yoʻl topishga yordam beradi.';
}

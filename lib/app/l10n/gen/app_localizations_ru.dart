// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Russian (`ru`).
class AppLocalizationsRu extends AppLocalizations {
  AppLocalizationsRu([String locale = 'ru']) : super(locale);

  @override
  String get appTitle => 'Барака Дастур';

  @override
  String get languageName => 'Русский';

  @override
  String get switchLanguageTooltip => 'Сменить язык';

  @override
  String get switchThemeTooltip => 'Сменить тему';

  @override
  String get placeholderNotice =>
      'Этот экран будет заполнен в следующих задачах.';

  @override
  String get homeTitle => 'Главная';

  @override
  String get homeDescription =>
      'Здесь будут сумма «Заплачено себе», баланс «Моё будущее» и задачи недели.';

  @override
  String get homeSectionsHeader => 'Разделы';

  @override
  String get incomeNewTitle => 'Новый доход';

  @override
  String get incomeNewDescription =>
      'Здесь доход вводится в несколько нажатий.';

  @override
  String get vaultTitle => 'Моё будущее';

  @override
  String get vaultDescription =>
      'Здесь будут баланс фонда «Моё будущее» и серия привычки.';

  @override
  String get auditTitle => 'Месячный аудит';

  @override
  String get auditDescription =>
      'Здесь находится ответ на вопрос «Куда ушли деньги?».';

  @override
  String get contentTitle => 'Главы';

  @override
  String get nativeBridgeTitle => 'Мост безопасности';

  @override
  String get nativeBridgeChecking => 'Проверка…';

  @override
  String nativeBridgeOk(int apiVersion, int sdkInt) {
    return 'Работает · API v$apiVersion · Android SDK $sdkInt';
  }

  @override
  String get nativeBridgeUnavailable => 'Нет связи с нативным слоем';

  @override
  String get lockEnterPin => 'Введите PIN-код';

  @override
  String get lockGreeting => 'Ваша тетрадь заблокирована';

  @override
  String pinWrong(int attempts) {
    return 'Код не подошёл. Попыток до паузы: $attempts.';
  }

  @override
  String pinLockedOut(String time) {
    return 'Слишком много неверных попыток. Попробуйте снова через $time.';
  }

  @override
  String get pinVerifying => 'Проверка…';

  @override
  String get pinErrorGeneric => 'Что-то пошло не так. Попробуйте ещё раз.';

  @override
  String get pinKeyDelete => 'Стереть последнюю цифру';

  @override
  String get pinKeyBiometric => 'Войти по отпечатку';

  @override
  String pinDigitsEntered(int count) {
    return 'Введено цифр: $count из 6';
  }

  @override
  String get pinSetupTitle => 'Установка PIN-кода';

  @override
  String get pinSetupEnter =>
      'Придумайте 6-значный код для защиты вашей тетради';

  @override
  String get pinSetupConfirm => 'Введите код ещё раз';

  @override
  String get pinSetupMismatch => 'Коды не совпали. Давайте начнём заново.';

  @override
  String get pinTooSimple => 'Такой код легко угадать. Выберите другие цифры.';

  @override
  String get pinSetupNote =>
      'Сам код нигде не хранится. Не забудьте его — восстановить нельзя.';

  @override
  String get pinSetupSaving => 'Сохранение…';

  @override
  String get biometricOfferTitle => 'Вход по отпечатку';

  @override
  String get biometricOfferBody =>
      'Можно входить по отпечатку пальца или блокировке устройства, не вводя код каждый раз. Это можно отключить в любой момент.';

  @override
  String get biometricEnable => 'Включить';

  @override
  String get biometricLater => 'Пока не нужно';

  @override
  String get biometricPromptTitle => 'Барака Дастур';

  @override
  String get biometricPromptSubtitle => 'Подтвердите, чтобы открыть тетрадь';

  @override
  String get biometricPromptCancel => 'Войти по коду';

  @override
  String get biometricLockedOut =>
      'Отпечаток временно заблокирован. Войдите по коду.';

  @override
  String get integrityTitle => 'На устройстве есть признаки риска';

  @override
  String integrityBody(String risks) {
    return 'Приложение продолжит работу, но на таком устройстве безопасность ваших данных не гарантирована. Обнаружено: $risks.';
  }

  @override
  String get integrityRiskRooted => 'root-права';

  @override
  String get integrityRiskEmulator => 'эмулятор';

  @override
  String get integrityRiskDebugger => 'подключённый отладчик';

  @override
  String get integrityRiskSignature => 'подпись приложения не совпадает';

  @override
  String get integrityRiskDebuggable => 'приложение могло быть изменено';

  @override
  String get integrityDismiss => 'Понятно';

  @override
  String get homeAddIncome => 'Доход';

  @override
  String get incomeAmountHint => 'Введите сумму';

  @override
  String get incomeRecentAmounts => 'Последние суммы';

  @override
  String get incomeSourceLabel => 'Источник';

  @override
  String get incomeSourceDailyWork => 'Дневная работа';

  @override
  String get incomeSourceOrder => 'Заказ';

  @override
  String get incomeSourceSalary => 'Зарплата';

  @override
  String get incomeSourceOther => 'Другое';

  @override
  String get channelLabel => 'Способ';

  @override
  String get channelCash => 'Наличные';

  @override
  String get channelCard => 'Карта';

  @override
  String get incomeSave => 'Сохранить';

  @override
  String get incomeSaved => 'Доход записан. Пусть будет с благословением!';

  @override
  String get keypadDelete => 'Стереть последнюю цифру';

  @override
  String get shareOfferTitle => 'Сначала себе';

  @override
  String shareOfferBody(String amount) {
    return 'Из них $amount — для вашего будущего.';
  }

  @override
  String get shareOfferHint =>
      'Даже немного, но каждый раз — и это станет привычкой.';

  @override
  String get shareAllocate => 'Отложить';

  @override
  String get shareOtherAmount => 'Другая сумма';

  @override
  String get shareSkip => 'Не в этот раз';

  @override
  String get shareSkipped => 'Хорошо, в следующий раз. Тетрадь подождёт.';

  @override
  String shareDone(String amount) {
    return 'В ваше будущее отложено $amount.';
  }

  @override
  String vaultHabitWeeks(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count недель',
      few: '$count недели',
      one: '$count неделя',
    );
    return '$_temp0';
  }

  @override
  String get vaultHabitCaption => 'подряд вы платили себе';

  @override
  String vaultHabitTotal(int count) {
    return 'Всего недель с накоплением: $count';
  }

  @override
  String get vaultThisWeekDone => 'На этой неделе отложено — молодец!';

  @override
  String get vaultThisWeekPending =>
      'На этой неделе ещё не отложено. Даже небольшая сумма засчитается.';

  @override
  String get vaultBalanceLabel => 'В фонде «Моё будущее»';

  @override
  String vaultRuleSummaryPercent(String percent) {
    return 'Доля: $percent % от каждого дохода';
  }

  @override
  String vaultRuleSummaryFixed(String amount) {
    return 'Доля: $amount в месяц';
  }

  @override
  String get vaultRuleProgressiveTag => 'прогрессивно';

  @override
  String get vaultRuleEdit => 'Настроить долю';

  @override
  String get vaultWithdraw => 'Снять деньги';

  @override
  String get vaultHistory => 'История';

  @override
  String get vaultHistoryEmpty => 'Записей пока нет. Начнём с первого дохода.';

  @override
  String get vaultReasonIncomeShare => 'Доля дохода';

  @override
  String get vaultReasonInitial => 'Начальные накопления';

  @override
  String get vaultReasonManual => 'Пополнение';

  @override
  String vaultReasonWithdrawal(String note) {
    return 'Снято: $note';
  }

  @override
  String get vaultInitialTitle => 'Ранее накопленные деньги';

  @override
  String get vaultInitialBody =>
      'Есть ли сбережения, отложенные до приложения? Внесите их один раз — учёт будет полным.';

  @override
  String get vaultInitialAction => 'Внести';

  @override
  String get vaultInitialSaved => 'Начальные накопления записаны.';

  @override
  String get vaultProgressionTitle => 'Молодец!';

  @override
  String vaultProgressionBody(int weeks, String percent) {
    return 'Вы $weeks недели подряд платили себе. Увеличить долю до $percent %?';
  }

  @override
  String get vaultProgressionAccept => 'Увеличить';

  @override
  String get vaultProgressionDecline => 'Пока нет';

  @override
  String get ruleTitle => 'Настройка доли';

  @override
  String get rulePercent5 => '5 % — для начала';

  @override
  String get rulePercent10 => '10 % — цель (десятая часть дохода)';

  @override
  String get ruleFixed => 'Фиксированная сумма — в месяц';

  @override
  String ruleFixedAmount(String amount) {
    return 'Сумма в месяц: $amount';
  }

  @override
  String get ruleFixedChoose => 'Выберите сумму';

  @override
  String get ruleProgressive => 'Прогрессивный режим';

  @override
  String get ruleProgressiveHint =>
      'Если 4 недели подряд откладываете, предложим увеличить долю на 1 % (до 10 %).';

  @override
  String get ruleSave => 'Сохранить';

  @override
  String get ruleSaved => 'Доля обновлена.';

  @override
  String get withdrawTitle => 'Снять из «Моё будущее»';

  @override
  String get withdrawReminder =>
      'Эти деньги — для вас в будущем. Берите их только при настоящей необходимости.';

  @override
  String withdrawAvailable(String amount) {
    return 'Доступно: $amount';
  }

  @override
  String get withdrawAmountLabel => 'Сколько снять? (сум)';

  @override
  String get withdrawReasonLabel => 'Зачем? (обязательно)';

  @override
  String get withdrawReasonHint => 'Например: лечение, ремонт дома';

  @override
  String get withdrawContinue => 'Продолжить';

  @override
  String get withdrawPauseTitle => 'Давайте немного подумаем';

  @override
  String withdrawPauseBody(String amount) {
    return '$amount будет снято из вашего будущего. Это действительно необходимо?';
  }

  @override
  String withdrawPauseWait(int seconds) {
    return 'Да, сниму ($seconds)';
  }

  @override
  String get withdrawPauseConfirm => 'Да, сниму';

  @override
  String get withdrawPauseCancel => 'Передумал(а)';

  @override
  String withdrawDone(String amount) {
    return 'Снято $amount. Восполним, когда будет возможность.';
  }

  @override
  String get withdrawErrorAmount =>
      'Сумма не должна превышать доступный остаток.';

  @override
  String get pinConfirmTitle => 'Повторите PIN-код';

  @override
  String get cancel => 'Отмена';

  @override
  String get amountDialogTitle => 'Сумма';

  @override
  String get amountDialogDone => 'Готово';

  @override
  String get genericError => 'Что-то пошло не так. Попробуйте ещё раз.';

  @override
  String get homePaidToSelf => 'Заплачено себе (этот месяц)';

  @override
  String get homeVaultBalance => 'Моё будущее';

  @override
  String homeStreak(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count недель подряд',
      few: '$count недели подряд',
      one: '$count неделя подряд',
    );
    return '$_temp0';
  }

  @override
  String get homeMonthResult => 'Итог месяца';

  @override
  String get homeMonthResultPlus => 'Должно остаться на руках';

  @override
  String get homeMonthResultMinus => 'Расходов записано больше доходов';

  @override
  String get homeWeeklyTasks => 'Задачи этой недели';

  @override
  String get homeAddExpense => 'Расход';

  @override
  String homeAuditDue(String month) {
    return 'Месячный аудит за $month — «Куда ушли деньги?»';
  }

  @override
  String homeAuditDone(String month) {
    return 'Последний аудит: $month';
  }

  @override
  String get sectionExpenses => 'Расходы';

  @override
  String get sectionObligations => 'Обязательства';

  @override
  String get sectionNasiya => 'Тетрадь долгов (насия)';

  @override
  String get sectionWhoseMoney => 'Чьи это деньги?';

  @override
  String get sectionMembers => 'Члены семьи';

  @override
  String get sectionSettings => 'Настройки';

  @override
  String get catRent => 'Аренда';

  @override
  String get catCredit => 'Кредит';

  @override
  String get catGroceries => 'Продукты';

  @override
  String get catUtilities => 'Коммунальные';

  @override
  String get catPhone => 'Телефон';

  @override
  String get catFuel => 'Бензин';

  @override
  String get catTransport => 'Проезд';

  @override
  String get catDailySmall => 'Мелкие ежедневные расходы';

  @override
  String get catChildren => 'Ребёнок';

  @override
  String get catSadaqa => 'Садака';

  @override
  String get catOther => 'Другое';

  @override
  String get expenseNewTitle => 'Новый расход';

  @override
  String get expenseCategory => 'Категория';

  @override
  String get expenseSaved =>
      'Расход записан. Записывать каждый сум — начало хозяйского отношения к деньгам.';

  @override
  String get expensesTitle => 'Расходы этого месяца';

  @override
  String get expensesEmpty => 'В этом месяце расходов пока нет.';

  @override
  String expensesTotal(String amount) {
    return 'Итого: $amount';
  }

  @override
  String get memberLabel => 'Кто';

  @override
  String get delete => 'Удалить';

  @override
  String get save => 'Сохранить';

  @override
  String get obligationsEmpty =>
      'Добавьте регулярные платежи: аренда, кредит, коммунальные. Напомним за день до оплаты.';

  @override
  String get obligationAdd => 'Добавить обязательство';

  @override
  String get obligationEdit => 'Изменить обязательство';

  @override
  String get obligationTitleLabel => 'Название';

  @override
  String get obligationKindLabel => 'Тип';

  @override
  String get obligationDayLabel => 'Какого числа каждый месяц?';

  @override
  String obligationDay(int day) {
    return 'Каждый месяц $day-го';
  }

  @override
  String obligationsMonthly(String amount) {
    return 'Всего в месяц: $amount';
  }

  @override
  String get kindRent => 'Аренда';

  @override
  String get kindCredit => 'Кредит';

  @override
  String get kindUtility => 'Коммунальные';

  @override
  String get kindPhone => 'Телефон';

  @override
  String get kindFuel => 'Бензин';

  @override
  String get kindOther => 'Другое';

  @override
  String get reminderChannel => 'Напоминания о платежах';

  @override
  String reminderTitle(String title) {
    return 'Завтра платёж: $title';
  }

  @override
  String reminderBody(String title) {
    return 'Напоминание: завтра день оплаты «$title». Подготовьтесь заранее — будет спокойнее.';
  }

  @override
  String get notificationsOff =>
      'Уведомления выключены — напоминания не придут.';

  @override
  String get notificationsEnable => 'Включить';

  @override
  String get nasiyaEmpty =>
      'Записывайте сюда покупки в долг — будет видно, кому и сколько вы должны.';

  @override
  String get nasiyaAdd => 'Добавить долг';

  @override
  String get nasiyaShopLabel => 'Магазин или кому';

  @override
  String nasiyaTotal(String amount) {
    return 'Всего долгов: $amount';
  }

  @override
  String nasiyaRemaining(String amount) {
    return 'Остаток: $amount';
  }

  @override
  String nasiyaDue(String date) {
    return 'Срок: $date';
  }

  @override
  String get nasiyaPay => 'Оплата';

  @override
  String get nasiyaPaid => 'Закрыто — молодец!';

  @override
  String get nasiyaDueLabel => 'До какого числа (необязательно)';

  @override
  String get nasiyaAmountLabel => 'Сумма';

  @override
  String auditPeriod(String start, String end) {
    return 'Период: $start — $end';
  }

  @override
  String get auditStepIncome => 'Доход';

  @override
  String get auditStepObligations => 'Обязательства';

  @override
  String get auditStepExpenses => 'Расходы';

  @override
  String get auditStepResult => 'Итог';

  @override
  String get auditIncomeHint =>
      'Сколько было дохода в прошлом месяце? Добавьте незаписанное.';

  @override
  String get auditAddIncome => 'Добавить незаписанный доход';

  @override
  String get auditObligationsHint =>
      'Эти платежи считаются оплаченными. Записанная как расход часть не учитывается дважды.';

  @override
  String auditObligationLine(String title, String amount, String recorded) {
    return '$title: $amount (записано: $recorded)';
  }

  @override
  String get auditExpensesHint =>
      'Добавьте по каждой категории то, что помните.';

  @override
  String auditAddTo(String category) {
    return 'Добавить в «$category»';
  }

  @override
  String get auditIncome => 'Доход';

  @override
  String get auditObligations => 'Обязательства';

  @override
  String get auditExpenses => 'Записанные расходы';

  @override
  String get auditSavings => 'Накопления';

  @override
  String get auditUnexplained => 'Необъяснённая сумма';

  @override
  String get auditUnexplainedHint =>
      'Неизвестно, куда ушли эти деньги. Чаще всего это мелкие ежедневные траты — самса, напитки, покупки по пути.';

  @override
  String get auditNegativeHint =>
      'Расходов записано больше доходов. Возможно, часть дохода не внесена.';

  @override
  String get auditMarkSmall => 'Отметить как мелкие ежедневные расходы';

  @override
  String get auditDistribute => 'Распределить по категориям';

  @override
  String get auditFinish => 'Завершить аудит';

  @override
  String get auditFinished =>
      'Аудит завершён. Знать, куда уходят деньги, — начало управления ими.';

  @override
  String get next => 'Далее';

  @override
  String get back => 'Назад';

  @override
  String whoseIntro(String month) {
    return '$month: кому ушёл ваш доход';
  }

  @override
  String get whoseEmpty => 'За этот месяц пока нет данных.';

  @override
  String get ownerLandlord => 'Хозяину жилья';

  @override
  String get ownerBank => 'Банку';

  @override
  String get ownerShop => 'Магазину';

  @override
  String get ownerUtilities => 'Государству (коммунальные)';

  @override
  String get ownerFuel => 'На топливо';

  @override
  String get ownerSelf => 'Вам самим';

  @override
  String get ownerSadaqa => 'Садака';

  @override
  String get ownerOther => 'Прочее';

  @override
  String get ownerUnexplained => 'Без объяснения';

  @override
  String whosePercent(String percent) {
    return '$percent %';
  }

  @override
  String get memberOwnerDefault => 'Я';

  @override
  String get memberOwnerTag => 'владелец';

  @override
  String get memberChildTag => 'ребёнок';

  @override
  String get memberAdd => 'Добавить члена семьи';

  @override
  String get memberName => 'Имя';

  @override
  String get memberIsChild => 'Ребёнок';

  @override
  String get membersHint =>
      'Заполняйте бюджет вместе — «не пишите в одиночку». В каждой записи видно, кто её внёс.';

  @override
  String get settingsMonthStart => 'День зарплаты';

  @override
  String settingsMonthStartHint(int day) {
    return 'Месяц начинается с этого дня: $day-е число';
  }

  @override
  String get contentDisclaimer =>
      'Учебный материал. Не является фетвой или финансовой консультацией.';

  @override
  String get contentAdvisor => 'Советник';

  @override
  String get contentLoadError =>
      'Не удалось загрузить главы. Будет исправлено в следующем обновлении.';

  @override
  String chapterLocked(String date) {
    return 'Откроется $date';
  }

  @override
  String chapterLockedTasks(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Откроется, когда выполните ещё $count задач предыдущей главы',
      few: 'Откроется, когда выполните ещё $count задачи предыдущей главы',
      one: 'Откроется, когда выполните ещё $count задачу предыдущей главы',
    );
    return '$_temp0';
  }

  @override
  String get chapterOpen => 'Открыта';

  @override
  String lawLabel(int number) {
    return 'Закон $number';
  }

  @override
  String get daftarPageTitle => 'Страница тетради';

  @override
  String get daftarPageHint =>
      'Запишите закон своими словами. Записанное своей рукой запоминается.';

  @override
  String get daftarPageSaved => 'Записано в тетрадь.';

  @override
  String get daftarPageWritten => 'Записано';

  @override
  String get weeklyTasksTitle => 'Задачи этой недели';

  @override
  String weeklyTasksProgress(int done) {
    return 'Выполнено $done из 3';
  }

  @override
  String get taskAuto => 'отмечено приложением';

  @override
  String get religiousPending =>
      'На проверке у улемов — видно только в тестовом режиме';

  @override
  String religiousSource(String source) {
    return 'Источник: $source';
  }

  @override
  String get weeklyChannel => 'Глава недели';

  @override
  String get weeklyNotificationTitle => 'Сегодня пятница — итоги недели';

  @override
  String get weeklyNotificationBody =>
      'Возможно, открылась новая глава. Давайте вместе посмотрим задачи прошлой недели.';

  @override
  String get catSnacks => 'Напитки и перекусы';

  @override
  String get catCafe => 'Чайхана и кафе';

  @override
  String get necessityLabel => 'Категория';

  @override
  String get necessityZarur => 'Необходимо';

  @override
  String get necessityKerak => 'Нужно';

  @override
  String get necessityHavas => 'Хочется';

  @override
  String get necessityNone => 'Вне категорий';

  @override
  String get necessitySadaqaNote =>
      'Садака — не «хотелка» и не входит в «утечки».';

  @override
  String get expenseFlagsLabel => 'Отметки';

  @override
  String get flagGift => 'Подарок — не считается';

  @override
  String get flagOstentation => 'Ради престижа';

  @override
  String get flagDebt => 'На заёмные деньги';

  @override
  String get debtHavasFlag => '«Хотелка» в долг';

  @override
  String get habitLabel => 'Привычка';

  @override
  String get habitNone => 'Нет';

  @override
  String get quickTitle => 'Быстрая запись';

  @override
  String get quickEmpty =>
      'Сделайте шаблон для частых трат (самса, чай, бензин) — потом запись в одно касание.';

  @override
  String get repeatLast => 'Повторить последний';

  @override
  String repeatLastDone(String amount) {
    return 'Повторено: $amount';
  }

  @override
  String templateRecorded(String title, String amount) {
    return '$title записано — $amount';
  }

  @override
  String get undo => 'Отменить';

  @override
  String get templatesTitle => 'Шаблоны';

  @override
  String get templateAdd => 'Добавить шаблон';

  @override
  String get templateTitleLabel => 'Название (например, Самса)';

  @override
  String get templateFromForm => 'Сохранить и как шаблон';

  @override
  String get categoriesTitle => 'Категории и уровни нужды';

  @override
  String get categoriesHint =>
      'У каждой категории есть уровень по умолчанию. Изменение применяется к новым расходам; кто и когда изменил — сохраняется.';

  @override
  String get categoryHistory => 'История изменений';

  @override
  String get categoryHistoryEmpty => 'Ещё не менялось';

  @override
  String categoryHistoryItem(String date, String from, String to, String who) {
    return '$date · $from → $to · $who';
  }

  @override
  String get whoChanges => 'Кто меняет?';

  @override
  String get rollupTitle => 'Мелкие расходы в сумме';

  @override
  String get rollupWindow => 'Прогноз по последним 30 дням';

  @override
  String rollupLine(String week, String month, String year) {
    return 'в неделю $week · в месяц $month · в год $year';
  }

  @override
  String rollupShare(String obligation, String percent) {
    return 'В месяц — $percent% от «$obligation»';
  }

  @override
  String get havasTitle => '«Хотелки» и привычки';

  @override
  String get havasRule =>
      'Не убивай желание — поставь в очередь. Лимит действует, только когда согласны все взрослые; запретов нет.';

  @override
  String get havasNoLimit => 'Месячный лимит на «хотелки» ещё не согласован.';

  @override
  String havasSpent(String amount) {
    return '«Хотелки» в этом месяце: $amount';
  }

  @override
  String havasOfLimit(String spent, String limit) {
    return '$spent / $limit';
  }

  @override
  String havasOk(String amount) {
    return 'Осталось $amount';
  }

  @override
  String havasNear(String percent) {
    return 'Вы приближаетесь к лимиту ($percent%).';
  }

  @override
  String havasOver(String amount) {
    return 'Лимит превышен на $amount. Запретов нет — спланируйте следующий месяц вместе.';
  }

  @override
  String get havasPropose => 'Предложить лимит';

  @override
  String get havasProposeTitle => 'Месячный лимит на «хотелки»';

  @override
  String havasPending(String amount) {
    return 'Предложение: $amount — ждём согласия всех взрослых';
  }

  @override
  String get havasConsent => 'Согласиться';

  @override
  String get havasConsented => 'Согласен(а)';

  @override
  String get havasAgreed => 'Лимит согласован и действует.';

  @override
  String havasConsentSaved(String name) {
    return '$name: согласие получено';
  }

  @override
  String get havasWithdraw => 'Отозвать предложение';

  @override
  String memberPinPrompt(String name) {
    return '$name, ваш личный PIN';
  }

  @override
  String get analysisTitle => 'Расточительство и щедрость (этот месяц)';

  @override
  String get analysisOstentation => 'Траты ради престижа';

  @override
  String get analysisDebtHavas => '«Хотелки» в долг';

  @override
  String get analysisSadaqa => 'Садака — не расточительство';

  @override
  String get analysisGifts => 'Подарки — не учтены';

  @override
  String get treatsTitle => 'Пятничная сладость';

  @override
  String get treatsHint =>
      'Превратите ежедневную мелкую «хотелку» в еженедельную семейную радость.';

  @override
  String get treatAdd => 'Добавить ритуал';

  @override
  String get treatTitleDefault => 'Пятничная сладость';

  @override
  String treatLine(String weekday, String amount) {
    return '$weekday · $amount';
  }

  @override
  String get treatChannel => 'День сладости';

  @override
  String treatNotifTitle(String title) {
    return 'Сегодня — $title';
  }

  @override
  String get treatNotifBody =>
      'Запланированный день радости. Разделите его с семьёй!';

  @override
  String get titleLabel => 'Название';

  @override
  String get habitsTitle => 'Привычки';

  @override
  String get habitsHint =>
      'Только статистика: вы просто видите, сколько уходит.';

  @override
  String get habitAdd => 'Добавить привычку';

  @override
  String habitLine(String month, String year) {
    return 'в месяц $month · в год $year';
  }

  @override
  String get habitArchive => 'Перестать отслеживать';

  @override
  String get widgetTitle => 'Быстрая запись';

  @override
  String get widgetLocked => 'Суммы видны, пока приложение открыто';

  @override
  String get widgetEmpty => 'Добавьте шаблон в приложении';

  @override
  String widgetRecorded(int count) {
    return 'Записано с виджета: $count';
  }

  @override
  String get vaultReasonRescue => 'Спасённые деньги';

  @override
  String get subscriptionsTitle => 'Подписки и автоплатежи';

  @override
  String get subscriptionsHint =>
      'Посмотрите, сколько каждая стоит в год, и спросите себя: нужна ли?';

  @override
  String get subscriptionsEmpty =>
      'Подписок пока нет. Добавьте тариф, кино, музыку, приложения.';

  @override
  String get subscriptionAdd => 'Добавить подписку';

  @override
  String get cycleMonthly => 'Ежемесячно';

  @override
  String get cycleYearly => 'Ежегодно';

  @override
  String subscriptionLine(String price, String yearly) {
    return '$price · в год $yearly';
  }

  @override
  String subscriptionLastUsed(String date) {
    return 'Последний раз: $date';
  }

  @override
  String subscriptionForgotten(int days) {
    String _temp0 = intl.Intl.pluralLogic(
      days,
      locale: localeName,
      other: '$days дней',
      few: '$days дня',
      one: '$days день',
    );
    return '$_temp0 без отметки «пользовался» — нужна ли?';
  }

  @override
  String get subscriptionUsed => 'Пользовался';

  @override
  String get subscriptionCancel => 'Отменил';

  @override
  String subscriptionCancelConfirm(String title, String yearly) {
    return '«$title» отменена? Спасено $yearly в год.';
  }

  @override
  String subscriptionCancelledLine(String yearly) {
    return 'Отменена · экономия $yearly в год';
  }

  @override
  String get subscriptionsCancelledHeader => 'Отменённые';

  @override
  String subscriptionsAnnualTotal(String amount) {
    return 'Активные подписки в год: $amount';
  }

  @override
  String get subscriptionUsedSaved => 'Отмечено';

  @override
  String get envelopesTitle => 'Конверты';

  @override
  String get envelopesHint =>
      'Недельный конверт: положите наличные в конверт. Траты картой тоже вычитаются из конверта.';

  @override
  String get envelopesEmpty =>
      'Конвертов нет. Откройте недельный конверт: «Базар», «Проезд», «Хотелки».';

  @override
  String get envelopeAdd => 'Открыть конверт';

  @override
  String get envelopeCashMode => 'Наличный конверт';

  @override
  String get envelopeCategories => 'Какие расходы из этого конверта?';

  @override
  String get envelopeLimitTitle => 'Недельный лимит';

  @override
  String envelopeLine(String spent, String limit, String left) {
    return '$spent / $limit · осталось $left';
  }

  @override
  String envelopePutCash(String amount) {
    return 'На этой неделе положите в конверт $amount';
  }

  @override
  String envelopeOver(String amount) {
    return 'Конверт превышен на $amount';
  }

  @override
  String envelopeCloseTitle(String title, String week) {
    return '«$title»: итог прошлой недели ($week)';
  }

  @override
  String get envelopeClosePrompt => 'Сколько наличных осталось в конверте?';

  @override
  String get envelopeCloseAction => 'Ввести остаток';

  @override
  String envelopeClosed(String amount) {
    return 'Остаток $amount — добавлен в «Спасённые деньги»';
  }

  @override
  String get rescueTitle => 'Спасённые деньги';

  @override
  String get rescueThisWeek => 'Спасено на этой неделе';

  @override
  String get rescueThisMonth => 'Спасено в этом месяце';

  @override
  String get rescueQuestion => 'Сколько вы спасли на этой неделе?';

  @override
  String get rescueHavas => 'Меньше «хотелок» (к базовому месяцу)';

  @override
  String get rescueSubscriptions => 'Отменённые подписки';

  @override
  String get rescueEnvelopes => 'Остатки конвертов';

  @override
  String get rescueTransferredLine => 'Переведено в «Будущее»';

  @override
  String get rescueNoBaseline =>
      'Нет базового месяца для сравнения — появится после первого аудита.';

  @override
  String rescueBaseline(String month) {
    return 'Базовый месяц: $month';
  }

  @override
  String get rescueBaselinePick => 'Выбрать базовый месяц';

  @override
  String get rescueSpentMore =>
      'В этот период на «хотелки» ушло больше, чем в базовом месяце. Ничего — каждая неделя даёт новый шанс.';

  @override
  String rescueTransfer(String amount) {
    return 'Перевести в «Будущее» — $amount';
  }

  @override
  String rescueTransferDone(String amount) {
    return '$amount переведено в «Будущее»';
  }

  @override
  String get rescueFormula =>
      'Спасено = снижение «хотелок» + отменённые подписки + остатки конвертов. Если потрачено больше — 0.';

  @override
  String get notNow => 'Пока нет';

  @override
  String get reserveTitle => 'Резерв на чёрный день';

  @override
  String get reserveHint =>
      'Чтобы в чёрный день не бежать за долгом. Никуда не тратится и не оценивается как «не выросли».';

  @override
  String reserveMonths(String months) {
    return '$months / 6 мес.';
  }

  @override
  String reserveTarget(String target, String monthly) {
    return 'Цель: $target (необходимое + нужное $monthly × 6)';
  }

  @override
  String get reserveFromEstimate => 'По вашей оценке';

  @override
  String get reserveMilestone3 => 'Первый этап — 3 месяца выполнен';

  @override
  String get reserveFull => 'Полный резерв — 6 месяцев. Отлично!';

  @override
  String get reserveNeedsEstimate =>
      'Для расчёта цели не хватает данных за 3 месяца. Сколько примерно в месяц уходит на необходимое и нужное?';

  @override
  String get reserveEstimateAction => 'Ввести оценку';

  @override
  String get reserveEstimateTitle => 'Необходимое + нужное в месяц (примерно)';

  @override
  String get growthTitle => 'Растущие деньги';

  @override
  String get growthHint =>
      'Чтобы опережать инфляцию — только в халяльных (без рибы) направлениях.';

  @override
  String get growthDeposit => 'Внести капитал';

  @override
  String get growthDepositTitle => 'В растущие деньги';

  @override
  String get gateTitle => 'Сначала подготовка, потом вложения';

  @override
  String get gateHint =>
      'Растущие деньги и партнёрство открываются при двух условиях. Это не запрет, а объяснение.';

  @override
  String gateReserve(String months) {
    return 'Резерв на чёрный день — 6 месяцев ($months / 6)';
  }

  @override
  String get gateDebt => 'Нет процентного долга или есть план выхода из долга';

  @override
  String get gateOpen => 'Ворота открыты';

  @override
  String get gateBypass => 'Всё равно внести';

  @override
  String get gateBypassTitle => 'Осознанное решение';

  @override
  String get gateBypassWarning =>
      'Резерв ещё не полный. В чёрный день деньги из растущей части могут не вернуться быстро, и придётся брать в долг. Всё равно продолжить?';

  @override
  String get gateBypassConfirm => 'Да, понимаю';

  @override
  String get gateBypassed => 'Ворота осознанно обойдены';

  @override
  String get withdrawFrom => 'Откуда?';

  @override
  String get withdrawEmergency => 'Это действительно чрезвычайная ситуация';

  @override
  String get withdrawEmergencyHint => 'Резерв — только на чёрный день.';

  @override
  String get refillTitle => 'План восполнения';

  @override
  String refillPlan(String monthly, int months) {
    return 'По $monthly в месяц — резерв восстановится за $months мес.';
  }

  @override
  String get ok => 'Понятно';

  @override
  String get pricesTitle => 'Тетрадь цен';

  @override
  String get pricesHint =>
      'Кто годами записывает цены, точно видит, как они меняются. Записывайте цены важных для вас товаров — увидите свою личную инфляцию.';

  @override
  String get pricesEmpty => 'Корзина пуста. Добавьте мясо, хлеб, муку, бензин…';

  @override
  String get priceItemAdd => 'Добавить товар';

  @override
  String get priceUnitLabel => 'Единица (кг, шт., л)';

  @override
  String get priceQuantityLabel => 'Сколько в месяц (например, 4 или 1,5)';

  @override
  String get priceAdd => 'Записать цену';

  @override
  String priceAddTitle(String name, String unit) {
    return '$name — цена сегодня (1 $unit)';
  }

  @override
  String get priceSaved => 'Цена записана';

  @override
  String priceLast(String price, String date) {
    return '$price · $date';
  }

  @override
  String priceChange(String fromDate, String from, String to, String change) {
    return '$fromDate: $from → сегодня $to ($change)';
  }

  @override
  String inflationYear(String change) {
    return 'Личная инфляция (1 год): $change';
  }

  @override
  String inflationSince(String date, String change) {
    return 'С $date: $change';
  }

  @override
  String get inflationUnknown =>
      'Для индекса нужны цены одного товара в разное время.';

  @override
  String priceStreak(int weeks) {
    String _temp0 = intl.Intl.pluralLogic(
      weeks,
      locale: localeName,
      other: '$weeks недель',
      few: '$weeks недели',
      one: '$weeks неделя',
    );
    return '$_temp0 подряд с записью цен';
  }

  @override
  String get priceReminderTitle => 'Тетрадь цен';

  @override
  String get priceReminderBody =>
      'Запишите цены на этой неделе — будете знать свою инфляцию.';

  @override
  String get mouseTitle => 'Влияние инфляции';

  @override
  String get mouseHint =>
      'Рост цен незаметно уменьшает ценность лежащих денег. Это не страшилка, а объяснение.';

  @override
  String get mouseNoPrices =>
      'Для расчёта запишите хотя бы одну цену в «Тетрадь цен».';

  @override
  String mouseBalance(String amount) {
    return 'Ваш резерв: $amount';
  }

  @override
  String mouseToday(String qty, String unit, String name) {
    return 'По сегодняшней цене: $qty $unit — $name';
  }

  @override
  String mouseYearAgo(String qty, String unit) {
    return 'По цене год назад было бы: $qty $unit';
  }

  @override
  String mouseFuture(String rate, int years, String qty, String unit) {
    return 'Если цены растут на $rate в год, через $years г.: $qty $unit';
  }

  @override
  String get mouseNextReserve =>
      'Следующий шаг: доведите резерв до 6 месяцев — даже лёжа, он спасает от долгов в чёрный день.';

  @override
  String get mouseNextGrowth =>
      'Следующий шаг: резерв полный. Направьте излишек в растущую часть — честную торговлю и партнёрство.';

  @override
  String get mouseOpenVault => 'Перейти в «Будущее»';

  @override
  String get incomeSourceTypeLabel => 'Откуда прибыль? (необязательно)';

  @override
  String get incomeTypeTer => 'Труд';

  @override
  String get incomeTypeMol => 'Товар — торговля';

  @override
  String get incomeTypeTavakkal => 'Риск — партнёрство';

  @override
  String get incomeTypeRibo => 'Проценты (риба)';

  @override
  String get incomeRiboNote =>
      'Если нет ни труда, ни товара, ни риска — это риба. Такой доход показывается отдельно.';

  @override
  String auditRiboIncome(String amount) {
    return 'Процентный доход (отдельно): $amount';
  }

  @override
  String get debtsTitle => 'Долги';

  @override
  String get debtsHint =>
      'Долг — не дыра, а рана. Ни один долг не забыт: банк, магазин, родня, друзья.';

  @override
  String debtsTotal(String amount) {
    return 'Всего долгов: $amount';
  }

  @override
  String debtsLoad(String payments, String percent) {
    return 'Ежемесячная нагрузка: $payments — $percent% дохода';
  }

  @override
  String debtsLoadUnknown(String payments) {
    return 'Ежемесячная нагрузка: $payments (доход ещё не записан)';
  }

  @override
  String get debtsEmpty => 'Долгов нет. Альхамдулиллах!';

  @override
  String get debtsBorrowed => 'Мои долги';

  @override
  String get debtsLent => 'Мне должны';

  @override
  String debtsLentTotal(String amount) {
    return 'Мне должны вернуть: $amount';
  }

  @override
  String get debtsGoals => 'Наши цели';

  @override
  String get debtAdd => 'Добавить долг';

  @override
  String get debtLend => 'Я дал в долг';

  @override
  String get goalAdd => 'Добавить цель';

  @override
  String get goalTargetTitle => 'Сумма цели';

  @override
  String get creditorBank => 'Банк';

  @override
  String get creditorShop => 'Магазин (насия)';

  @override
  String get creditorRelative => 'Родственник';

  @override
  String get creditorFriend => 'Друг';

  @override
  String get creditorOther => 'Другое';

  @override
  String get debtInterestFlag => 'С процентами (риба)';

  @override
  String debtNext(String amount, String date) {
    return 'Следующий: $amount · $date';
  }

  @override
  String debtRemaining(String amount) {
    return 'Осталось: $amount';
  }

  @override
  String get checkTitle => 'Остановись и подумай';

  @override
  String get checkHint =>
      'Это не запрет — три вопроса для осознанного решения.';

  @override
  String get checkNecessity => 'Это необходимость или роскошь?';

  @override
  String get checkNeed => 'Необходимость';

  @override
  String get checkLuxury => 'Роскошь';

  @override
  String get checkAlternative => 'Есть ли беспроцентная альтернатива?';

  @override
  String get altReserve => 'Резерв на чёрный день';

  @override
  String get altRelative => 'Без процентов у родни';

  @override
  String get altSell => 'Продать вещь';

  @override
  String get altNone => 'Нет';

  @override
  String checkLoad(String percent) {
    return 'С этим долгом нагрузка составит $percent% дохода';
  }

  @override
  String get debtCreditorLabel => 'У кого?';

  @override
  String get debtCreditorName => 'Имя или название';

  @override
  String get debtAmountLabel => 'Основная сумма';

  @override
  String get debtReasonLabel => 'Причина (свадьба, машина, быт…)';

  @override
  String get debtScheduleLabel => 'График платежей';

  @override
  String get scheduleManual => 'Сам(а) задам';

  @override
  String get scheduleAnnuity => 'Аннуитет (банк)';

  @override
  String get scheduleDifferentiated => 'Дифференцированный (банк)';

  @override
  String get scheduleFixedMarkup => 'Фиксированная наценка';

  @override
  String get debtTermLabel => 'Срок (мес.)';

  @override
  String get debtRateLabel => 'Годовая ставка, %';

  @override
  String get debtMarkupLabel => 'Сумма наценки';

  @override
  String get debtEarlyTerms => 'Условия досрочного погашения (штраф, комиссия)';

  @override
  String get debtRibaWarning =>
      'В этом долге есть проценты или наценка — это риба. Постарайтесь найти беспроцентную альтернативу. Расчёт приблизительный.';

  @override
  String get manualRowAdd => 'Добавить строку';

  @override
  String get manualRowAmount => 'Сумма платежа';

  @override
  String planMustCover(String planned, String principal) {
    return 'Сумма графика должна равняться основной сумме: $planned / $principal';
  }

  @override
  String get scheduleRequired =>
      'Намерение вернуть — без графика долг не сохранить.';

  @override
  String get costTitle => 'Настоящая цена долга';

  @override
  String get costPrincipal => 'Основная сумма';

  @override
  String get costTotal => 'Всего будет выплачено';

  @override
  String get costOver => 'Переплата';

  @override
  String costOpportunity(String goal, String percent) {
    return 'Эта переплата — $percent% цели «$goal»';
  }

  @override
  String get debtSaveAction => 'Сохранить долг';

  @override
  String get debtPay => 'Я заплатил';

  @override
  String get debtPayTitle => 'Сумма платежа';

  @override
  String get debtPrepayment => 'Досрочный (дополнительный) платёж';

  @override
  String get debtPaymentsHeader => 'История платежей';

  @override
  String get debtPlanPaid => 'оплачено';

  @override
  String get debtReceipt => 'Долговая расписка';

  @override
  String get receiptHint =>
      'Вторая сторона и свидетели пишут имя и расписываются на этом телефоне. Это запись для личного учёта, не юридическая гарантия.';

  @override
  String get roleLender => 'Займодавец';

  @override
  String get roleBorrower => 'Заёмщик';

  @override
  String get roleWitness => 'Свидетель';

  @override
  String get witnessAdd => 'Добавить свидетеля';

  @override
  String get signAction => 'Подписать';

  @override
  String get signed => 'Подписано';

  @override
  String signTitle(String role) {
    return '$role: имя и подпись';
  }

  @override
  String get signHere => 'Распишитесь здесь пальцем';

  @override
  String get signClear => 'Очистить';

  @override
  String get receiptShare => 'Создать PDF и поделиться';

  @override
  String get receiptPdfTitle => 'Долговая расписка';

  @override
  String get receiptPdfParties => 'Стороны и условия';

  @override
  String get receiptPdfAmount => 'Сумма';

  @override
  String get receiptPdfDate => 'Дата';

  @override
  String get receiptPdfReason => 'Причина';

  @override
  String get receiptPdfMarkup => 'Проценты / наценка';

  @override
  String get receiptPdfNoMarkup => 'Нет — беспроцентный заём (кард хасан)';

  @override
  String get receiptPdfPayment => 'Платёж';

  @override
  String get receiptPdfSignatures => 'Подписи';

  @override
  String get receiptPdfNote =>
      'Этот документ — запись для личного учёта, не юридическая гарантия.';

  @override
  String get lendTitle => 'Я дал в долг (без процентов)';

  @override
  String get lendHint => 'В данном долге процентов не бывает.';

  @override
  String get lendDebtor => 'Кому?';

  @override
  String lendDue(String date) {
    return 'Вернуть до: $date';
  }

  @override
  String get lendReceive => 'Вернул(а)';

  @override
  String get dueTitle => 'Скоро срок';

  @override
  String dueReceivable(String name, String amount, String date) {
    return '$name — $amount, срок $date. Можно вежливо напомнить.';
  }

  @override
  String dueDebt(String name, String amount, String date) {
    return 'Платёж $name: $amount · $date';
  }

  @override
  String get recoveryTitle => 'Режим выхода из долгов';

  @override
  String get recoveryOfferBody =>
      'Делите доход 70 / 20 / 10: хозяйство, ускоренное погашение долга и всё равно «Моё будущее». Из долга выходят по плану.';

  @override
  String get recoveryEnable => 'Включить режим';

  @override
  String recoveryActive(String needs, String debt, String savings) {
    return 'Включён: хозяйство $needs % · долг $debt % · «Моё будущее» $savings %';
  }

  @override
  String get recoverySettings => 'Настроить';

  @override
  String get recoveryExplain =>
      'Долг — плата прошлому, сбережения — плата будущему. Без сбережений при первой беде снова приходится занимать.';

  @override
  String get recoveryNeeds =>
      'Хозяйство, % (обязательные платежи по долгам внутри)';

  @override
  String get recoveryDebt => 'Ускоренное погашение, %';

  @override
  String get recoverySavings => '«Моё будущее», %';

  @override
  String get recoverySavingsZero =>
      'Доля сбережений не может быть 0 — минимум 1 %.';

  @override
  String recoveryTotalError(int total) {
    return 'В сумме должно быть 100 % (сейчас $total %).';
  }

  @override
  String recoveryBudgetTitle(String income) {
    return 'Распределение в месяц (средний доход $income)';
  }

  @override
  String recoveryBudgetNeeds(String amount) {
    return 'Хозяйство: $amount';
  }

  @override
  String recoveryBudgetMandatory(String amount) {
    return 'из них обязательные платежи по долгам: $amount';
  }

  @override
  String recoveryBudgetHousehold(String amount) {
    return 'остаётся на хозяйство: $amount';
  }

  @override
  String recoveryBudgetDebt(String amount) {
    return 'Дополнительный платёж по долгу: $amount';
  }

  @override
  String recoveryBudgetSavings(String amount) {
    return '«Моё будущее»: $amount';
  }

  @override
  String get recoveryMandatoryOver =>
      'Обязательные платежи превышают долю хозяйства — пересмотрите доли.';

  @override
  String get recoveryNoIncome =>
      'Доход ещё не записан — суммы появятся после ввода дохода.';

  @override
  String get recoverySaveEnable => 'Сохранить и включить';

  @override
  String get recoveryDisable => 'Выйти из режима';

  @override
  String get recoveryStandard => 'Стандарт 70 / 20 / 10';

  @override
  String get freedShareTitle => 'Альхамдулиллях, без долгов!';

  @override
  String freedShareBody(String percent) {
    return 'Все долги закрыты — режим вернулся в обычный. Направить освободившиеся $percent % в резерв и растущие деньги?';
  }

  @override
  String get freedShareAccept => 'Да, в «Моё будущее»';

  @override
  String get payoffTitle => 'План выхода из долгов';

  @override
  String get payoffEstimate =>
      'Расчёт приблизительный: график банка, штрафы и комиссии зависят от договора.';

  @override
  String payoffMonthly(String amount) {
    return 'Каждый месяц дополнительно: $amount';
  }

  @override
  String payoffLump(String amount) {
    return 'Единоразово: $amount';
  }

  @override
  String get payoffMonthlyTitle => 'Ежемесячный доп. платёж';

  @override
  String get payoffLumpTitle => 'Единоразовый доп. платёж';

  @override
  String get payoffSources => 'Источники доп. платежей';

  @override
  String payoffSourceShare(String percent, String amount) {
    return 'Доля ($percent %): $amount в месяц';
  }

  @override
  String get payoffSourceShareOff => 'Доля: 20 % дохода при включённом режиме';

  @override
  String payoffSourceRescue(String amount) {
    return 'Спасённые деньги (неделя): $amount';
  }

  @override
  String payoffSourceSold(String amount) {
    return 'Проданные вещи: $amount';
  }

  @override
  String get payoffApply => 'В долг';

  @override
  String payoffApplied(String amount, String name) {
    return '$amount внесено досрочно в долг «$name».';
  }

  @override
  String get payoffOrder => 'Порядок погашения';

  @override
  String get payoffOrderHint =>
      'Сначала процентные (самый дорогой), затем беспроцентные — ближайший срок. Порядок можно менять.';

  @override
  String get payoffOrderReset => 'Стандартный порядок';

  @override
  String get payoffUp => 'Выше';

  @override
  String get payoffDown => 'Ниже';

  @override
  String payoffDebtFree(String base, String plan) {
    return 'День без долгов: $base → $plan';
  }

  @override
  String payoffEarly(int months) {
    return 'на $months мес. раньше';
  }

  @override
  String payoffSaved(String amount) {
    return 'экономия $amount';
  }

  @override
  String get payoffSameEnd => 'Срок не меняется';

  @override
  String payoffFees(String amount) {
    return 'Штраф / комиссия: $amount';
  }

  @override
  String get payoffBaseline => 'Обычный';

  @override
  String get payoffAccelerated => 'С доплатой';

  @override
  String get payoffShowTable => 'Показать графики';

  @override
  String payoffMonths(int months) {
    return '$months мес.';
  }

  @override
  String get payoffFeeLabel => 'Штраф за досрочное погашение, %';

  @override
  String payoffFeeValue(String percent) {
    return 'Штраф: $percent %';
  }

  @override
  String get payoffNoFee => 'Без штрафа';

  @override
  String debtFreeOn(String date) {
    return 'День без долгов: $date';
  }

  @override
  String get contributorsTitle => 'Помощники';

  @override
  String get contributorsHint =>
      'Погашаем вместе с семьёй: записывайте, кто сколько платит.';

  @override
  String get contributorAdd => 'Добавить помощника';

  @override
  String get contributorShareTitle => 'Ежемесячная доля (необязательно)';

  @override
  String contributorLine(String share, String paid) {
    return '$share в месяц · внёс $paid';
  }

  @override
  String contributorPaid(String paid) {
    return 'Внёс: $paid';
  }

  @override
  String get whoPaid => 'Кто заплатил?';

  @override
  String get whoPaidFamily => 'Сама семья';

  @override
  String debtFeeNote(String amount) {
    return 'штраф $amount';
  }

  @override
  String get debtClosedTitle => 'Альхамдулиллях! Долг закрыт';

  @override
  String debtClosedBody(String name) {
    return 'Долг «$name» полностью погашен. Одним обязательством меньше.';
  }

  @override
  String debtClosedFreed(String amount) {
    return 'Теперь каждый месяц освобождается $amount. Направить в «Моё будущее»?';
  }

  @override
  String get debtClosedRedirected => 'Доля «Моего будущего» увеличена.';

  @override
  String get debtClosedNoIncome =>
      'Доход не записан, поэтому доля не увеличена автоматически — увеличьте её в настройках «Моего будущего».';

  @override
  String get debtClosedDone => 'Спасибо';

  @override
  String get modeReturned =>
      'Все долги закрыты — режим выхода из долгов завершён.';

  @override
  String get sellablesTitle => 'Вещи на продажу';

  @override
  String get sellablesHint =>
      'Ценные вещи, которыми не пользовались больше 6 месяцев. Деньги от продажи одним нажатием идут в долг.';

  @override
  String get sellableAdd => 'Добавить вещь';

  @override
  String get sellableName => 'Название вещи';

  @override
  String get sellableEstimate => 'Примерная цена';

  @override
  String sellableListed(String amount) {
    return 'В продаже · примерно $amount';
  }

  @override
  String sellableSold(String amount) {
    return 'Продано: $amount';
  }

  @override
  String sellableAppliedTo(String amount, String name) {
    return 'Продано: $amount · в долг «$name»';
  }

  @override
  String get sellableMarkSold => 'Продано';

  @override
  String get sellableSoldPrice => 'Цена продажи';

  @override
  String get sellableChooseDebt => 'В какой долг?';

  @override
  String get sellablesEmpty => 'Пока нет вещей.';

  @override
  String homeDebtFree(String date) {
    return 'День без долгов: $date';
  }

  @override
  String homeDebtFreeBody(String amount, int months) {
    return 'Осталось: $amount · $months мес.';
  }

  @override
  String homeDebtFreePlan(String date) {
    return 'По плану: $date';
  }

  @override
  String get homeRecoveryOffer =>
      'Включите режим выхода из долгов — 70 / 20 / 10';

  @override
  String get ceremoniesTitle => 'Торжества';

  @override
  String get ceremoniesHint =>
      'Планируйте свадьбу и торжества заранее и без долгов: сравнивайте сценарии, советуйтесь с семьёй.';

  @override
  String get ceremoniesEmpty => 'Планов пока нет.';

  @override
  String get ceremonyAdd => 'Составить план';

  @override
  String get ceremonyNameLabel => 'Название (например, свадьба сына)';

  @override
  String get ceremonyTypeTitle => 'Вид торжества';

  @override
  String get ceremonyTypeToy => 'Свадьба';

  @override
  String get ceremonyTypeBeshik => 'Бешик-той';

  @override
  String get ceremonyTypeSunnat => 'Суннат-той';

  @override
  String get ceremonyTypeMaraka => 'Поминки (маърака)';

  @override
  String get ceremonyTypeOther => 'Другое';

  @override
  String get ceremonyStatusDraft => 'Черновик';

  @override
  String get ceremonyStatusDiscussed => 'Обсуждено в семье';

  @override
  String get ceremonyStatusConfirmed => 'Утверждено';

  @override
  String get ceremonyFirstScenario => 'Основной';

  @override
  String ceremonyDate(String date) {
    return 'Дата: $date';
  }

  @override
  String get ceremonyDateNone => 'Дата не выбрана';

  @override
  String ceremonyGuests(int count) {
    return '$count чел.';
  }

  @override
  String get ceremonyGuestsTitle => 'Число гостей';

  @override
  String get scenarioAdd => 'Добавить сценарий';

  @override
  String get scenarioName => 'Название сценария (например, 1 день, 100 гостей)';

  @override
  String get scenarioCompare => 'Сравнение сценариев';

  @override
  String get scenarioSelect => 'Выбрать';

  @override
  String get scenarioSelected => 'Выбран';

  @override
  String get scenarioRemove => 'Удалить';

  @override
  String scenarioTotal(String amount) {
    return 'Итого: $amount';
  }

  @override
  String scenarioDebt(String amount) {
    return 'Долг: $amount';
  }

  @override
  String get scenarioNoDebt => 'Без долга';

  @override
  String scenarioPayoff(int months, String date) {
    return 'Долг погашается за $months мес. (до $date)';
  }

  @override
  String scenarioPayoffInterest(String amount) {
    return 'переплата $amount';
  }

  @override
  String get scenarioPayoffNever =>
      'С таким платежом долг никогда не закончится';

  @override
  String get scenarioPayoffUnknown =>
      'Чтобы рассчитать срок, укажите ежемесячный платёж';

  @override
  String scenarioGoal(String goal, String percent) {
    return 'Эти деньги: «$goal» — $percent %';
  }

  @override
  String get lineAdd => 'Добавить строку';

  @override
  String get lineTitle => 'Название (плов, певец, сарпо…)';

  @override
  String get lineOneTime => 'Разово';

  @override
  String get linePerGuest => 'На гостя';

  @override
  String linePerGuestValue(String price, int guests, String total) {
    return '$price × $guests = $total';
  }

  @override
  String get lineAmountTitle => 'Сумма';

  @override
  String get linePriceTitle => 'Цена на гостя';

  @override
  String get lineSourceTitle => 'Источник средств';

  @override
  String get fundingSavings => 'Сбережения';

  @override
  String get fundingFamily => 'Вклад семьи';

  @override
  String get fundingGifts => 'Ожидаемые подарки';

  @override
  String get fundingDebt => 'Долг';

  @override
  String ceremonyDebtTerms(String amount) {
    return 'Долг в месяц: $amount';
  }

  @override
  String get ceremonyDebtTermsUnset => 'Сколько сможете платить в месяц?';

  @override
  String get ceremonyDebtMonthlyTitle => 'Ежемесячный платёж по долгу';

  @override
  String get discussionTitle => 'Как провести это без долгов?';

  @override
  String get discussionHint =>
      'В плане есть долг. Перед утверждением семья обсуждает эти вопросы, и каждый взрослый ставит отметку.';

  @override
  String get discussionQ1 => 'Можно ли сократить число гостей?';

  @override
  String get discussionQ2 => 'Не хватит ли одного скромного дня?';

  @override
  String get discussionQ3 =>
      'Что можно покрыть из сбережений или вклада семьи?';

  @override
  String get discussionQ4 => 'Кто, когда и как будет возвращать долг?';

  @override
  String get discussionQ5 => 'Что эти деньги могли бы дать молодой семье?';

  @override
  String get discussionMark => 'Обсудил(а)';

  @override
  String get discussionMarked => 'Отмечено';

  @override
  String get discussionDone => 'Семья обсудила — теперь можно утвердить.';

  @override
  String discussionMarkedSnack(String name) {
    return '$name отметил(а).';
  }

  @override
  String get ceremonyConfirm => 'Утвердить план';

  @override
  String get ceremonyConfirmedSnack => 'План утверждён.';

  @override
  String get ceremonyConfirmBlocked =>
      'В плане есть долг — сначала семейное обсуждение.';

  @override
  String get ceremonyReopen => 'Открыть снова';

  @override
  String get ceremonyLocked =>
      'План утверждён. Чтобы изменить, откройте снова.';

  @override
  String get giftTitle => 'Копилка вместо подарков';

  @override
  String get giftHint =>
      'Цель для молодой семьи: гости вкладываются в неё вместо пышности. Вклады записываются вручную.';

  @override
  String get giftCreate => 'Открыть цель';

  @override
  String get giftGoalName => 'Название цели (например, жильё для молодых)';

  @override
  String get giftTargetTitle => 'Сумма цели';

  @override
  String giftProgress(String collected, String target) {
    return 'Собрано: $collected / $target';
  }

  @override
  String get giftAddContribution => 'Записать вклад';

  @override
  String get giftContributorName => 'Кто внёс?';

  @override
  String get giftShare => 'Поделиться';

  @override
  String giftShareText(
    String title,
    String goal,
    String target,
    String collected,
  ) {
    return '$title: вместо подарка поддержите цель молодой семьи «$goal». Цель: $target, собрано: $collected.';
  }

  @override
  String get pressure1 =>
      'Люди поговорят три дня, а на четвёртый займутся своими заботами.';

  @override
  String get pressure2 =>
      'Лучший подарок молодой семье — жизнь, начатая без долгов.';

  @override
  String get pressure3 =>
      'Годами платить за один день пышности — тяжёлая ноша, взятая на себя добровольно.';

  @override
  String get roleParty => 'Партнёр';

  @override
  String get pnTitle => 'Партнёрство';

  @override
  String get pnHint =>
      'У одного деньги лежат без дела, у другого ремесло простаивает без денег. Партнёрство — не милостыня и не долг: риск делится.';

  @override
  String get pnEmpty => 'Партнёрств пока нет.';

  @override
  String get pnNew => 'Составить договор';

  @override
  String get pnTypeMudaraba => 'Мудараба';

  @override
  String get pnTypeMusharaka => 'Мушарака';

  @override
  String get pnTypeMudarabaHint =>
      'Капитал от одной стороны, труд — от другой. Финансовый убыток несёт владелец капитала, работник теряет свой труд.';

  @override
  String get pnTypeMusharakaHint =>
      'Обе стороны вносят капитал. Убыток делится пропорционально капиталу.';

  @override
  String get pnStatusDraft => 'Не подписан';

  @override
  String get pnStatusSigned => 'Подписан';

  @override
  String get pnStatusActive => 'Действует';

  @override
  String get pnStatusClosed => 'Закрыт';

  @override
  String get pnRoleProvider => 'Владелец капитала';

  @override
  String get pnRoleWorker => 'Работник';

  @override
  String get pnRoleBoth => 'Капитал и труд';

  @override
  String get pnPeriodMonthly => 'Ежемесячно';

  @override
  String get pnPeriodQuarterly => 'Ежеквартально';

  @override
  String get pnPeriodYearly => 'Ежегодно';

  @override
  String get pnCapitalCash => 'Деньги';

  @override
  String get pnCapitalEquipment => 'Оборудование';

  @override
  String get pnStepType => 'Вид';

  @override
  String get pnStepParties => 'Стороны';

  @override
  String get pnStepCapital => 'Капитал';

  @override
  String get pnStepProfit => 'Прибыль и убыток';

  @override
  String get pnStepTerms => 'Условия';

  @override
  String get pnStepReview => 'Проверка';

  @override
  String get pnName => 'Название (например, швейный цех)';

  @override
  String get pnMyRole => 'Моя роль';

  @override
  String get pnMyName => 'Моё имя';

  @override
  String get pnPartnerName => 'Имя партнёра';

  @override
  String get pnPartnerRole => 'Роль партнёра';

  @override
  String pnCapitalOf(String name, String amount) {
    return '$name: $amount';
  }

  @override
  String get pnCapitalAdd => 'Добавить капитал';

  @override
  String get pnCapitalTitle => 'Название (например, швейная машина)';

  @override
  String get pnCapitalAmount => 'Цена или сумма';

  @override
  String get pnCapitalNone => 'Не вносит капитал (труд)';

  @override
  String get pnProfitMethod => 'Как делится прибыль?';

  @override
  String get pnProfitPercent => 'Процент чистой прибыли';

  @override
  String get pnProfitFixed => 'Фиксированная сумма (в месяц …)';

  @override
  String get pnProfitGuaranteed => 'Прибыль, обещанная даже при убытке';

  @override
  String get pnNotPartnership =>
      'Это не партнёрство — это риба или долг. В партнёрстве прибыль — только процент от чистой прибыли: нет прибыли — никто не получает, убыток делится по правилам.';

  @override
  String get pnMyShare => 'Моя доля, %';

  @override
  String pnPartnerShare(String percent) {
    return 'Доля партнёра: $percent %';
  }

  @override
  String get pnLossRuleMudaraba =>
      'Убыток: финансовый убыток несёт владелец капитала; работник теряет труд. Исключение — небрежность или нарушение условий (с пояснением).';

  @override
  String pnLossRuleMusharaka(String shares) {
    return 'Убыток пропорционально капиталу: $shares.';
  }

  @override
  String get pnTermMonths => 'Срок (мес.)';

  @override
  String get pnReportPeriod => 'Периодичность отчёта';

  @override
  String get pnEndTerms => 'Что будет по окончании срока?';

  @override
  String get pnEndTermsDefault =>
      'Производится расчёт: капитал и оборудование возвращаются владельцу, последняя прибыль делится по долям.';

  @override
  String get pnDisputeTerms => 'Как решаются споры?';

  @override
  String get pnDisputeTermsDefault =>
      'Сначала взаимный совет, затем при участии свидетелей и уважаемого старейшины.';

  @override
  String get pnWitnesses => 'Свидетели';

  @override
  String get pnWitnessAdd => 'Добавить свидетеля';

  @override
  String get pnNext => 'Далее';

  @override
  String get pnBack => 'Назад';

  @override
  String get pnCreate => 'Создать договор';

  @override
  String get pnTemplatePending =>
      'Шаблон ещё не проверен юристом и улемами — это запись для личного учёта, не юридическая гарантия.';

  @override
  String pnContractVersion(int version) {
    return 'Договор, версия $version';
  }

  @override
  String get pnResign => 'Договор изменён — все должны подписать заново.';

  @override
  String get pnAmend => 'Изменить договор';

  @override
  String get pnAmendTerm => 'Новый срок (мес.)';

  @override
  String get pnPdf => 'Создать и отправить PDF';

  @override
  String get pnPdfTitle => 'Договор партнёрства';

  @override
  String get pnPdfParties => 'Стороны и капитал';

  @override
  String get pnPdfTerms => 'Условия';

  @override
  String get pnPdfShare => 'Доля прибыли';

  @override
  String get pnPdfCapital => 'Капитал';

  @override
  String get pnPdfRole => 'Роль';

  @override
  String get pnPdfName => 'Имя';

  @override
  String get pnPdfType => 'Вид';

  @override
  String get pnPdfLoss => 'Правило убытка';

  @override
  String get pnPdfNote =>
      'Партнёрство — не милостыня и не долг: прибыль только как процент от чистой прибыли, заранее обещанного дохода нет. Запись для личного учёта, не юридическая гарантия.';

  @override
  String get pnPdfVersion => 'Версия';

  @override
  String get pnLossCalc => 'Кто несёт убыток?';

  @override
  String pnLossAmount(String amount) {
    return 'Сумма убытка: $amount';
  }

  @override
  String get pnNegligence => 'Небрежность работника или нарушение условий';

  @override
  String get pnNegligenceNote => 'Пояснение (что случилось?)';

  @override
  String get pnNegligenceNoteRequired =>
      'Небрежность без пояснения не принимается.';

  @override
  String get pnActivate => 'Начать партнёрство';

  @override
  String get pnActivated => 'Партнёрство действует.';

  @override
  String get pnSignFirst => 'Перед началом договор подписывают все.';

  @override
  String get pnGateTitle => 'Внесение капитала — проверка готовности';

  @override
  String get pnGateClosed =>
      'Проверка не пройдена: сначала резерв на 6 месяцев и план по долгам. Если всё же вносите — это будет записано как осознанное решение.';

  @override
  String get pnGateOpen => 'Проверка пройдена — вы готовы вносить капитал.';

  @override
  String get pnGateBypass => 'Всё равно начать';

  @override
  String get pnNotDebtTitle => 'Это не долг';

  @override
  String get pnNotDebtBody =>
      'В мудараба полученный капитал — не долг: обязанности возврата нет, убыток несёт владелец капитала (кроме небрежности). Прибыль делится по долям. Посоветуйтесь с семьёй.';

  @override
  String get pnNotDebtAck => 'Понятно';

  @override
  String get pnConsentTitle => 'Согласие семьи';

  @override
  String get pnConsent => 'Согласен(на)';

  @override
  String get pnConsented => 'Согласие дано';

  @override
  String get pnBuyoutTitle => 'Поэтапный выкуп доли';

  @override
  String get pnBuyoutHint =>
      'Работник понемногу из своей доли прибыли выкупает долю владельца капитала и в итоге становится самостоятельным.';

  @override
  String pnBuyoutMonthly(String amount) {
    return 'В месяц: $amount';
  }

  @override
  String get pnBuyoutSet => 'Задать ежемесячный платёж';

  @override
  String pnBuyoutRemaining(String amount, String percent) {
    return 'Оставшаяся доля владельца капитала: $amount ($percent %)';
  }

  @override
  String pnBuyoutEnd(String date, int months) {
    return 'Полный выкуп: $date ($months мес.)';
  }

  @override
  String get pnBuyoutPay => 'Записать платёж';

  @override
  String get pnBuyoutHistory => 'Платежи выкупа';

  @override
  String get pnBuyoutNone => 'Платежей пока нет.';

  @override
  String pnBuyoutPaidRow(String amount, String date) {
    return '$amount — $date';
  }

  @override
  String get pnClose => 'Закрыть партнёрство';

  @override
  String get pnErrorShares => 'Сумма долей должна быть 100 %.';

  @override
  String get agAlreadySigned => 'Эта сторона уже подписала договор.';

  @override
  String get expenseDeleted => 'Расход удалён.';

  @override
  String get pnAlreadySigned => 'Эта сторона уже подписала договор.';

  @override
  String get pnErrorCapital => 'В мушарака капитал вносят обе стороны.';

  @override
  String get pnErrorRoles =>
      'В мудараба капитал от одной стороны, труд — от другой.';

  @override
  String get pnErrorNoCapital =>
      'Добавьте деньги или оборудование, которые вносит владелец капитала.';

  @override
  String get ledgerTitle => 'Кассовая книга';

  @override
  String get ledgerHint =>
      'Деньги дела отдельно от домашних: в семейный бюджет попадает только ваша распределённая доля.';

  @override
  String get ledgerReadOnly =>
      'Книгу ведёт работник; вы только просматриваете её и получаете отчёт за период.';

  @override
  String ledgerOpenPeriod(String start) {
    return 'Открытый период: $start — сегодня';
  }

  @override
  String ledgerIncome(String amount) {
    return 'Приход: $amount';
  }

  @override
  String ledgerExpense(String amount) {
    return 'Расход: $amount';
  }

  @override
  String ledgerNet(String amount) {
    return 'Чистая прибыль: $amount';
  }

  @override
  String ledgerLoss(String amount) {
    return 'Убыток: $amount';
  }

  @override
  String get ledgerAdd => 'Добавить запись';

  @override
  String get ledgerKindIncome => 'Приход (заказ)';

  @override
  String get ledgerKindExpense => 'Расход';

  @override
  String get ledgerKindForce => 'Форс-мажор';

  @override
  String get ledgerKindCorrection => 'Корректировка';

  @override
  String get ledgerEntryTitle => 'За что? (заказ, ткань, зарплата…)';

  @override
  String get ledgerNote => 'Пояснение (доказательство, детали)';

  @override
  String get ledgerAttach => 'Фото чека';

  @override
  String get ledgerAttached => 'Фото прикреплено';

  @override
  String get ledgerCorrectionMinus => 'Уменьшает прибыль';

  @override
  String get ledgerLocked => 'Закрытый период — не меняется';

  @override
  String get ledgerClose => 'Закрыть период и распределить';

  @override
  String get ledgerCloseConfirm =>
      'После закрытия записи не меняются; исправление — только новой записью в следующем периоде. Закрыть?';

  @override
  String get ledgerClosedTitle => 'Закрытые периоды';

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
    return 'Выкуп: $amount';
  }

  @override
  String get ledgerReport => 'Отчёт PDF';

  @override
  String get ledgerEmpty => 'Записей пока нет.';

  @override
  String ledgerClosedSnack(String amount) {
    return 'Период закрыт. Ваша доля записана в доход семьи: $amount';
  }

  @override
  String get ledgerClosedPlain => 'Период закрыт.';

  @override
  String get ledgerReportTitle => 'Отчёт партнёрства за период';

  @override
  String get ledgerReportDistribution => 'Распределение';

  @override
  String get ledgerReportEntries => 'Записи';

  @override
  String get ledgerReportBuyout => 'Оставшаяся доля владельца капитала';

  @override
  String get ledgerReportNote =>
      'Отчёт для прозрачности перед партнёром: приход, расход, прибыль и распределение — по записям книги.';

  @override
  String get ledgerOpenButton => 'Кассовая книга';

  @override
  String get ideasTitle => 'От ремесла к делу';

  @override
  String get ideasHint =>
      'Ремёсла семьи, которые простаивают: шитьё, кулинария, ремонт, языки… Посчитайте трижды.';

  @override
  String get skillsTitle => 'Ремёсла';

  @override
  String get skillAdd => 'Добавить ремесло';

  @override
  String get skillName => 'Ремесло (например, шитьё)';

  @override
  String get ideasList => 'Идеи';

  @override
  String get ideaAdd => 'Расчёт идеи';

  @override
  String get ideaName => 'Идея (например, швейный цех дома)';

  @override
  String get ideaCapex => 'Стартовые вложения (CAPEX)';

  @override
  String get ideaCapexAdd => 'Добавить позицию';

  @override
  String get ideaCapexTitle => 'Что? (оверлок, раскройный стол, ткань…)';

  @override
  String ideaCapexTotal(String amount) {
    return 'Итого: $amount';
  }

  @override
  String ideaIncome(String amount) {
    return 'Доход в месяц (средний): $amount';
  }

  @override
  String ideaExpense(String amount) {
    return 'Расход в месяц: $amount';
  }

  @override
  String get ideaIncomeTitle => 'Средний доход в месяц';

  @override
  String get ideaExpenseTitle => 'Расход в месяц';

  @override
  String get ideaShare => 'Моя доля в партнёрстве, %';

  @override
  String get ideaSave => 'Рассчитать и сохранить';

  @override
  String get scenarioPessimistic => 'Пессимистичный';

  @override
  String get scenarioBase => 'Средний';

  @override
  String get scenarioOptimistic => 'Оптимистичный';

  @override
  String ideaScenarioLine(String income, String expense, String net) {
    return 'Доход $income · расход $expense · прибыль $net';
  }

  @override
  String ideaMyNet(String amount) {
    return 'После раздела: $amount';
  }

  @override
  String ideaPayback(int months) {
    return 'Окупится за $months мес.';
  }

  @override
  String get ideaNoPayback => 'Не окупается — пересмотрите расходы или цену';

  @override
  String get ideaToContract => 'Черновик договора';

  @override
  String get offerTitle => 'Проверить предложение';

  @override
  String get offerHint =>
      'Если обещают прибыль без риска — там либо риба, либо мошенничество.';

  @override
  String get offerName => 'Предложение (например, «группа сигналов»)';

  @override
  String get offerQGuaranteed => 'Прибыль обещана заранее (даже при убытке)?';

  @override
  String get offerQLoss => 'Если будет убыток, он делится?';

  @override
  String get offerQReal => 'За этим стоит реальный товар или работа?';

  @override
  String get offerQRecruit => 'Требуется привлекать новых людей?';

  @override
  String get offerQPressure => 'Торопят: «решайте прямо сейчас»?';

  @override
  String get offerQContract => 'Есть письменный договор?';

  @override
  String get offerYes => 'Да';

  @override
  String get offerNo => 'Нет';

  @override
  String get offerUnknown => 'Не знаю';

  @override
  String get offerCheck => 'Оценить';

  @override
  String get offerGreen =>
      'Зелёный: серьёзных признаков риска нет. Всё равно прочитайте договор и посоветуйтесь.';

  @override
  String get offerYellow =>
      'Жёлтый: уточните — признаки ниже вызывают сомнение.';

  @override
  String get offerRed =>
      'Красный: это признак рибы или мошенничества. Не давайте денег.';

  @override
  String get offerFlagGuaranteed =>
      'Обещание прибыли без риска — это не партнёрство: либо риба, либо мошенничество.';

  @override
  String get offerFlagLoss =>
      'Если убыток не делится — это не партнёрство, а долг или риба.';

  @override
  String get offerFlagReal =>
      'Без реального товара или работы «прибыль» платят из денег новичков.';

  @override
  String get offerFlagRecruit =>
      'Требование привлекать новых участников — признак пирамиды.';

  @override
  String get offerFlagPressure => 'Спешка — способ не дать время подумать.';

  @override
  String get offerFlagContract =>
      'Договорённость без письменного договора не защитить.';

  @override
  String offerFlagUnknown(String question) {
    return 'Ответ неизвестен — сначала уточните: $question';
  }

  @override
  String get offerHistory => 'Прошлые проверки';

  @override
  String get offerVerdictGreen => 'Зелёный';

  @override
  String get offerVerdictYellow => 'Жёлтый';

  @override
  String get offerVerdictRed => 'Красный';

  @override
  String get homeOfferCheckBody =>
      'Кто-то обещает прибыль без риска? Проверьте за минуту.';

  @override
  String get ledgerNetLabel => 'Чистая прибыль';

  @override
  String get ledgerLossLabel => 'Убыток';

  @override
  String get ledgerBuyoutLabel => 'Платёж выкупа';

  @override
  String ledgerNextPeriod(String start) {
    return 'Следующий период: с $start';
  }

  @override
  String get obWelcome => 'Ассалому алайкум! Добро пожаловать в Барака Дастур';

  @override
  String get obLanguage => 'Язык';

  @override
  String get obLanguageHint => 'Позже можно изменить в настройках.';

  @override
  String get obRestore => 'Восстановить из резервной копии';

  @override
  String get obFamily => 'Члены семьи';

  @override
  String get obFamilyHint =>
      'У каждой записи будет отметка «кто?». Если ведёте один — укажите только своё имя.';

  @override
  String get obOwnerName => 'Ваше имя';

  @override
  String get obAddMember => 'Добавить члена семьи';

  @override
  String get obMemberAdult => 'Взрослый';

  @override
  String get obMemberChild => 'Ребёнок';

  @override
  String get obIncome => 'Как приходит ваш доход?';

  @override
  String get obIncomeHint => 'Под это подстроятся главный экран и напоминания.';

  @override
  String get obIncomeDaily => 'Ежедневно наличными';

  @override
  String get obIncomeDailyHint =>
      'Такси, рынок, мастер — каждый вечер напомним: «сколько сегодня?».';

  @override
  String get obIncomeOrders => 'По заказам';

  @override
  String get obIncomeOrdersHint =>
      'Шитьё, кулинария, ремонт — каждую субботу недельное напоминание.';

  @override
  String get obIncomeSalary => 'Ежемесячная зарплата';

  @override
  String get obIncomeSalaryHint =>
      'Напомним в день зарплаты; месячный период начнётся с этого дня.';

  @override
  String get obSalaryDay => 'День зарплаты';

  @override
  String get obDebt => 'Есть ли у вас сейчас долги?';

  @override
  String get obDebtHint =>
      'Банк, магазин в долг, родня или друзья — всё учитывается. Это не покидает приложение.';

  @override
  String get obDebtYes => 'Да, есть';

  @override
  String get obDebtNo => 'Нет';

  @override
  String get obDebtRecovery =>
      'После записи долгов предложим режим выхода из долгов: 70 % на хозяйство, 20 % на ускоренное погашение, 10 % всё равно в «Моё будущее».';

  @override
  String get obNext => 'Продолжить';

  @override
  String get obFinish => 'Начать';

  @override
  String obStep(int step, int total) {
    return '$step / $total';
  }

  @override
  String get reminderIncomeTitle => 'Записали доход?';

  @override
  String get reminderIncomeDaily =>
      'Сколько заработали сегодня? Запишите за минуту — доля тоже отложится.';

  @override
  String get reminderIncomeWeekly => 'Деньги за заказы этой недели записаны?';

  @override
  String get reminderIncomeMonthly =>
      'Сегодня день зарплаты. Сначала заплатите себе — отложите долю в «Моё будущее».';

  @override
  String get settingsIncomeKind => 'Тип дохода';

  @override
  String get backupTitle => 'Резервная копия';

  @override
  String get backupHint =>
      'Вся книга записывается в файл, зашифрованный вашим паролем. При смене телефона или удалении приложения восстановите из этого файла с паролем. Не забудьте пароль: его никто не восстановит.';

  @override
  String get backupPassword => 'Пароль (не менее 8 символов)';

  @override
  String get backupPasswordRepeat => 'Повторите пароль';

  @override
  String get backupPasswordMismatch => 'Пароли не совпадают.';

  @override
  String get backupExport => 'Создать и сохранить копию';

  @override
  String get backupImport => 'Восстановить из файла';

  @override
  String get backupImportConfirm =>
      'Текущие данные будут полностью заменены данными из копии. Продолжить?';

  @override
  String get backupImportPassword => 'Пароль копии';

  @override
  String backupRestored(int count) {
    return 'Восстановлено записей: $count.';
  }

  @override
  String get backupBadPassword => 'Неверный пароль или файл повреждён.';

  @override
  String get backupBadFormat => 'Это не резервная копия Барака Дастур.';

  @override
  String get backupVersion =>
      'Копия создана в другой версии приложения — обновите приложение.';

  @override
  String get backupWorking => 'Шифрование…';

  @override
  String get homeAddIncomeDaily => 'Выручка за день';

  @override
  String get homeAddIncomeOrders => 'Оплата заказа';

  @override
  String get homeAddIncomeSalary => 'Зарплата';

  @override
  String get reminderIncomeChannel => 'Напоминания о доходе';

  @override
  String get settingsBackupHint =>
      'Файл, зашифрованный паролем: сохранение и восстановление';

  @override
  String get backupRestoring => 'Восстановление…';

  @override
  String get backupExportTitle => 'Создать копию';

  @override
  String get backupImportTitle => 'Восстановить из копии';

  @override
  String get backupImportHint =>
      'Выберите файл и введите пароль, заданный при создании копии.';

  @override
  String get obMemberRemove => 'Убрать';

  @override
  String showMore(int count) {
    return 'Показать ещё ($count)';
  }

  @override
  String get settingsIncomeKindUnset => 'Выберите';

  @override
  String get roleArbiter => 'Третейский судья';

  @override
  String get receiptErrName => 'Укажите имя.';

  @override
  String get receiptErrSignature => 'Подпись не нарисована.';

  @override
  String get agTitle => 'Договорённости';

  @override
  String get agScreenTitle => 'Договорённость';

  @override
  String get agIntro =>
      'Устная договорённость — дом на песке. Записать — не недоверие, а способ сберечь доверие.';

  @override
  String get agEmpty =>
      'Договорённостей пока нет. Запишите аренду, услугу, семейную договорённость или ту, что сейчас держится на словах.';

  @override
  String get agNew => 'Новая договорённость';

  @override
  String get agTypePartnership => 'Партнёрство';

  @override
  String get agTypeLoan => 'Расписка о долге';

  @override
  String get agTypeRent => 'Аренда';

  @override
  String get agTypeService => 'Услуга или работа';

  @override
  String get agTypeFamily => 'Семейная договорённость';

  @override
  String get agTypeOther => 'Другое';

  @override
  String get agStatusDraft => 'Черновик';

  @override
  String get agStatusSigned => 'Подписана';

  @override
  String get agStatusActive => 'Действует';

  @override
  String get agStatusDispute => 'Спор';

  @override
  String get agStatusClosed => 'Закрыта';

  @override
  String agVersion(int n) {
    return 'Версия $n';
  }

  @override
  String get agOralBadge => 'записана с устной';

  @override
  String agEffectiveFrom(String date) {
    return 'Действует с: $date';
  }

  @override
  String get agLegacyHint =>
      'Документ подписан до порядка из 9 вопросов — подписи действительны. В следующей версии заполните вопросы.';

  @override
  String agProgress(int n) {
    return 'Отвечено на $n из 9 вопросов';
  }

  @override
  String get agReadyHint => '9 вопросов готовы — можно подписывать.';

  @override
  String get agSignLocked =>
      'Подписание откроется, когда на все 9 вопросов будет дан ответ (или отмечено «не относится» с пояснением).';

  @override
  String get agAdvisorTip =>
      'Совет: заранее запишите и неудобные пункты — например, что будет, если кто-то неделю не сможет выполнять своё дело. Чётко записанное правило предотвращает будущие споры.';

  @override
  String get agNeedsAnswer => 'Нужен ответ';

  @override
  String get agAutoBadge => 'Заполнено из документа';

  @override
  String get agAutoHint =>
      'Этот ответ берётся из исходного документа — меняйте договор или запись о долге.';

  @override
  String get agErrSigned =>
      'Подписанная версия не меняется — создайте новую версию.';

  @override
  String get agQ1 => 'Кто с кем?';

  @override
  String get agQ2 => 'Кто что вносит?';

  @override
  String get agQ3 => 'Кто что делает?';

  @override
  String get agQ4 => 'Как делится прибыль?';

  @override
  String get agQ5 => 'Что будет при убытке?';

  @override
  String get agQ6 =>
      'Где деньги, кто ведёт учёт, когда смотрит вторая сторона?';

  @override
  String get agQ7 => 'Как выйти из договорённости?';

  @override
  String get agQ8 => 'Кто рассудит, если не договоритесь?';

  @override
  String get agQ9 => 'Когда пересматривается?';

  @override
  String get agQ1Hint => 'Полное имя, роль и связь. Минимум две стороны.';

  @override
  String get agQ2Hint =>
      'Деньги, товар, труд или связи — у каждой стороны минимум один вклад.';

  @override
  String get agQ3Hint =>
      'У каждого дела — один ответственный и пункт «если не выполнено». Дело, оставленное «на всех», часто не делает никто.';

  @override
  String get agQ4Hint =>
      'Только в процентах. Фиксированная сумма в партнёрстве запрещена.';

  @override
  String get agQ5Hint =>
      'В мудараба убыток несёт владелец капитала, в мушарака — пропорционально капиталу.';

  @override
  String get agQ6Hint => 'По умолчанию — открытая сверка раз в месяц.';

  @override
  String get agQ7Hint =>
      'Предупреждение заранее, оценка доли, срок выплаты и раздел имущества.';

  @override
  String get agQ8Hint =>
      'Человек, которому доверяют обе стороны, но не сама сторона. Судья тоже подписывает согласие.';

  @override
  String get agQ9Hint =>
      'Срок и дата ежегодного пересмотра; напомним за 30 дней.';

  @override
  String agQuestionTitle(int n, String title) {
    return '$n. $title';
  }

  @override
  String get agNotApplicable => 'Не относится';

  @override
  String get agNaReason => 'Почему не относится (пояснение обязательно)';

  @override
  String agNaSummary(String reason) {
    return 'Не относится: $reason';
  }

  @override
  String get agPartyName => 'Полное имя';

  @override
  String get agPartyRole => 'Роль';

  @override
  String get agPartyRelation => 'Связь (родственник, сосед…)';

  @override
  String get agPartyAdd => 'Добавить сторону';

  @override
  String get agWho => 'Кто';

  @override
  String get agContribKind => 'Вид вклада';

  @override
  String get agContribMoney => 'Деньги';

  @override
  String get agContribGoods => 'Товар или оборудование';

  @override
  String get agContribLabor => 'Труд';

  @override
  String get agContribNetwork => 'Связи';

  @override
  String get agAmountSom => 'Сумма (сум)';

  @override
  String get agDescription => 'Описание';

  @override
  String get agContribAdd => 'Добавить вклад';

  @override
  String get agDutyHint =>
      'Ответственный — одна сторона. «Все» выбрать нельзя.';

  @override
  String get agDutyTitle => 'Дело';

  @override
  String get agDutyOwner => 'Единственный ответственный';

  @override
  String get agDutyBreach =>
      'Если не выполнено (например, за 1 день сообщит и найдёт замену)';

  @override
  String get agDutyAdd => 'Добавить дело';

  @override
  String get agProfitHint => 'Доли в процентах, сумма 100 %.';

  @override
  String agProfitShare(String name) {
    return 'Доля $name, %';
  }

  @override
  String get agProfitText => 'Или словами (например, аренда в месяц …)';

  @override
  String get agLossText => 'Как распределяется убыток';

  @override
  String get agLossMusharaka =>
      'Убыток распределяется пропорционально капиталу.';

  @override
  String get agLossLoan =>
      'В долге прибыль и убыток не делятся — возвращается только основная сумма (без процентов).';

  @override
  String get agLoanSchedule => 'График возврата (из записи о долге)';

  @override
  String get agLoanNoInterest => 'Без процентов';

  @override
  String get agCustodyWhere => 'Где хранятся деньги';

  @override
  String get agCustodyKeeper => 'Кто ведёт учёт';

  @override
  String get agCustodyEvery => 'Открытая сверка';

  @override
  String get agEveryWeek => 'Каждую неделю';

  @override
  String get agEvery2Weeks => 'Раз в две недели';

  @override
  String get agEveryMonth => 'Раз в месяц';

  @override
  String get agEveryQuarter => 'Раз в квартал';

  @override
  String get agEveryYear => 'Раз в год';

  @override
  String agEveryDays(int days) {
    return 'Каждые $days дн.';
  }

  @override
  String get agReviewTooRare =>
      'Сверка реже раза в месяц — чтобы недоразумения не копились, сверяйтесь чаще.';

  @override
  String get agExitNotice => 'Предупреждение заранее (дней)';

  @override
  String get agExitValuation => 'Как оценивается доля';

  @override
  String get agExitPayout => 'Когда и как выплачивается';

  @override
  String get agExitAssets => 'Как делится имущество';

  @override
  String get agArbiterHint => 'Судья не может быть одной из сторон.';

  @override
  String get agArbiterName => 'Имя судьи';

  @override
  String get agArbiterRole => 'Кто (например, старейшина махалли)';

  @override
  String get agWitnesses => 'Свидетели (через запятую)';

  @override
  String get agTermMonths => 'Срок (мес.)';

  @override
  String get agReviewDate => 'Дата ежегодного пересмотра';

  @override
  String agReviewOn(String date) {
    return 'Пересмотр: $date';
  }

  @override
  String get agErrPartiesMin2 => 'Нужны минимум две стороны с именами.';

  @override
  String get agErrContribution => 'Укажите вклад каждой стороны.';

  @override
  String get agErrDutyOwner =>
      'Назначьте одного ответственного на каждое дело.';

  @override
  String get agErrDutyBreach =>
      'Для каждого дела укажите пункт «если не выполнено».';

  @override
  String get agErrShares => 'Сумма долей должна быть 100 %.';

  @override
  String get agErrGuaranteed =>
      'Это не партнёрство — фиксированная сумма будет рибой или долгом. Прибыль только в процентах.';

  @override
  String get agErrArbiterParty => 'Судья не может быть одной из сторон.';

  @override
  String get agErrNaReason => 'Поясните, почему «не относится».';

  @override
  String get agErrTitle => 'Укажите название.';

  @override
  String get agErrIncomplete => 'Сначала ответьте на все 9 вопросов.';

  @override
  String get agErrFuture =>
      'Устная договорённость начинается с прошедшей даты.';

  @override
  String get agErrNotSigned => 'Сначала пусть подпишут все.';

  @override
  String get agSignatures => 'Подписи';

  @override
  String get agPrepareSign => 'Перейти к подписанию';

  @override
  String get agSignInPartnership => 'Подписи — на экране договора партнёрства';

  @override
  String get agActivate => 'Ввести в действие';

  @override
  String get agRenewUnchanged =>
      'Ежегодный пересмотр: подтвердить без изменений';

  @override
  String get agUnchangedNote => 'Подтверждено без изменений';

  @override
  String get agNewVersion => 'Новая версия (изменения)';

  @override
  String get agJournal => 'Журнал учёта';

  @override
  String agChainOk(int n) {
    return 'Записей: $n · цепочка цела, ничего не изменено';
  }

  @override
  String agChainBroken(int n) {
    return 'Внимание: цепочка нарушена начиная с записи $n — запись могла быть изменена';
  }

  @override
  String get agChainHead => 'Голова цепочки';

  @override
  String get agJContribution => 'Вклад';

  @override
  String get agJProfit => 'Доля прибыли';

  @override
  String get agJLoss => 'Доля убытка';

  @override
  String get agJLoanPayment => 'Платёж по долгу';

  @override
  String get agJIncome => 'Приход';

  @override
  String get agJExpense => 'Расход';

  @override
  String get agJForceMajeure => 'Форс-мажор';

  @override
  String get agJBuyout => 'Выкуп доли';

  @override
  String get agJOpening => 'Начальное состояние';

  @override
  String get agJCorrection => 'Исправление';

  @override
  String get agPdfShare => 'PDF договорённости';

  @override
  String agPdfSubtitle(int version, String date) {
    return 'Версия $version · с $date';
  }

  @override
  String get agPdfIntro =>
      'Договорённость простым языком по 9 основным вопросам.';

  @override
  String get agPdfNote =>
      'Запись для личного учёта, не юридическая гарантия и не консультация.';

  @override
  String get agFieldTitle => 'Название (например, аренда магазина)';

  @override
  String get agFieldMe => 'Ваше имя';

  @override
  String get agFieldOther => 'Вторая сторона';

  @override
  String get agFieldType => 'Тип';

  @override
  String get agOralTitle => 'Записать устную договорённость';

  @override
  String get agOralHint =>
      'Партнёрство, аренда или долг, которые сейчас держатся на словах';

  @override
  String get agOralIntro =>
      'Договорённость могла начаться в прошлом. Внесите состояние на сегодня одной записью — стороны подтвердят его подписью.';

  @override
  String get agOralSince => 'С какого времени';

  @override
  String get agOralOpening => 'Состояние на сегодня';

  @override
  String get agOralOpeningHint =>
      'Кто сколько вложил, сколько поделено, сколько долга осталось.';

  @override
  String get agOralMine => 'Ваш вклад';

  @override
  String get agOralTheirs => 'Вклад второй стороны';

  @override
  String get agOralNote =>
      'Пояснение (например, за 3 месяца прибыль делили 2 раза)';

  @override
  String get agOralSave => 'Записать и перейти к 9 вопросам';

  @override
  String get acDutiesTitle => 'Обязанности';

  @override
  String get acDutyReport => 'Не могу выполнить';

  @override
  String get acDutyReportTitle => 'Не могу выполнить обязанность';

  @override
  String get acDutyReason => 'Причина';

  @override
  String get acDutyFix => 'Предложение взамен (необязательно)';

  @override
  String get acDutyWho => 'Кто сообщает';

  @override
  String get acDutyClauseTitle => 'Пункт договора';

  @override
  String acDutyClauseBody(Object clause) {
    return '$clause\n\nЭто не вина — вернёмся к согласованному правилу.';
  }

  @override
  String get acIncidentsTitle => 'События после последней проверки';

  @override
  String acIncidentLine(Object reason, Object fix) {
    return '$reason — $fix';
  }

  @override
  String acIncidentNoFix(Object reason) {
    return '$reason';
  }

  @override
  String get acReviewTitle => 'Ежемесячная открытая проверка счёта';

  @override
  String acReviewNext(Object date) {
    return 'Следующая проверка: $date';
  }

  @override
  String get acReviewDue => 'Пора провести проверку';

  @override
  String acReviewOpenInfo(Object date) {
    return 'Проверка открыта. Дата среза: $date';
  }

  @override
  String get acReviewStart => 'Начать проверку';

  @override
  String get acReviewContinue => 'Перейти к проверке';

  @override
  String acReviewMinutesCount(int count) {
    return 'Протоколов: $count';
  }

  @override
  String get acReviewScreenTitle => 'Проверка';

  @override
  String acReviewCutoff(Object date) {
    return 'Дата среза: $date';
  }

  @override
  String get acReviewPeriodTitle => 'Записи периода';

  @override
  String get acReviewPeriodEmpty => 'В этом периоде записей нет.';

  @override
  String acReviewTotals(Object income, Object expense) {
    return 'Доход: $income · Расход: $expense';
  }

  @override
  String acReviewChainOk(int count) {
    return 'Цепочка целая ($count записей)';
  }

  @override
  String acReviewChainBroken(int seq) {
    return 'Цепочка нарушена: №$seq';
  }

  @override
  String get acReviewIncidents => 'События';

  @override
  String get acReviewAgree => 'Ознакомлен, согласен';

  @override
  String get acReviewObject => 'Есть возражения';

  @override
  String get acReviewObjectTitle => 'Возражение';

  @override
  String get acReviewObjectHint => 'С чем вы не согласны?';

  @override
  String acReviewVerdictAgree(Object party) {
    return '$party: согласен';
  }

  @override
  String acReviewVerdictObject(Object party, Object note) {
    return '$party: возражение — $note';
  }

  @override
  String get acReviewWaiting =>
      'Когда все стороны ответят, завершите протокол.';

  @override
  String get acReviewComplete => 'Завершить протокол';

  @override
  String get acReviewDone => 'Проверка завершена. Протокол сохранён.';

  @override
  String get acReviewLockedNote =>
      'Финансовые записи до этой даты заморожены; можно добавлять только исправления.';

  @override
  String get acReviewMinutesShare => 'Поделиться протоколом (PDF)';

  @override
  String get acReviewLedgerTitle => 'Записи счёта';

  @override
  String get acDisputesTitle => 'Споры';

  @override
  String get acDisputeNone => 'Открытых споров нет.';

  @override
  String get acDisputeOpen => 'Открыть спор';

  @override
  String get acDisputeTopic => 'Тема';

  @override
  String get acDisputeClause => 'Пункт (необязательно)';

  @override
  String get acDisputeClaim => 'Ваше требование';

  @override
  String get acDisputeAddClaim => 'Добавить требование';

  @override
  String get acDisputeStatusOpen => 'Открыт';

  @override
  String get acDisputeStatusDecided => 'Решён';

  @override
  String get acDisputeScreenTitle => 'Спор';

  @override
  String get acDisputeClaimsTitle => 'Требования сторон';

  @override
  String get acDisputeDecisionTitle => 'Решение арбитра';

  @override
  String get acDisputeDecisionHint => 'Текст решения';

  @override
  String get acDisputeDecide => 'Записать решение';

  @override
  String get acDisputePdf => 'Папка дела для арбитра (PDF)';

  @override
  String get acDisputeInDispute =>
      'Договор в споре: распределение приостановлено.';

  @override
  String get acDisputeDecidedNote =>
      'Решение записано. Договор снова действует.';

  @override
  String get acRenewalTitle => 'Ежегодное обновление';

  @override
  String acRenewalDue(Object date) {
    return 'Дата обновления: $date. Напоминание за 30 дней.';
  }

  @override
  String get acRenewalUnchanged => 'Подтвердить без изменений';

  @override
  String get acRenewalNeedsSign =>
      'Новую версию должны снова подписать все стороны.';

  @override
  String get acRenewalNotifTitle => 'Пора обновить договор';

  @override
  String acRenewalNotifBody(Object title) {
    return '«$title» обновляется через 30 дней. Перечитайте вместе.';
  }

  @override
  String get acRenewalChannel => 'Напоминания о договорах';

  @override
  String get acSpikeTitle => 'Крупная прибыль';

  @override
  String get acSpikeMessage =>
      'Прибыль с благословением — поздравляем! Теперь давайте вместе перечитаем договор.';

  @override
  String acSpikeAmount(Object amount) {
    return 'Прибыль периода: $amount';
  }

  @override
  String acSpikeRead(Object party) {
    return '$party перечитал(а) пункты 4–5';
  }

  @override
  String get acSpikeReviewOffer => 'Внеочередная проверка';

  @override
  String get acSpikeDistribute => 'Распределить';

  @override
  String get acSpikeCancel => 'Пока нет';

  @override
  String get acHomeTitle => 'Скоро проверка / обновление';

  @override
  String acHomeBody(int count) {
    return 'В $count договорах скоро проверка или обновление.';
  }

  @override
  String acHomeDisputes(int count) {
    return 'Открытых споров: $count';
  }

  @override
  String acCenterNextReview(Object date) {
    return 'Следующая проверка: $date';
  }

  @override
  String acCenterOpenIncidents(int count) {
    return 'Открытых событий: $count';
  }

  @override
  String acCenterDisputes(int count) {
    return 'Споров: $count';
  }

  @override
  String get acCenterEmptyHint => 'Здесь видны даты проверок и обновлений.';

  @override
  String get agFamilyTemplate => 'Шаблон';

  @override
  String get agFamilyHint =>
      'Семейное соглашение — не приказ, а договорённость. Свидетели и арбитр не обязательны; достаточно подтверждения взрослых.';

  @override
  String get agTplChores => 'Кто что делает дома';

  @override
  String get agTplChoresHint =>
      'Ясно, кто какие домашние дела делает; если не получилось — сообщите без упрёков.';

  @override
  String get agTplMoney => 'Где хранятся деньги и кто ведёт учёт';

  @override
  String get agTplMoneyHint =>
      'Где лежат общие деньги, кто их ведёт и как это видно.';

  @override
  String get agTplHavas => 'Лимит на прихоти';

  @override
  String get agTplHavasHint =>
      'Лимит расходов на прихоти в семье (связан с разделом «Прихоти»).';

  @override
  String get agTplCouncil => 'Когда проходит семейный совет';

  @override
  String get agTplCouncilHint =>
      'День ежемесячного совета и какие решения принимаются.';

  @override
  String get agJDutyIncident => 'Обязанность не выполнена';

  @override
  String get agJReviewOpened => 'Проверка открыта';

  @override
  String get agJReviewAck => 'Ответ на проверку';

  @override
  String get agJAccountReview => 'Протокол проверки';

  @override
  String get agJProfitSpikeAck => 'Подтверждение «крупной прибыли»';

  @override
  String get agJDisputeOpened => 'Спор';

  @override
  String get agJArbiterDecision => 'Решение арбитра';

  @override
  String get agErrReviewLocked =>
      'Записи до этой даты закрыты протоколом проверки.';

  @override
  String get agErrReviewOpen => 'Проверка открыта. Сначала завершите её.';

  @override
  String get agErrNoReview => 'Эта проверка не открыта.';

  @override
  String get agErrReviewIncomplete => 'Пусть ответят все стороны.';

  @override
  String get agErrReviewAcked => 'Эта сторона уже ответила.';

  @override
  String get agErrObjection => 'Для возражения напишите комментарий.';

  @override
  String get agErrReasonRequired => 'Напишите причину.';

  @override
  String get agErrDutyNotFound => 'Обязанность не найдена.';

  @override
  String get agErrPartyNotFound => 'Сторона не найдена.';

  @override
  String get agErrInDispute =>
      'Договор в споре — сначала нужно решение арбитра.';

  @override
  String get agErrDisputeNotFound => 'Спор не найден.';

  @override
  String get agErrDisputeDecided => 'Этот спор уже решён.';

  @override
  String get agErrClaimRequired => 'Напишите тему и требование.';

  @override
  String get agErrDecisionRequired => 'Напишите текст решения.';

  @override
  String get agErrSpikeAck =>
      'Крупная прибыль: обе стороны должны перечитать пункты 4–5 и подтвердить.';

  @override
  String get agErrAcked => 'Эта сторона уже подтвердила.';

  @override
  String get acPdfColDate => 'Дата';

  @override
  String get acPdfColKind => 'Вид';

  @override
  String get acPdfColParty => 'Сторона';

  @override
  String get acPdfColAmount => 'Сумма';

  @override
  String get acPdfColNote => 'Примечание';

  @override
  String get acReviewAcksTitle => 'Ответы сторон';

  @override
  String get acPdfFolderAgreement => 'Договор';

  @override
  String get acPdfFolderVersions => 'История версий';

  @override
  String get acPdfFolderParties => 'Стороны';

  @override
  String get acPdfFolderLedger => 'Записи периода и проверка цепочки';

  @override
  String get acPdfFolderMinutes => 'Протоколы проверок';

  @override
  String get acPdfFolderIncidents => 'События по обязанностям';

  @override
  String get acPdfFolderClaims => 'Требования сторон';

  @override
  String get acPdfFolderDecision => 'Решения арбитра';

  @override
  String get acPdfFolderIntegrity => 'Целостность цепочки';

  @override
  String get acPdfNoDecision => 'Решения арбитра пока нет.';

  @override
  String get acPdfNone => 'Нет';

  @override
  String acPdfMinutesLine(Object date, Object id, Object head) {
    return '$date · $id · начало цепочки $head';
  }

  @override
  String acPdfObjection(Object note) {
    return 'Возражение: $note';
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
    return 'Срез: $date';
  }

  @override
  String acPdfIncidentLine(Object date, Object party, Object reason) {
    return '$date · $party: $reason';
  }

  @override
  String get offerQExit => 'Можно ли забрать деньги в любой момент?';

  @override
  String get offerQLicense =>
      'Есть ли государственное разрешение собирать деньги у людей?';

  @override
  String get offerQVerified =>
      'Видели ли вы дело своими глазами (склад, товар, документы)?';

  @override
  String get offerFlagExit =>
      'Деньги трудно вернуть: если войти легко, а выйти трудно — уходите.';

  @override
  String get offerFlagLicense =>
      'Нет государственного разрешения — сбор денег у людей может быть незаконным.';

  @override
  String get offerFlagVerified =>
      'Дело не показали. Честный инициатор не скрывает своё дело.';

  @override
  String get offerVerifyTitle =>
      'Прежде чем вложить деньги, посмотрите своими глазами';

  @override
  String get offerVerifyGoods => 'Склад и товар: что продаётся и где хранится?';

  @override
  String get offerVerifyDocs =>
      'Договор: на что пойдут деньги и кто несёт убыток?';

  @override
  String get offerVerifyLicense =>
      'Государственное разрешение на сбор денег у людей';

  @override
  String get offerVerifySource =>
      'Откуда выплаты: от продажи товара или из денег новых участников?';

  @override
  String get offerVerifyExit => 'Порядок возврата денег';

  @override
  String get offerVerifyHint =>
      'Честный человек обрадуется такой просьбе. Отказ или спешка — уже признак опасности.';

  @override
  String get offerRate => 'Обещанная доходность, % в месяц (необязательно)';

  @override
  String offerRateYearly(Object rate, Object simple, Object compound) {
    return '$rate % в месяц — за год $simple раза по простому счёту и $compound раза по сложному. Честная торговля или производство не дают такой доходности стабильно.';
  }

  @override
  String get offerAmount => 'Сколько хотите вложить? (необязательно)';

  @override
  String get offerSignsTitle => 'Пять признаков опасности';

  @override
  String get offerSignsNone =>
      'Признаков опасности нет. Всё равно посмотрите дело своими глазами.';

  @override
  String get offerSignsCaution => 'Есть один признак — будьте настороже.';

  @override
  String get offerSignsFlee => 'Два признака и больше — уходите.';

  @override
  String get offerSignGuaranteed =>
      'Обещают гарантированную большую прибыль: у честной прибыли нет гарантии, в ней есть риск.';

  @override
  String get offerSignUrgency => 'Торопят: боятся, что вы подумаете.';

  @override
  String get offerSignRecruit =>
      'Доход не от товара, а от привлечения новых людей.';

  @override
  String get offerSignNoBusiness =>
      'Самого дела не видно: нет товара, документов или разрешения — только офис.';

  @override
  String get offerSignHardExit => 'Войти легко, выйти трудно.';

  @override
  String get offerCatRibo =>
      'Риба: прибыль, обещанная без риска и без разделения убытка.';

  @override
  String get offerCatGharar =>
      'Гарар: неопределённая сделка — неизвестно, что продаётся и где работают деньги.';

  @override
  String get offerCatQimor =>
      'Азартная игра: выигрыш только за счёт проигрыша других — выплаты из денег новых участников.';

  @override
  String get offerPyramidTitle => 'Как рушится пирамида?';

  @override
  String get offerPyramidRecruits => 'Сколько людей приводит каждый';

  @override
  String get offerPyramidPopulation => 'Население города';

  @override
  String offerPyramidResult(int levels, Object share) {
    return 'На $levels-м уровне люди заканчиваются. На нижнем уровне окажутся $share % участников — в день обвала они теряют деньги. На каком уровне будете вы?';
  }

  @override
  String get offerPyramidBait =>
      'Выплаты первым участникам — приманка для других: их платят из денег новых.';

  @override
  String get offerDecisionTitle => 'Решение';

  @override
  String get offerAdvisor => 'С кем вы посоветовались?';

  @override
  String get offerAdviceNote =>
      'Спросить совета — не слабость. Переспите с этим: час времени бережёт годы труда.';

  @override
  String get offerDecline => 'Отказался';

  @override
  String get offerPostpone => 'Отложу';

  @override
  String get offerAccept => 'Вложу деньги';

  @override
  String offerAcceptOpensAt(Object time) {
    return '«Вложу деньги» откроется после $time.';
  }

  @override
  String get offerDecisionDeclined => 'Отказ';

  @override
  String get offerDecisionPostponed => 'Отложено';

  @override
  String get offerDecisionAccepted => 'Вложено';

  @override
  String get offerDecisionSaved => 'Решение записано.';

  @override
  String get offerErrAdvisor => 'Сначала укажите, с кем посоветовались.';

  @override
  String get offerErrCoolingOff =>
      'Это решение откроется через 24 часа после проверки.';

  @override
  String get offerErrDecided => 'По этому предложению решение уже принято.';

  @override
  String get offerErrRate =>
      'Укажите процент правильно (например, 35 или 2,5).';

  @override
  String get lumpTitle => 'Пришла крупная сумма';

  @override
  String get lumpHint =>
      'Получили крупную сумму (многолетние накопления, наследство, продажа имущества)? Сначала пополните семейный запас на полгода, остальное — в ремесло.';

  @override
  String get lumpAmount => 'Сумма';

  @override
  String lumpRate(Object currency) {
    return 'Курс: сколько сумов за 1 $currency';
  }

  @override
  String lumpReserve(Object amount) {
    return 'В семейный запас (6 месяцев): $amount';
  }

  @override
  String lumpInvest(Object amount) {
    return 'Можно вложить в ремесло: $amount';
  }

  @override
  String get lumpWallNote =>
      'Эти деньги не вкладываются ни в торговлю, ни в партнёрство.';

  @override
  String get lumpReserveFull =>
      'Семейный запас уже полон — всё можно направить в ремесло.';

  @override
  String get lumpNoTarget =>
      'Сначала укажите необходимые расходы на 6 месяцев — тогда станет ясен нужный размер запаса.';

  @override
  String get lumpDeposit => 'Положить в запас';

  @override
  String get lumpDeposited => 'Положено в запас.';

  @override
  String get lumpIdeas => 'Перейти к «Ремесло в дело»';

  @override
  String get lumpOpen => 'Пришла крупная сумма?';

  @override
  String get ideaTplWorkshop => 'Шаблон: сварочная мастерская';

  @override
  String get ideaTplWelder => 'Сварочный аппарат';

  @override
  String get ideaTplGrinder => 'Болгарка';

  @override
  String get ideaTplRent => 'Аренда мастерской (первый месяц)';

  @override
  String get ideaTplMetal => 'Металл (на первые заказы)';

  @override
  String get ideaTplSafety => 'Защитная одежда и маска';

  @override
  String get ideaDemandQ =>
      'Есть ли спрос? Кто будет заказывать, сколько домов вокруг строится или ремонтируется?';

  @override
  String get ideaTplSuggest => 'Что понадобится — нажмите и укажите цену:';
}

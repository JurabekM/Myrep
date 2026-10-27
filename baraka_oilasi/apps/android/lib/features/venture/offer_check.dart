import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../shared/widgets.dart';

const offerQuestions = [
  'guaranteed',
  'lossShared',
  'realActivity',
  'recruitment',
  'urgency',
  'written',
  'licensed',
  'inspection',
  'exitEasy',
];
const offerReplies = ['YES', 'NO', 'UNKNOWN'];

/// Kurs yoki ustoz taklifi (uy/SPEC 2G.4): 8 savol; Musofir makonida (M6) — 9-savol `jobAbroad`.
const courseQuestions = [
  'fastRich',
  'secretFormula',
  'incomeGuarantee',
  'syllabus',
  'teacherVerifiable',
  'urgency',
  'recruitment',
  'trialOrRefund',
];
const List<String> mfCourseQuestions = [...courseQuestions, 'jobAbroad'];
const offerModes = ['OFFER', 'COURSE'];

/// Bayroq yoki xulosa rangi: yashil — aksent, sariq — ogohlantirish, qizil — xavf.
Color verdictColor(BuildContext context, String level) => switch (level) {
  'RED' => context.palette.danger,
  'YELLOW' => context.palette.warn,
  _ => context.palette.accentText,
};

/// `mode` — `OFFER` (sarmoya taklifi) yoki `COURSE` (kurs/ustoz, bilim rejasidan). `askJobAbroad` —
/// Musofir makonida kursdan keyin chet elda ish kafolati so'raladi (M6).
void openOfferCheck(BuildContext context, {String mode = 'OFFER', bool askJobAbroad = false}) =>
    showSheet<void>(context, (_) => OfferCheckSheet(initialMode: mode, askJobAbroad: askJobAbroad));

/// «Kafolatlangan foyda» detektori (uy/SPEC 2E.5): tavakkalsiz, kafolatlangan foyda va'da qilinsa —
/// u yerda yo ribo, yo firibgarlik bor. `COURSE` turi — kurs yoki ustoz taklifi (2G.4): pul faqat
/// haqiqiy hunar va bilim uchun. Qaror jadvali yadroda; hech narsa saqlanmaydi.
class OfferCheckSheet extends ConsumerStatefulWidget {
  const OfferCheckSheet({this.initialMode = 'OFFER', this.askJobAbroad = false, super.key});

  final String initialMode;

  /// Musofir makoni: `COURSE` turida 9-savol — «kursdan keyin chet elda ish kafolati».
  final bool askJobAbroad;

  @override
  ConsumerState<OfferCheckSheet> createState() => _OfferCheckSheetState();
}

class _OfferCheckSheetState extends ConsumerState<OfferCheckSheet> with ActionState {
  final _a = <String, String>{};
  OfferCheckDto? _r;
  late String _mode = widget.initialMode;

  /// So'rov raqami: tur yoki javob o'zgarsa oshadi — eski javob (boshqa tur yoki eski javoblar
  /// bilan) ko'rsatilmaydi.
  int _seq = 0;

  bool get _course => _mode == 'COURSE';

  /// Javoblar yoki tur o'zgardi: natija tozalanadi, uchayotgan so'rov eskiradi.
  void _invalidate() {
    _seq++;
    _r = null;
  }

  Future<void> _check() async {
    String v(String k) => _a[k] ?? '';
    final core = ref.read(coreProvider);
    final seq = ++_seq;
    final course = _course;
    final r = await act(
      () => course
          ? core.checkCourse(
              input: CourseAnswersInput(
                fastRich: v('fastRich'),
                secretFormula: v('secretFormula'),
                incomeGuarantee: v('incomeGuarantee'),
                syllabus: v('syllabus'),
                teacherVerifiable: v('teacherVerifiable'),
                urgency: v('urgency'),
                recruitment: v('recruitment'),
                trialOrRefund: v('trialOrRefund'),
                // Uy va Kasb-kor — so'ralmaydi (`null`).
                jobAbroad: widget.askJobAbroad ? v('jobAbroad') : null,
              ),
            )
          : core.checkOffer(
              input: OfferAnswersInput(
                guaranteed: v('guaranteed'),
                lossShared: v('lossShared'),
                realActivity: v('realActivity'),
                recruitment: v('recruitment'),
                urgency: v('urgency'),
                written: v('written'),
                licensed: v('licensed'),
                inspection: v('inspection'),
                exitEasy: v('exitEasy'),
              ),
            ),
    );
    if (!mounted) return;
    if (seq != _seq) {
      // Eski so'rov (tur yoki javoblar o'zgargan): natija ham, xato ham ko'rsatilmaydi.
      if (error != null) setState(() => error = null);
      return;
    }
    if (r != null) setState(() => _r = r);
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    final questions = _course ? (widget.askJobAbroad ? mfCourseQuestions : courseQuestions) : offerQuestions;
    final complete = questions.every(_a.containsKey);
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Semantics(
            header: true,
            child: Text(context.t('offer.title'), style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
          ),
          const SizedBox(height: 8),
          SegmentedChoice<String>(
            label: context.t('offer.mode'),
            options: [for (final m in offerModes) (m, context.t('offer.mode.$m'))],
            value: _mode,
            onChanged: (m) => setState(() {
              _mode = m;
              _a.clear();
              _invalidate();
            }),
          ),
          const SizedBox(height: 8),
          Hint(context.t(_course ? 'offer.course.intro' : 'offer.intro')),
          for (final q in questions)
            Padding(
              key: ValueKey('$_mode-$q'),
              padding: const EdgeInsets.only(top: 12),
              child: SegmentedChoice<String>(
                label: context.t(_course ? 'offer.course.q.$q' : 'offer.q.$q'),
                options: [for (final v in offerReplies) (v, context.t('offer.reply.$v'))],
                value: _a[q],
                onChanged: (v) => setState(() {
                  _a[q] = v;
                  _invalidate();
                }),
              ),
            ),
          ErrorText(error),
          if (r != null) ...[const SizedBox(height: 12), OfferResult(r, course: _course)],
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: [
              FilledButton(onPressed: !complete || busy ? null : _check, child: Text(context.t('offer.check'))),
              TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(context.t('common.close'))),
            ],
          ),
        ],
      ),
    );
  }
}

/// Taklif tekshiruvi natijasi: xulosa, belgilar soni, bayroqlar va maslahat. `course` — kurs turi
/// matnlari (xulosa «pul to'lamang», ikki belgi — kursga xos izoh).
class OfferResult extends StatelessWidget {
  const OfferResult(this.r, {this.course = false, super.key});

  final OfferCheckDto r;
  final bool course;

  String _flag(BuildContext context, String code) =>
      course && code == 'TWO_SIGNS' ? context.t('offer.course.twoSigns') : context.t('offer.flag.$code');

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    child: Container(
      key: const Key('offer-result'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: verdictColor(context, r.verdict), width: 2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            context.t(course ? 'offer.course.verdict.${r.verdict}' : 'offer.verdict.${r.verdict}'),
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: verdictColor(context, r.verdict)),
          ),
          if (r.signs > 0)
            Text(
              context.t(course ? 'offer.course.signs' : 'offer.signs', {'count': r.signs}),
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
          for (final f in r.flags)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text.rich(
                TextSpan(
                  children: [
                    TextSpan(
                      text: '● ',
                      style: TextStyle(color: verdictColor(context, f.level)),
                    ),
                    TextSpan(text: _flag(context, f.code)),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 6),
          Hint(context.t(course ? 'offer.course.advice.${r.verdict}' : 'offer.advice.${r.verdict}')),
        ],
      ),
    ),
  );
}

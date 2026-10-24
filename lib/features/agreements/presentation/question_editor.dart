import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/agreements/domain/agreement.dart';
import 'package:baraka_daftari/features/agreements/presentation/agreement_labels.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Bitta savol muharriri (SPEC 2F.2). Natija — yangilangan javoblar
/// (`null` — bekor qilindi). «Tegishli emas» uchun izoh majburiy.
Future<AgreementAnswers?> editQuestion(
  BuildContext context, {
  required AgreementType type,
  required AgreementQuestion question,
  required AgreementAnswers answers,
  required CurrencyCode currency,
}) => Navigator.of(context).push<AgreementAnswers>(
  MaterialPageRoute(
    fullscreenDialog: true,
    builder: (_) => _QuestionEditor(
      type: type,
      question: question,
      answers: answers,
      currency: currency,
    ),
  ),
);

class _QuestionEditor extends StatefulWidget {
  const _QuestionEditor({
    required this.type,
    required this.question,
    required this.answers,
    required this.currency,
  });

  final AgreementType type;
  final AgreementQuestion question;
  final AgreementAnswers answers;
  final CurrencyCode currency;

  @override
  State<_QuestionEditor> createState() => _QuestionEditorState();
}

class _QuestionEditorState extends State<_QuestionEditor> {
  late AgreementAnswers _a = widget.answers;
  late bool _na =
      widget.answers.statusOf(widget.question).state ==
      QuestionState.notApplicable;
  late final _reason = TextEditingController(
    text: widget.answers.statusOf(widget.question).reason,
  );
  var _seq = 0;

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  String _newId(String prefix) =>
      '$prefix${DateTime.now().microsecondsSinceEpoch}${_seq++}';

  /// «Tegishli emas» sheriklikda foyda va zarar savollari uchun taqiq
  /// (SPEC 2E.1): bu savollar doim javob talab qiladi.
  bool get _canBeNotApplicable =>
      !(widget.type == AgreementType.partnership &&
          (widget.question == AgreementQuestion.profitRule ||
              widget.question == AgreementQuestion.lossRule));

  void _save() {
    final q = widget.question;
    final status = _na
        ? QuestionStatus(QuestionState.notApplicable, _reason.text.trim())
        : QuestionStatus.answered;
    Navigator.pop(context, _a.mark(q, status));
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final q = widget.question;
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.agQuestionTitle(q.number, agQuestion(l10n, q))),
        actions: [
          TextButton(
            key: const Key('ag-q-save'),
            onPressed: _na && _reason.text.trim().isEmpty ? null : _save,
            child: Text(l10n.save),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          Text(agQuestionHint(l10n, q)),
          const SizedBox(height: 8),
          if (_canBeNotApplicable)
            SwitchListTile(
              key: const Key('ag-q-na'),
              contentPadding: EdgeInsets.zero,
              title: Text(l10n.agNotApplicable),
              value: _na,
              onChanged: (v) => setState(() => _na = v),
            ),
          if (_na)
            TextField(
              key: const Key('ag-q-reason'),
              controller: _reason,
              decoration: InputDecoration(labelText: l10n.agNaReason),
              onChanged: (_) => setState(() {}),
            )
          else
            ..._body(context),
        ],
      ),
    );
  }

  List<Widget> _body(BuildContext context) => switch (widget.question) {
    AgreementQuestion.parties => _parties(context),
    AgreementQuestion.contributions => _contributions(context),
    AgreementQuestion.duties => _duties(context),
    AgreementQuestion.profitRule => _profit(context),
    AgreementQuestion.lossRule => _loss(context),
    AgreementQuestion.custody => _custody(context),
    AgreementQuestion.exitClause => _exit(context),
    AgreementQuestion.arbiter => _arbiter(context),
    AgreementQuestion.term => _term(context),
  };

  Widget _field({
    required Key key,
    required String label,
    required String value,
    required ValueChanged<String> onChanged,
    int maxLines = 1,
    TextInputType? keyboardType,
  }) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: TextFormField(
      key: key,
      initialValue: value,
      maxLines: maxLines,
      keyboardType: keyboardType,
      inputFormatters: keyboardType == TextInputType.number
          ? [FilteringTextInputFormatter.digitsOnly]
          : null,
      decoration: InputDecoration(labelText: label),
      onChanged: onChanged,
    ),
  );

  Widget _partyDropdown({
    required Key key,
    required String label,
    required String? value,
    required ValueChanged<String?> onChanged,
  }) {
    final ids = {for (final p in _a.parties) p.id};
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: DropdownButtonFormField<String>(
        key: key,
        value: ids.contains(value) ? value : null,
        decoration: InputDecoration(labelText: label),
        items: [
          for (final p in _a.parties)
            DropdownMenuItem(
              value: p.id,
              child: Text(p.name.isEmpty ? '—' : p.name),
            ),
        ],
        onChanged: onChanged,
      ),
    );
  }

  // 1. Kim bilan kim?
  List<Widget> _parties(BuildContext context) {
    final l10n = context.l10n;
    return [
      for (final (i, p) in _a.parties.indexed)
        Card(
          key: ValueKey(p.id),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: [
                _field(
                  key: Key('ag-party-name-$i'),
                  label: l10n.agPartyName,
                  value: p.name,
                  onChanged: (v) => _setParty(i, name: v),
                ),
                _field(
                  key: Key('ag-party-role-$i'),
                  label: l10n.agPartyRole,
                  value: p.role,
                  onChanged: (v) => _setParty(i, role: v),
                ),
                _field(
                  key: Key('ag-party-relation-$i'),
                  label: l10n.agPartyRelation,
                  value: p.relation,
                  onChanged: (v) => _setParty(i, relation: v),
                ),
                if (_a.parties.length > 2)
                  Align(
                    alignment: Alignment.centerRight,
                    child: IconButton(
                      tooltip: l10n.obMemberRemove,
                      icon: const Icon(Icons.close),
                      onPressed: () => setState(
                        () => _a = _a.copyWith(
                          parties: [..._a.parties]..removeAt(i),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      TextButton.icon(
        key: const Key('ag-party-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.agPartyAdd),
        onPressed: () => setState(
          () => _a = _a.copyWith(
            parties: [
              ..._a.parties,
              AgreementParty(id: _newId('p'), name: ''),
            ],
          ),
        ),
      ),
    ];
  }

  void _setParty(int i, {String? name, String? role, String? relation}) {
    final p = _a.parties[i];
    final list = [..._a.parties];
    list[i] = AgreementParty(
      id: p.id,
      name: name ?? p.name,
      role: role ?? p.role,
      relation: relation ?? p.relation,
      isMe: p.isMe,
    );
    _a = _a.copyWith(parties: list);
  }

  // 2. Kim nima qo'shyapti?
  List<Widget> _contributions(BuildContext context) {
    final l10n = context.l10n;
    return [
      for (final (i, c) in _a.contributions.indexed)
        Card(
          key: ValueKey('c$i${c.partyId}'),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: [
                _partyDropdown(
                  key: Key('ag-contrib-party-$i'),
                  label: l10n.agWho,
                  value: c.partyId,
                  onChanged: (v) => _setContribution(i, partyId: v),
                ),
                DropdownButtonFormField<ContributionKind>(
                  key: Key('ag-contrib-kind-$i'),
                  value: c.kind,
                  decoration: InputDecoration(labelText: l10n.agContribKind),
                  items: [
                    for (final k in ContributionKind.values)
                      DropdownMenuItem(
                        value: k,
                        child: Text(agContributionKind(l10n, k)),
                      ),
                  ],
                  onChanged: (k) =>
                      setState(() => _setContribution(i, kind: k)),
                ),
                _field(
                  key: Key('ag-contrib-amount-$i'),
                  label: l10n.agAmountSom,
                  value: c.amount == null
                      ? ''
                      : c.amount!.wholeMajor.toString(),
                  keyboardType: TextInputType.number,
                  onChanged: (v) => _setContribution(
                    i,
                    amount: int.tryParse(v),
                    clearAmount: v.trim().isEmpty,
                  ),
                ),
                _field(
                  key: Key('ag-contrib-desc-$i'),
                  label: l10n.agDescription,
                  value: c.description,
                  onChanged: (v) => _setContribution(i, description: v),
                ),
                Align(
                  alignment: Alignment.centerRight,
                  child: IconButton(
                    tooltip: l10n.obMemberRemove,
                    icon: const Icon(Icons.close),
                    onPressed: () => setState(
                      () => _a = _a.copyWith(
                        contributions: [..._a.contributions]..removeAt(i),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      TextButton.icon(
        key: const Key('ag-contrib-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.agContribAdd),
        onPressed: _a.parties.isEmpty
            ? null
            : () => setState(
                () => _a = _a.copyWith(
                  contributions: [
                    ..._a.contributions,
                    AgreementContribution(
                      partyId: _a.parties.first.id,
                      kind: ContributionKind.money,
                    ),
                  ],
                ),
              ),
      ),
    ];
  }

  void _setContribution(
    int i, {
    String? partyId,
    ContributionKind? kind,
    int? amount,
    bool clearAmount = false,
    String? description,
  }) {
    final c = _a.contributions[i];
    final list = [..._a.contributions];
    list[i] = AgreementContribution(
      partyId: partyId ?? c.partyId,
      kind: kind ?? c.kind,
      amount: clearAmount
          ? null
          : amount != null
          ? Money.major(amount, widget.currency)
          : c.amount,
      description: description ?? c.description,
    );
    _a = _a.copyWith(contributions: list);
  }

  // 3. Kim nima qiladi?
  List<Widget> _duties(BuildContext context) {
    final l10n = context.l10n;
    return [
      Text(
        l10n.agDutyHint,
        style: Theme.of(context).textTheme.bodySmall,
      ),
      for (final (i, d) in _a.duties.indexed)
        Card(
          key: ValueKey(d.id),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: [
                _field(
                  key: Key('ag-duty-title-$i'),
                  label: l10n.agDutyTitle,
                  value: d.title,
                  onChanged: (v) => _setDuty(i, title: v),
                ),
                _partyDropdown(
                  key: Key('ag-duty-owner-$i'),
                  label: l10n.agDutyOwner,
                  value: d.ownerPartyId,
                  onChanged: (v) => setState(() => _setDuty(i, owner: v)),
                ),
                _field(
                  key: Key('ag-duty-breach-$i'),
                  label: l10n.agDutyBreach,
                  value: d.breachClause,
                  maxLines: 2,
                  onChanged: (v) => _setDuty(i, breach: v),
                ),
                Align(
                  alignment: Alignment.centerRight,
                  child: IconButton(
                    tooltip: l10n.obMemberRemove,
                    icon: const Icon(Icons.close),
                    onPressed: () => setState(
                      () => _a = _a.copyWith(
                        duties: [..._a.duties]..removeAt(i),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      TextButton.icon(
        key: const Key('ag-duty-add'),
        icon: const Icon(Icons.add),
        label: Text(l10n.agDutyAdd),
        onPressed: () => setState(
          () => _a = _a.copyWith(
            duties: [
              ..._a.duties,
              AgreementDuty(id: _newId('d'), title: ''),
            ],
          ),
        ),
      ),
    ];
  }

  void _setDuty(int i, {String? title, String? owner, String? breach}) {
    final d = _a.duties[i];
    final list = [..._a.duties];
    list[i] = AgreementDuty(
      id: d.id,
      title: title ?? d.title,
      ownerPartyId: owner ?? d.ownerPartyId,
      breachClause: breach ?? d.breachClause,
    );
    _a = _a.copyWith(duties: list);
  }

  // 4. Foyda qanday bo'linadi? (faqat foiz)
  List<Widget> _profit(BuildContext context) {
    final l10n = context.l10n;
    final p = _a.profit;
    return [
      Text(l10n.agProfitHint, style: Theme.of(context).textTheme.bodySmall),
      for (final (i, party) in _a.parties.indexed)
        _field(
          key: Key('ag-profit-$i'),
          label: l10n.agProfitShare(party.name),
          value: p.shares[party.id] == null
              ? ''
              : percentLabel(p.shares[party.id]!),
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          onChanged: (v) {
            final bp = parsePercentBp(v);
            // Joriy holatdan: build vaqtidagi `p` eskirgan bo'lishi mumkin —
            // bitta sessiyada ikki ulush kiritilsa, birinchisi yo'qolmasin.
            final shares = {..._a.profit.shares};
            if (bp == null) {
              shares.remove(party.id);
            } else {
              shares[party.id] = bp;
            }
            _a = _a.copyWith(
              profit: ProfitRule(shares: shares, text: _a.profit.text),
            );
          },
        ),
      if (widget.type != AgreementType.partnership)
        _field(
          key: const Key('ag-profit-text'),
          label: l10n.agProfitText,
          value: p.text,
          maxLines: 2,
          onChanged: (v) => _a = _a.copyWith(
            profit: ProfitRule(shares: _a.profit.shares, text: v),
          ),
        ),
    ];
  }

  // 5. Zarar ko'rilsa nima bo'ladi?
  List<Widget> _loss(BuildContext context) => [
    _field(
      key: const Key('ag-loss'),
      label: context.l10n.agLossText,
      value: _a.lossText,
      maxLines: 3,
      onChanged: (v) => _a = _a.copyWith(lossText: v),
    ),
  ];

  // 6. Pul qayerda, hisobni kim yuritadi, qachon ko'riladi?
  List<Widget> _custody(BuildContext context) {
    final l10n = context.l10n;
    final c = _a.custody;
    // Joriy holatdan o'qiladi: matn maydoni setState chaqirmaydi, shuning uchun
    // build vaqtidagi `c` eskirgan bo'lishi mumkin — yozilgan matn yo'qolmasin.
    CustodyRule next({String? where, String? keeper, int? every}) {
      final cur = _a.custody;
      return CustodyRule(
        where: where ?? cur.where,
        keeperPartyId: keeper ?? cur.keeperPartyId,
        keeperDeviceId: cur.keeperDeviceId,
        reviewEveryDays: every ?? cur.reviewEveryDays,
      );
    }

    return [
      _field(
        key: const Key('ag-custody-where'),
        label: l10n.agCustodyWhere,
        value: c.where,
        onChanged: (v) => _a = _a.copyWith(custody: next(where: v)),
      ),
      _partyDropdown(
        key: const Key('ag-custody-keeper'),
        label: l10n.agCustodyKeeper,
        value: c.keeperPartyId,
        onChanged: (v) =>
            setState(() => _a = _a.copyWith(custody: next(keeper: v))),
      ),
      DropdownButtonFormField<int>(
        key: const Key('ag-custody-every'),
        value: const [7, 14, 30, 90, 365].contains(c.reviewEveryDays)
            ? c.reviewEveryDays
            : 30,
        decoration: InputDecoration(labelText: l10n.agCustodyEvery),
        items: [
          for (final d in const [7, 14, 30, 90, 365])
            DropdownMenuItem(value: d, child: Text(agReviewEvery(l10n, d))),
        ],
        onChanged: (d) =>
            setState(() => _a = _a.copyWith(custody: next(every: d))),
      ),
      if (c.reviewEveryDays > 31)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(
            l10n.agReviewTooRare,
            key: const Key('ag-review-rare'),
            style: TextStyle(color: Theme.of(context).colorScheme.tertiary),
          ),
        ),
    ];
  }

  // 7. Qanday ajralib chiqiladi?
  List<Widget> _exit(BuildContext context) {
    final l10n = context.l10n;
    final e = _a.exit;
    // Joriy holatdan o'qiladi (qarang: _custody) — bitta sessiyada bir nechta
    // maydon yozilganda oldingilari o'chib ketmasin. Bo'sh raqam — «yo'q».
    ExitClause next({
      int? notice,
      bool clearNotice = false,
      String? valuation,
      String? payout,
      String? assets,
    }) {
      final cur = _a.exit;
      return ExitClause(
        noticeDays: clearNotice ? null : (notice ?? cur.noticeDays),
        valuation: valuation ?? cur.valuation,
        payout: payout ?? cur.payout,
        assets: assets ?? cur.assets,
      );
    }

    return [
      _field(
        key: const Key('ag-exit-notice'),
        label: l10n.agExitNotice,
        value: e.noticeDays?.toString() ?? '',
        keyboardType: TextInputType.number,
        onChanged: (v) => _a = _a.copyWith(
          exit: next(notice: int.tryParse(v), clearNotice: v.trim().isEmpty),
        ),
      ),
      _field(
        key: const Key('ag-exit-valuation'),
        label: l10n.agExitValuation,
        value: e.valuation,
        maxLines: 2,
        onChanged: (v) => _a = _a.copyWith(exit: next(valuation: v)),
      ),
      _field(
        key: const Key('ag-exit-payout'),
        label: l10n.agExitPayout,
        value: e.payout,
        maxLines: 2,
        onChanged: (v) => _a = _a.copyWith(exit: next(payout: v)),
      ),
      _field(
        key: const Key('ag-exit-assets'),
        label: l10n.agExitAssets,
        value: e.assets,
        maxLines: 2,
        onChanged: (v) => _a = _a.copyWith(exit: next(assets: v)),
      ),
    ];
  }

  // 8. Kelisha olmasangiz, kim hakam?
  List<Widget> _arbiter(BuildContext context) {
    final l10n = context.l10n;
    final ar = _a.arbiter ?? const ArbiterInfo(name: '');
    return [
      Text(l10n.agArbiterHint, style: Theme.of(context).textTheme.bodySmall),
      _field(
        key: const Key('ag-arbiter-name'),
        label: l10n.agArbiterName,
        value: ar.name,
        onChanged: (v) => _a = _a.copyWith(
          arbiter: ArbiterInfo(name: v, role: _a.arbiter?.role ?? ''),
        ),
      ),
      _field(
        key: const Key('ag-arbiter-role'),
        label: l10n.agArbiterRole,
        value: ar.role,
        onChanged: (v) => _a = _a.copyWith(
          arbiter: ArbiterInfo(name: _a.arbiter?.name ?? '', role: v),
        ),
      ),
      _field(
        key: const Key('ag-witnesses'),
        label: l10n.agWitnesses,
        value: _a.witnesses.join(', '),
        onChanged: (v) => _a = _a.copyWith(
          witnesses: [
            for (final w in v.split(','))
              if (w.trim().isNotEmpty) w.trim(),
          ],
        ),
      ),
    ];
  }

  // 9. Qachon yangilanadi?
  List<Widget> _term(BuildContext context) {
    final l10n = context.l10n;
    final t = _a.term;
    return [
      _field(
        key: const Key('ag-term-months'),
        label: l10n.agTermMonths,
        value: t.termMonths?.toString() ?? '',
        keyboardType: TextInputType.number,
        onChanged: (v) => _a = _a.copyWith(
          term: TermRule(
            termMonths: int.tryParse(v),
            reviewDate: _a.term.reviewDate,
          ),
        ),
      ),
      ListTile(
        key: const Key('ag-term-review'),
        contentPadding: EdgeInsets.zero,
        title: Text(l10n.agReviewDate),
        subtitle: Text(t.reviewDate == null ? '—' : formatDate(t.reviewDate!)),
        trailing: const Icon(Icons.event),
        onTap: () async {
          final now = DateTime.now();
          final r = t.reviewDate;
          final picked = await showDatePicker(
            context: context,
            initialDate: r == null
                ? DateTime(now.year + 1, now.month, now.day)
                : DateTime(r.year, r.month, r.day),
            firstDate: DateTime(now.year - 1),
            lastDate: DateTime(now.year + 30),
          );
          if (picked == null) return;
          setState(
            () => _a = _a.copyWith(
              term: TermRule(
                termMonths: _a.term.termMonths,
                reviewDate: LocalDate(picked.year, picked.month, picked.day),
              ),
            ),
          );
        },
      ),
    ];
  }
}

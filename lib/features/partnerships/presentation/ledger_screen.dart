import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/app/refresh.dart';
import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/app/widgets/labels.dart';
import 'package:baraka_daftari/app/widgets/money_input.dart';
import 'package:baraka_daftari/app/widgets/paged_list.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/logging/app_log.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/pdf/baraka_pdf.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_providers.dart';
import 'package:baraka_daftari/features/agreements/domain/accountability.dart';
import 'package:baraka_daftari/features/agreements/presentation/agreement_labels.dart';
import 'package:baraka_daftari/features/partnerships/data/partnership_providers.dart';
import 'package:baraka_daftari/features/partnerships/domain/venture_service.dart';
import 'package:baraka_daftari/features/partnerships/presentation/partnership_wizard_screen.dart';
import 'package:baraka_daftari/features/partnerships/presentation/profit_spike_dialog.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:share_plus/share_plus.dart';

String entryKindLabel(BuildContext context, VentureEntryKind k) {
  final l10n = context.l10n;
  return switch (k) {
    VentureEntryKind.income => l10n.ledgerKindIncome,
    VentureEntryKind.expense => l10n.ledgerKindExpense,
    VentureEntryKind.forceMajeure => l10n.ledgerKindForce,
    VentureEntryKind.correction => l10n.ledgerKindCorrection,
  };
}

/// Sheriklik kassa daftari (SPEC 2E.3): kirim, xarajat, fors-major,
/// davrni yopish va taqsimot, sherikka hisobot.
class LedgerScreen extends ConsumerWidget {
  const LedgerScreen({required this.partnershipId, super.key});

  final String partnershipId;

  void _refresh(WidgetRef ref) {
    ref
      ..invalidate(ledgerViewProvider(partnershipId))
      ..invalidate(partnershipViewProvider(partnershipId));
    refreshMoneyViews(ref);
  }

  String _error(BuildContext context, String code) {
    final l10n = context.l10n;
    return switch (code) {
      VentureLedgerService.errPeriodClosed => l10n.ledgerLocked,
      VentureLedgerService.errReadOnly => l10n.ledgerReadOnly,
      AccountabilityErrors.inDispute ||
      AccountabilityErrors.reviewOpen ||
      AccountabilityErrors.reviewLocked ||
      AccountabilityErrors.spikeAckRequired => agError(l10n, code),
      _ => partnershipError(context, code),
    };
  }

  Future<void> _add(BuildContext context, WidgetRef ref, LedgerView v) async {
    final messenger = ScaffoldMessenger.of(context);
    final draft = await showDialog<_EntryDraft>(
      context: context,
      builder: (_) => const _EntryDialog(),
    );
    if (draft == null || !context.mounted) return;
    final amount = await showAmountSheet(
      context,
      currency: v.currency,
      title: entryKindLabel(context, draft.kind),
    );
    if (amount == null || !amount.isPositive || !context.mounted) return;
    try {
      await (await ref.read(ventureLedgerServiceProvider.future)).addEntry(
        v.partnership.partnership,
        kind: draft.kind,
        title: draft.title,
        amount: draft.minus ? -amount : amount,
        note: draft.note,
        receiptImage: draft.image,
      );
    } on DomainRuleException catch (e) {
      AppLog.event('ledger_rejected_${e.code}');
      if (context.mounted) {
        messenger.showSnackBar(
          SnackBar(content: Text(_error(context, e.code))),
        );
      }
    }
    _refresh(ref);
  }

  Future<void> _close(
    BuildContext context,
    WidgetRef ref,
    LedgerView v,
  ) async {
    final l10n = context.l10n;
    final messenger = ScaffoldMessenger.of(context);
    final money = context.money;
    final loss = v.openNet.isNegative;
    final mudaraba = v.partnership.partnership.type == PartnershipType.mudaraba;
    final pv = v.partnership.partnership;
    // «Katta foyda» tasdig'i taqsimotdan oldin (SPEC 2F.7).
    final check = await (await ref.read(
      ventureLedgerServiceProvider.future,
    )).spikeCheck(pv);
    if (check.blocks) {
      if (!context.mounted) return;
      final outcome = await showDialog<ProfitSpikeOutcome>(
        context: context,
        builder: (_) =>
            ProfitSpikeDialog(partnershipId: pv.meta.id, initial: check),
      );
      if (outcome == null || !context.mounted) return;
      if (outcome == ProfitSpikeOutcome.review) {
        final a = await (await ref.read(
          agreementServiceProvider.future,
        )).bySource(AgreementSource.partnership, pv.meta.id);
        if (a != null && context.mounted) {
          await context.push(AppRoutes.agreementReview(a.meta.id));
        }
        _refresh(ref);
        return;
      }
    }
    if (!context.mounted) return;
    final answer = await showDialog<(bool, String?)>(
      context: context,
      builder: (_) => _CloseDialog(askNegligence: loss && mudaraba),
    );
    if (answer == null || !context.mounted) return;
    try {
      final closed =
          await (await ref.read(
            ventureLedgerServiceProvider.future,
          )).closePeriod(
            pv,
            negligence: answer.$1,
            negligenceNote: answer.$2,
          );
      final me = v.partnership.me;
      final mine = me == null
          ? null
          : closed.shares
                .where((s) => s.partnerId == me.meta.id)
                .firstOrNull
                ?.amount;
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            mine != null && mine.isPositive
                ? l10n.ledgerClosedSnack(money(mine))
                : l10n.ledgerClosedPlain,
          ),
        ),
      );
    } on DomainRuleException catch (e) {
      AppLog.event('ledger_close_rejected_${e.code}');
      if (context.mounted) {
        messenger.showSnackBar(
          SnackBar(content: Text(_error(context, e.code))),
        );
      }
    }
    _refresh(ref);
  }

  Future<void> _report(
    BuildContext context,
    LedgerView v,
    ClosedPeriod c,
  ) async {
    final l10n = context.l10n;
    final money = context.money;
    final messenger = ScaffoldMessenger.of(context);
    final pv = v.partnership;
    final p = c.period;
    final entries = [
      for (final e in v.entries)
        if (!e.occurredOn.isBefore(p.startDate) &&
            !e.occurredOn.isAfter(p.endDate))
          e,
    ];
    String name(String id) =>
        pv.partners.where((x) => x.meta.id == id).firstOrNull?.name ?? '—';
    // Async'dan oldin — kontekstdan olinadigan matnlar.
    final kinds = {
      for (final k in VentureEntryKind.values) k: entryKindLabel(context, k),
    };
    final range = l10n.ledgerPeriod(
      formatDate(p.startDate),
      formatDate(p.endDate),
    );
    try {
      final bytes = await BarakaPdf.build(
        fonts: await PdfFonts.load(rootBundle),
        title: l10n.ledgerReportTitle,
        subtitle: '${pv.partnership.title} · $range',
        footer: l10n.appTitle,
        blocks: [
          PdfKeyValues([
            (l10n.ledgerKindIncome, money(p.income)),
            (l10n.ledgerKindExpense, money(p.expense)),
            (
              p.net.isNegative ? l10n.ledgerLossLabel : l10n.ledgerNetLabel,
              money(p.net),
            ),
            if (p.buyout.isPositive) (l10n.ledgerBuyoutLabel, money(p.buyout)),
            (l10n.ledgerReportBuyout, money(pv.buyoutRemaining)),
          ]),
          PdfHeading(l10n.ledgerReportDistribution),
          PdfTable(
            headers: [l10n.pnPdfName, l10n.pnPdfShare, l10n.pnBuyoutTitle],
            rows: [
              for (final s in c.shares)
                [name(s.partnerId), money(s.amount), money(s.buyout)],
            ],
            numericColumns: const {1, 2},
          ),
          PdfHeading(l10n.ledgerReportEntries),
          PdfTable(
            headers: [
              l10n.receiptPdfDate,
              l10n.pnPdfType,
              l10n.titleLabel,
              l10n.lineAmountTitle,
            ],
            rows: [
              for (final e in entries)
                [
                  formatDate(e.occurredOn),
                  kinds[e.kind]!,
                  e.title,
                  money(e.effect),
                ],
            ],
            numericColumns: const {3},
          ),
          PdfNote(l10n.ledgerReportNote),
        ],
      );
      await SharePlus.instance.share(
        ShareParams(
          files: [
            XFile.fromData(
              bytes,
              mimeType: 'application/pdf',
              name: 'sheriklik_hisoboti.pdf',
            ),
          ],
          fileNameOverrides: const ['sheriklik_hisoboti.pdf'],
          subject: l10n.ledgerReportTitle,
        ),
      );
    } on Object {
      AppLog.event('ledger_report_failed');
      messenger.showSnackBar(SnackBar(content: Text(l10n.genericError)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final theme = Theme.of(context);
    final money = context.money;
    final view = ref.watch(ledgerViewProvider(partnershipId));
    return Scaffold(
      appBar: AppBar(title: Text(l10n.ledgerTitle)),
      floatingActionButton: switch (view) {
        AsyncData(:final value?) when !value.readOnly =>
          FloatingActionButton.extended(
            key: const Key('ledger-add'),
            icon: const Icon(Icons.add),
            label: Text(l10n.ledgerAdd),
            onPressed: () => _add(context, ref, value),
          ),
        _ => null,
      },
      body: switch (view) {
        AsyncData(:final value?) => () {
          final v = value;
          final names = {
            for (final x in v.partnership.partners) x.meta.id: x.name,
          };
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
            children: [
              Text(
                v.partnership.partnership.title,
                style: theme.textTheme.titleLarge,
              ),
              Text(l10n.ledgerHint, style: theme.textTheme.bodySmall),
              if (v.readOnly)
                Card(
                  key: const Key('ledger-read-only'),
                  color: theme.colorScheme.secondaryContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text(l10n.ledgerReadOnly),
                  ),
                ),
              const SizedBox(height: 8),
              Card(
                key: const Key('ledger-summary'),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        // Davr bugun yopilgan bo'lsa, keyingisi ertadan.
                        v.openStart.isAfter(v.today)
                            ? l10n.ledgerNextPeriod(formatDate(v.openStart))
                            : l10n.ledgerOpenPeriod(formatDate(v.openStart)),
                        style: theme.textTheme.titleSmall,
                      ),
                      Text(l10n.ledgerIncome(money(v.openIncome))),
                      Text(l10n.ledgerExpense(money(v.openExpense))),
                      Text(
                        v.openNet.isNegative
                            ? l10n.ledgerLoss(money(-v.openNet))
                            : l10n.ledgerNet(money(v.openNet)),
                        key: const Key('ledger-net'),
                        style: theme.textTheme.titleMedium?.copyWith(
                          color: v.openNet.isNegative
                              ? theme.colorScheme.error
                              : theme.colorScheme.primary,
                        ),
                      ),
                      if (!v.readOnly && v.openEntries.isNotEmpty)
                        Align(
                          alignment: Alignment.centerRight,
                          child: FilledButton.tonal(
                            key: const Key('ledger-close'),
                            onPressed: () => _close(context, ref, v),
                            child: Text(l10n.ledgerClose),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              if (v.entries.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Text(l10n.ledgerEmpty),
                ),
              PagedList(
                count: v.entries.length,
                itemBuilder: (context, i) {
                  final e = v.entries[i];
                  return ListTile(
                    key: Key('ledger-entry-${e.meta.id}'),
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(
                      switch (e.kind) {
                        VentureEntryKind.income => Icons.south_west,
                        VentureEntryKind.expense => Icons.north_east,
                        VentureEntryKind.forceMajeure => Icons.warning_amber,
                        VentureEntryKind.correction => Icons.edit_note,
                      },
                      color: e.effect.isNegative
                          ? theme.colorScheme.error
                          : null,
                    ),
                    title: Text(e.title),
                    subtitle: Text(
                      [
                        formatDate(e.occurredOn),
                        entryKindLabel(context, e.kind),
                        if (e.receiptImage != null) l10n.ledgerAttached,
                        if (v.isLocked(e)) l10n.ledgerLocked,
                        if (e.note != null) e.note!,
                      ].join(' · '),
                    ),
                    trailing: Text(money(e.effect)),
                    onTap: e.receiptImage == null
                        ? null
                        : () => showDialog<void>(
                            context: context,
                            builder: (_) => Dialog(
                              child: Image.memory(
                                Uint8List.fromList(e.receiptImage!),
                              ),
                            ),
                          ),
                  );
                },
              ),
              if (v.closed.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(l10n.ledgerClosedTitle, style: theme.textTheme.titleSmall),
                for (final c in v.closed.reversed)
                  Card(
                    key: Key('ledger-period-${c.period.meta.id}'),
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 12, 8, 4),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            l10n.ledgerPeriod(
                              formatDate(c.period.startDate),
                              formatDate(c.period.endDate),
                            ),
                            style: theme.textTheme.titleSmall,
                          ),
                          Text(
                            c.period.net.isNegative
                                ? l10n.ledgerLoss(money(-c.period.net))
                                : l10n.ledgerNet(money(c.period.net)),
                          ),
                          for (final s in c.shares)
                            Text(
                              l10n.ledgerShareLine(
                                names[s.partnerId] ?? '—',
                                money(s.amount),
                              ),
                            ),
                          if (c.period.buyout.isPositive)
                            Text(l10n.ledgerBuyoutLine(money(c.period.buyout))),
                          Align(
                            alignment: Alignment.centerRight,
                            child: TextButton.icon(
                              key: Key('ledger-report-${c.period.meta.id}'),
                              icon: const Icon(Icons.ios_share),
                              label: Text(l10n.ledgerReport),
                              onPressed: () => _report(context, v, c),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
              const SizedBox(height: 4),
              Text(
                v.partnership.partnership.type == PartnershipType.mudaraba
                    ? l10n.pnLossRuleMudaraba
                    : l10n.pnLossRuleMusharaka(
                        [
                          for (final x in v.partnership.partners)
                            _ratio(
                              x.name,
                              ratioBasisPoints(
                                    v.partnership.capitalOf(x),
                                    v.partnership.totalCapital,
                                  ) ??
                                  0,
                            ),
                        ].join(', '),
                      ),
                style: theme.textTheme.bodySmall,
              ),
            ],
          );
        }(),
        AsyncData() || AsyncError() => Center(child: Text(l10n.genericError)),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }

  static String _ratio(String name, int bp) => '$name ${percentLabel(bp)} %';
}

/// Yangi yozuv qoralamasi.
class _EntryDraft {
  const _EntryDraft({
    required this.kind,
    required this.title,
    this.note,
    this.image,
    this.minus = false,
  });

  final VentureEntryKind kind;
  final String title;
  final String? note;
  final List<int>? image;
  final bool minus;
}

class _EntryDialog extends StatefulWidget {
  const _EntryDialog();

  @override
  State<_EntryDialog> createState() => _EntryDialogState();
}

class _EntryDialogState extends State<_EntryDialog> {
  final _title = TextEditingController();
  final _note = TextEditingController();
  VentureEntryKind _kind = VentureEntryKind.income;
  List<int>? _image;
  bool _minus = true;

  @override
  void dispose() {
    _title.dispose();
    _note.dispose();
    super.dispose();
  }

  Future<void> _pick(ImageSource source) async {
    try {
      final file = await ImagePicker().pickImage(
        source: source,
        maxWidth: 1280,
        imageQuality: 70,
      );
      if (file == null) return;
      final bytes = await file.readAsBytes();
      if (mounted) setState(() => _image = bytes);
    } on Object {
      AppLog.event('ledger_image_failed');
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AlertDialog(
      title: Text(l10n.ledgerAdd),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                for (final k in VentureEntryKind.values)
                  ChoiceChip(
                    key: Key('ledger-kind-${k.name}'),
                    label: Text(entryKindLabel(context, k)),
                    selected: _kind == k,
                    onSelected: (_) => setState(() => _kind = k),
                  ),
              ],
            ),
            TextField(
              key: const Key('ledger-title'),
              controller: _title,
              decoration: InputDecoration(labelText: l10n.ledgerEntryTitle),
              onChanged: (_) => setState(() {}),
            ),
            if (_kind == VentureEntryKind.forceMajeure ||
                _kind == VentureEntryKind.correction)
              TextField(
                key: const Key('ledger-note'),
                controller: _note,
                decoration: InputDecoration(labelText: l10n.ledgerNote),
              ),
            if (_kind == VentureEntryKind.correction)
              SwitchListTile(
                key: const Key('ledger-minus'),
                contentPadding: EdgeInsets.zero,
                title: Text(l10n.ledgerCorrectionMinus),
                value: _minus,
                onChanged: (x) => setState(() => _minus = x),
              ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                OutlinedButton.icon(
                  key: const Key('ledger-photo'),
                  icon: const Icon(Icons.photo_camera_outlined),
                  label: Text(l10n.ledgerAttach),
                  onPressed: () => _pick(ImageSource.camera),
                ),
                IconButton(
                  key: const Key('ledger-gallery'),
                  icon: const Icon(Icons.photo_library_outlined),
                  onPressed: () => _pick(ImageSource.gallery),
                ),
              ],
            ),
            if (_image != null)
              Text(l10n.ledgerAttached, key: const Key('ledger-attached')),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('ledger-entry-ok'),
          onPressed: _title.text.trim().isEmpty
              ? null
              : () => Navigator.pop(
                  context,
                  _EntryDraft(
                    kind: _kind,
                    title: _title.text,
                    note: _note.text,
                    image: _image,
                    minus: _kind == VentureEntryKind.correction && _minus,
                  ),
                ),
          child: Text(l10n.save),
        ),
      ],
    );
  }
}

/// Davrni yopish tasdig'i; mudaraba zararida — beparvolik va izoh.
class _CloseDialog extends StatefulWidget {
  const _CloseDialog({required this.askNegligence});

  final bool askNegligence;

  @override
  State<_CloseDialog> createState() => _CloseDialogState();
}

class _CloseDialogState extends State<_CloseDialog> {
  final _note = TextEditingController();
  bool _negligence = false;

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final blocked = _negligence && _note.text.trim().isEmpty;
    return AlertDialog(
      title: Text(l10n.ledgerClose),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(l10n.ledgerCloseConfirm),
            if (widget.askNegligence) ...[
              SwitchListTile(
                key: const Key('ledger-negligence'),
                contentPadding: EdgeInsets.zero,
                title: Text(l10n.pnNegligence),
                value: _negligence,
                onChanged: (x) => setState(() => _negligence = x),
              ),
              if (_negligence)
                TextField(
                  key: const Key('ledger-negligence-note'),
                  controller: _note,
                  decoration: InputDecoration(
                    labelText: l10n.pnNegligenceNote,
                  ),
                  onChanged: (_) => setState(() {}),
                ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          key: const Key('ledger-close-ok'),
          onPressed: blocked
              ? null
              : () => Navigator.pop(context, (_negligence, _note.text)),
          child: Text(l10n.ledgerClose),
        ),
      ],
    );
  }
}

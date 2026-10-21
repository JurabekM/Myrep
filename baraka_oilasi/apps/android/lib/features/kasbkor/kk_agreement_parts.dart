import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/i18n.dart';
import '../../app/theme.dart';
import '../../core/core.dart';
import '../../shared/files.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';

/// Ogohlantirish matni (sariq), ekran o'quvchi uchun eslatma sifatida.
class KkNote extends StatelessWidget {
  const KkNote(this.text, {this.color, super.key});

  final String text;
  final Color? color;

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    child: Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Text(text, style: TextStyle(color: color ?? context.palette.warn, fontSize: 14)),
    ),
  );
}

/// Chegarali ichki blok (forma).
class KkBox extends StatelessWidget {
  const KkBox({required this.children, this.color, super.key});

  final List<Widget> children;
  final Color? color;

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(top: 8),
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      border: Border.all(color: color ?? context.palette.line),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: children),
  );
}

/// Bir qatorli tugmalar to'plami (bosilgani — to'ldirilgan).
class KkToggleRow<T> extends StatelessWidget {
  const KkToggleRow({required this.options, required this.value, required this.onChanged, this.label, super.key});

  final String? label;
  final List<(T, String)> options;
  final T? value;
  final ValueChanged<T>? onChanged;

  @override
  Widget build(BuildContext context) => SegmentedChoice<T>(
    label: label ?? '',
    options: options,
    value: value,
    onChanged: onChanged ?? (_) {},
  );
}

/// Shablon yurist ko'rigidan o'tmagan bo'lsa — ogohlantirish (BARAKA_OILASI 9, `reviewStatus`).
class TemplateReviewNote extends StatelessWidget {
  const TemplateReviewNote(this.status, {super.key});

  final String? status;

  @override
  Widget build(BuildContext context) {
    if (status != 'PENDING') return const SizedBox.shrink();
    return Card(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: context.palette.warn),
      ),
      child: Padding(padding: const EdgeInsets.all(12), child: KkNote(context.t('kk.agr.reviewPending'))),
    );
  }
}

/// Kelishuv holati: qoralama / imzolangan (versiya) / tugagan; imzolanmagan o'zgarishlar va yetishmayotganlar.
class AgreementStatus extends StatelessWidget {
  const AgreementStatus(this.state, {required this.testKey, super.key});

  final KkAgreementStateDto state;
  final String testKey;

  @override
  Widget build(BuildContext context) {
    final s = state;
    final pal = context.palette;
    final label = switch (s.status) {
      'SIGNED' => context.t('kk.agr.status.SIGNED', {'n': s.signedVersions, 'date': showDate(s.signedOn ?? '')}),
      'ENDED' => context.t('kk.agr.status.ENDED', {'date': showDate(s.endedOn ?? '')}),
      _ => context.t('kk.agr.status.DRAFT'),
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          key: Key(testKey),
          style: TextStyle(color: s.status == 'SIGNED' ? pal.accentText : pal.inkMuted, fontSize: 14),
        ),
        if (s.status != 'ENDED' && s.signedVersions > 0 && s.unsignedChanges)
          KkNote(context.t('kk.agr.unsignedChanges')),
        if (s.missing.isNotEmpty)
          KkNote(
            context.t('kk.agr.missing', {'fields': s.missing.map((m) => context.t('kk.agr.field.$m')).join(', ')}),
          ),
      ],
    );
  }
}

/// Imzolash: qog'oz nusxa imzolangan sana; keyingi versiyada — yangi shartlar qachondan amal qiladi.
class SignForm extends ConsumerStatefulWidget {
  const SignForm({
    required this.spaceId,
    required this.id,
    required this.name,
    required this.state,
    required this.onDone,
    super.key,
  });

  final String spaceId;
  final String id;
  final String name;
  final KkAgreementStateDto state;
  final VoidCallback onDone;

  @override
  ConsumerState<SignForm> createState() => _SignFormState();
}

class _SignFormState extends ConsumerState<SignForm> with ActionState {
  String? _signedOn;
  String? _from;

  Future<void> _save() async {
    final ok = await act(() async {
      await ref
          .read(coreProvider)
          .kkSignAgreement(
            spaceId: widget.spaceId,
            id: widget.id,
            input: KkSignInput(signedOn: _signedOn, effectiveFrom: _from),
          );
      return true;
    });
    if (ok ?? false) widget.onDone();
  }

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    label: context.t('kk.agr.signTitle', {'name': widget.name}),
    child: KkBox(
      children: [
        Hint(context.t('kk.agr.signHint')),
        const SizedBox(height: 12),
        DateField(
          label: context.t('kk.agr.signedOn'),
          value: _signedOn,
          onChanged: (v) => setState(() => _signedOn = v),
        ),
        if (widget.state.signedVersions > 0) ...[
          const SizedBox(height: 12),
          DateField(
            label: context.t('kk.agr.effectiveFrom'),
            value: _from,
            onChanged: (v) => setState(() => _from = v),
          ),
        ],
        ErrorText(error),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: busy ? null : _save, child: Text(context.t('kk.agr.signSave'))),
        ),
      ],
    ),
  );
}

/// Kelishuvni tugatish (ajralish yoki ta'minotni to'xtatish): yozuvlar saqlanadi.
class EndForm extends ConsumerStatefulWidget {
  const EndForm({required this.spaceId, required this.id, required this.name, required this.onDone, super.key});

  final String spaceId;
  final String id;
  final String name;
  final VoidCallback onDone;

  @override
  ConsumerState<EndForm> createState() => _EndFormState();
}

class _EndFormState extends ConsumerState<EndForm> with ActionState {
  String? _on;

  Future<void> _save() async {
    final ok = await act(() async {
      await ref.read(coreProvider).kkEndAgreement(spaceId: widget.spaceId, id: widget.id, endedOn: _on);
      return true;
    });
    if (ok ?? false) widget.onDone();
  }

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    label: context.t('kk.agr.endTitle', {'name': widget.name}),
    child: KkBox(
      children: [
        DateField(label: context.t('kk.agr.endedOn'), value: _on, onChanged: (v) => setState(() => _on = v)),
        ErrorText(error),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: busy ? null : _save, child: Text(context.t('kk.agr.endSave'))),
        ),
      ],
    ),
  );
}

/// PDF va o'chirish tugmalari (o'chirish — faqat imzolanmagan kelishuvda). PDF ulashish oynasi orqali.
class AgreementFileActions extends ConsumerStatefulWidget {
  const AgreementFileActions({
    required this.spaceId,
    required this.id,
    required this.name,
    required this.state,
    super.key,
  });

  final String spaceId;
  final String id;
  final String name;
  final KkAgreementStateDto state;

  @override
  ConsumerState<AgreementFileActions> createState() => _AgreementFileActionsState();
}

class _AgreementFileActionsState extends ConsumerState<AgreementFileActions> with ActionState {
  bool _saved = false;

  Future<void> _pdf() async {
    final ok = await act(() async {
      final bytes = await ref.read(coreProvider).kkAgreementPdf(spaceId: widget.spaceId, id: widget.id);
      await ref.read(shareFileProvider)(bytes, 'kelishuv.pdf', pdfMime);
      return true;
    });
    if (ok ?? false) setState(() => _saved = true);
  }

  Future<void> _delete() => act(() => ref.read(coreProvider).kkDeleteAgreement(spaceId: widget.spaceId, id: widget.id));

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Wrap(
        spacing: 8,
        runSpacing: 8,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          Semantics(
            label: context.t('kk.agr.pdfNamed', {'name': widget.name}),
            child: OutlinedButton(onPressed: busy ? null : _pdf, child: Text(context.t('kk.agr.pdf'))),
          ),
          if (widget.state.signedVersions == 0)
            Semantics(
              label: context.t('kk.agr.deleteNamed', {'name': widget.name}),
              child: TextButton(onPressed: busy ? null : _delete, child: Text(context.t('kk.agr.delete'))),
            ),
          if (_saved) Semantics(liveRegion: true, child: Hint(context.t('kk.agr.pdfSaved'))),
        ],
      ),
      ErrorText(error),
    ],
  );
}

/// Telefon va uni saqlashga rozilik (OQ-Y3): rozilik belgilanmasa, yadro telefonni qabul qilmaydi.
class PhoneFields extends StatelessWidget {
  const PhoneFields({
    required this.phone,
    required this.consent,
    required this.onConsent,
    super.key,
  });

  final TextEditingController phone;
  final bool consent;
  final ValueChanged<bool> onConsent;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Field(label: context.t('kk.agr.phone'), controller: phone, keyboardType: TextInputType.phone),
      CheckboxListTile(
        contentPadding: EdgeInsets.zero,
        controlAffinity: ListTileControlAffinity.leading,
        value: consent,
        title: Text(context.t('kk.agr.phoneConsent')),
        onChanged: (v) => onConsent(v ?? false),
      ),
    ],
  );
}

/// Bo'sh matn → `null` (ixtiyoriy maydonlar).
String? kkOpt(String v) => v.trim().isEmpty ? null : v.trim();

/// Kartadagi amal tugmasi: ochiq formaga mos tugma to'ldirilgan ko'rinadi.
class KkActionButton extends StatelessWidget {
  const KkActionButton({required this.label, required this.active, required this.onPressed, super.key});

  final String label;
  final bool active;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) => active
      ? FilledButton(onPressed: onPressed, child: Text(label))
      : OutlinedButton(onPressed: onPressed, child: Text(label));
}

/// Ochiladigan tarix bo'limi (desktop'dagi `<details>`).
class KkDetails extends StatefulWidget {
  const KkDetails({required this.summary, required this.children, super.key});

  final String summary;
  final List<Widget> children;

  @override
  State<KkDetails> createState() => _KkDetailsState();
}

class _KkDetailsState extends State<KkDetails> {
  bool _open = false;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Semantics(
        button: true,
        expanded: _open,
        child: InkWell(
          onTap: () => setState(() => _open = !_open),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 10),
            child: Row(
              children: [
                Icon(_open ? Icons.expand_less : Icons.expand_more, color: context.palette.inkMuted),
                const SizedBox(width: 4),
                Expanded(child: Hint(widget.summary)),
              ],
            ),
          ),
        ),
      ),
      if (_open) ...widget.children,
    ],
  );
}

/// Tarix qatori: chapda sana va tur, o'ngda summa, ostida izoh.
class KkHistoryRow extends StatelessWidget {
  const KkHistoryRow({required this.title, required this.value, this.note, super.key});

  final String title;
  final String value;
  final String? note;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(vertical: 6),
    decoration: BoxDecoration(
      border: Border(top: BorderSide(color: context.palette.line)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: Text(title)),
            const SizedBox(width: 8),
            Text(value, style: const TextStyle(fontFeatures: [FontFeature.tabularFigures()])),
          ],
        ),
        if (note != null && note!.isNotEmpty) Hint(note!),
      ],
    ),
  );
}

/// Ogohlantirish chegarali karta (muddati o'tgan, muzlagan va h.k.).
ShapeBorder? kkWarnShape(BuildContext context, {required bool warn}) => warn
    ? RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: context.palette.warn),
      )
    : null;

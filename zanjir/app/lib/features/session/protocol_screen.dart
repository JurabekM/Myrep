import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:zanjir_data/zanjir_data.dart';

import '../../core/config.dart';
import '../../core/providers.dart';
import '../../l10n/gen/app_localizations.dart';
import '../../l10n/labels.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/disclaimer_banner.dart';
import '../../widgets/text_prompt.dart';

/// Saqlangan hujjat (payload + PDF) va uning tekshiruv natijasi.
final protocolDocumentProvider = FutureProvider.family<ProtocolDocumentRow?, String>(
  (ref, id) async => (await ref.watch(repositoriesProvider.future)).protocols.document(id),
);

final protocolVerifyProvider = FutureProvider.family<String?, String>(
  (ref, id) async => (await ref.watch(repositoriesProvider.future)).protocols.verify(id),
);

/// Sessiya protokoli: imzolash shartlari, imzolash, imzolangan protokollar (QR, hash, ulashish, bekor qilish).
/// Ekran ochiq turganda ekranshot taqiqlanadi (FLAG_SECURE).
class ProtocolScreen extends ConsumerStatefulWidget {
  const ProtocolScreen({super.key, required this.sessionId});
  final String sessionId;

  @override
  ConsumerState<ProtocolScreen> createState() => _ProtocolScreenState();
}

class _ProtocolScreenState extends ConsumerState<ProtocolScreen> {
  late final _secure = ref.read(secureScreenProvider);

  @override
  void initState() {
    super.initState();
    _secure.enable();
  }

  @override
  void dispose() {
    _secure.disable();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.protocol)),
      body: AsyncView(
        value: ref.watch(sessionProtocolsProvider(widget.sessionId)),
        builder: (protocols) {
          final hasActive = protocols.any((p) => p.$2 == ProtocolStatus.active);
          return ListView(
            padding: const EdgeInsets.only(bottom: 24),
            children: [
              for (final (row, status) in protocols) ProtocolCard(protocol: row, status: status),
              if (!hasActive) _SignPanel(sessionId: widget.sessionId),
            ],
          );
        },
      ),
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}

class _SignPanel extends ConsumerStatefulWidget {
  const _SignPanel({required this.sessionId});
  final String sessionId;

  @override
  ConsumerState<_SignPanel> createState() => _SignPanelState();
}

class _SignPanelState extends ConsumerState<_SignPanel> {
  final _comment = TextEditingController();
  String? _language;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _comment.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _comment.dispose();
    super.dispose();
  }

  /// Izoh shu yerda kiritiladi: `lead_comment_required` izoh yozilgach UI'da yo'qoladi
  /// (imzolashda qoralama izoh bilan qayta tuziladi va shartlar repozitoriyda qayta tekshiriladi).
  List<ProtocolBlocker> _effective(ProtocolDraft d) => [
    for (final b in d.blockers)
      if (!(b.code == 'lead_comment_required' && _comment.text.trim().isNotEmpty)) b,
  ];

  Future<void> _sign(String language) async {
    final l10n = AppLocalizations.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.protocolSignTitle),
        content: Text(l10n.signConfirm),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.cancel)),
          FilledButton(
            key: const Key('protocol.confirmSign'),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(l10n.sign),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    setState(() => _busy = true);
    try {
      final repos = await ref.read(repositoriesProvider.future);
      final fonts = await ref.read(protocolFontsProvider.future);
      final draft = await repos.protocols.prepare(
        sessionId: widget.sessionId,
        language: language,
        leadComment: _comment.text,
        verifyBaseUrl: verifyBaseUrl,
      );
      await repos.protocols.sign(draft, fonts);
      ref.invalidate(sessionProtocolsProvider(widget.sessionId));
      ref.invalidate(protocolDraftProvider(widget.sessionId));
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.protocolSigned)));
    } catch (e) {
      ref.invalidate(protocolDraftProvider(widget.sessionId));
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_signError(l10n, e))));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _signError(AppLocalizations l10n, Object e) {
    if (e is DataRuleException && e.code == 'protocol_blocked') return l10n.blockersTitle;
    return l10n.errorText(e);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final language = _language ?? (Localizations.localeOf(context).languageCode == 'ru' ? 'ru' : 'uz');
    return AsyncView(
      value: ref.watch(protocolDraftProvider(widget.sessionId)),
      builder: (draft) {
        final blockers = _effective(draft);
        final needsReview = ((draft.payload['summary'] as Map?)?['NEEDS_REVIEW'] as int? ?? 0) > 0;
        return Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(l10n.protocolSignTitle, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 12),
              Wrap(
                spacing: 12,
                runSpacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Text(l10n.protocolLanguage),
                  SegmentedButton<String>(
                    segments: [
                      ButtonSegment(value: 'uz', label: Text(l10n.languageUz)),
                      ButtonSegment(value: 'ru', label: Text(l10n.languageRu)),
                    ],
                    selected: {language},
                    onSelectionChanged: (s) => setState(() => _language = s.first),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                key: const Key('protocol.comment'),
                controller: _comment,
                minLines: needsReview ? 3 : 1,
                maxLines: 6,
                decoration: InputDecoration(
                  labelText: l10n.leadComment,
                  helperText: needsReview ? l10n.leadCommentHint : null,
                  helperMaxLines: 3,
                ),
              ),
              const SizedBox(height: 16),
              if (blockers.isEmpty)
                Text(l10n.readyToSign, style: const TextStyle(color: ZanjirColors.success))
              else ...[
                Text(
                  l10n.blockersTitle,
                  style: const TextStyle(color: ZanjirColors.warn, fontWeight: FontWeight.bold),
                ),
                for (final b in blockers)
                  ListTile(
                    key: Key('protocol.blocker.${b.code}'),
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.block, color: ZanjirColors.warn),
                    title: Text(l10n.blockerText(b)),
                  ),
              ],
              const SizedBox(height: 16),
              FilledButton.icon(
                key: const Key('protocol.sign'),
                onPressed: blockers.isEmpty && !_busy ? () => _sign(language) : null,
                icon: _busy
                    ? const SizedBox.square(dimension: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.draw),
                label: Text(l10n.sign),
              ),
            ],
          ),
        );
      },
    );
  }
}

/// Imzolangan protokol: raqam, holat, imzolovchi, QR, hash'lar, tekshiruv, ulashish, bekor qilish (LEAD/ADMIN).
class ProtocolCard extends ConsumerWidget {
  const ProtocolCard({super.key, required this.protocol, required this.status});
  final ProtocolRow protocol;
  final ProtocolStatus status;

  Future<void> _revoke(BuildContext context, WidgetRef ref) async {
    final l10n = AppLocalizations.of(context);
    final reason = await promptText(
      context,
      title: l10n.revokeProtocol,
      label: l10n.revokeReason,
      confirm: l10n.revokeProtocol,
      fieldKey: const Key('protocol.revokeReason'),
    );
    if (reason == null || reason.trim().isEmpty) return;
    try {
      await (await ref.read(repositoriesProvider.future)).protocols.revoke(protocol.id, reason: reason.trim());
      ref.invalidate(sessionProtocolsProvider(protocol.sessionId));
      ref.invalidate(protocolDraftProvider(protocol.sessionId));
    } catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.errorText(e))));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final active = status == ProtocolStatus.active;
    final role = ref.watch(profileProvider).value?.role;
    return Card(
      key: Key('protocol.card.${protocol.id}'),
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      child: AsyncView(
        value: ref.watch(protocolDocumentProvider(protocol.id)),
        builder: (doc) {
          final payload = doc == null
              ? const <String, Object?>{}
              : (jsonDecode(doc.payloadJson) as Map).cast<String, Object?>();
          final verifyUrl = (payload['protocol'] as Map?)?['verify_url'] as String?;
          final signer = (payload['signer'] as Map?)?['full_name'] as String? ?? '';
          final signedAt = (payload['signed_at'] as String?)?.replaceFirst('T', ' ').substring(0, 16) ?? '';
          final verify = ref.watch(protocolVerifyProvider(protocol.id));
          return Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(l10n.protocolNumber(protocol.number), style: Theme.of(context).textTheme.titleMedium),
                    ),
                    Chip(
                      label: Text(active ? l10n.protocolActive : l10n.protocolRevoked),
                      side: BorderSide(color: active ? ZanjirColors.success : ZanjirColors.danger),
                    ),
                  ],
                ),
                Text(l10n.signedByAt(signer, signedAt), style: const TextStyle(color: ZanjirColors.inkMuted)),
                const SizedBox(height: 12),
                if (verifyUrl != null)
                  Center(
                    child: Semantics(
                      label: l10n.verifyUrlLabel,
                      child: Container(
                        color: Colors.white,
                        padding: const EdgeInsets.all(8),
                        child: QrImageView(data: verifyUrl, size: 168, backgroundColor: Colors.white),
                      ),
                    ),
                  ),
                if (verifyUrl != null) SelectableText(verifyUrl, textAlign: TextAlign.center),
                const SizedBox(height: 8),
                _Hash(label: l10n.payloadHash, value: protocol.payloadSha256),
                _Hash(label: l10n.pdfHash, value: protocol.pdfSha256),
                verify.when(
                  data: (reason) => ListTile(
                    key: const Key('protocol.verify'),
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(
                      reason == null ? Icons.verified : Icons.gpp_bad,
                      color: reason == null ? ZanjirColors.success : ZanjirColors.danger,
                    ),
                    title: Text(reason == null ? l10n.verifyOk : l10n.verifyFailed(reason)),
                  ),
                  loading: () => const LinearProgressIndicator(),
                  error: (e, _) => Text(l10n.verifyFailed('$e'), style: const TextStyle(color: ZanjirColors.danger)),
                ),
                if (doc != null)
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      FilledButton.tonalIcon(
                        key: const Key('protocol.share'),
                        onPressed: () => ref.read(pdfActionsProvider).share(doc.pdf, 'ZANJIR-${protocol.number}.pdf'),
                        icon: const Icon(Icons.share),
                        label: Text(l10n.sharePdf),
                      ),
                      OutlinedButton.icon(
                        key: const Key('protocol.print'),
                        onPressed: () => ref.read(pdfActionsProvider).print(doc.pdf, 'ZANJIR-${protocol.number}'),
                        icon: const Icon(Icons.print),
                        label: Text(l10n.printPdf),
                      ),
                      if (active && SettingsRepository.editorRoles.contains(role))
                        TextButton.icon(
                          key: const Key('protocol.revoke'),
                          onPressed: () => _revoke(context, ref),
                          icon: const Icon(Icons.cancel, color: ZanjirColors.danger),
                          label: Text(l10n.revokeProtocol, style: const TextStyle(color: ZanjirColors.danger)),
                        ),
                    ],
                  ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _Hash extends StatelessWidget {
  const _Hash({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 6),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: ZanjirColors.inkMuted, fontSize: 12)),
        SelectableText(value, style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
      ],
    ),
  );
}

/// QR havola `zanjir://app/v/<qr_token>`: shu qurilmadagi protokolni topib, holat va tekshiruvni ko'rsatadi.
final _protocolByTokenProvider = FutureProvider.family<(ProtocolRow, ProtocolStatus)?, String>((ref, token) async {
  final repos = await ref.watch(repositoriesProvider.future);
  final row = await repos.protocols.byQrToken(token);
  return row == null ? null : (row, await repos.protocols.status(row.id));
});

class ProtocolVerifyScreen extends ConsumerWidget {
  const ProtocolVerifyScreen({super.key, required this.token});
  final String token;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.verifyTitle)),
      body: AsyncView(
        value: ref.watch(_protocolByTokenProvider(token)),
        builder: (found) => found == null
            ? Padding(padding: const EdgeInsets.all(16), child: Text(l10n.protocolNotFound))
            : ListView(
                children: [ProtocolCard(protocol: found.$1, status: found.$2)],
              ),
      ),
      bottomNavigationBar: const DisclaimerBanner(),
    );
  }
}

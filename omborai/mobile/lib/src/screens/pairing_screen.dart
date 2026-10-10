import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../app_session.dart';
import '../auth.dart';

/// Juftlash kodini ko'rsatish (boshqa qurilmaga) va boshqa qurilmadan kodni kiritish.
class PairingScreen extends StatefulWidget {
  const PairingScreen({super.key, required this.session});

  final AppSession session;

  @override
  State<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends State<PairingScreen> {
  final _input = TextEditingController();
  String? _code;
  String? _message;

  @override
  void initState() {
    super.initState();
    _loadCode();
  }

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _loadCode() async {
    final code = await widget.session.pairingCode();
    if (!mounted) return;
    setState(() => _code = code);
  }

  Future<void> _join() async {
    try {
      parsePairingCode(_input.text);
      await widget.session.joinStore(_input.text);
      if (!mounted) return;
      setState(() => _message = "Do'kon qo'shildi. Ma'lumot kelishini kuting.");
      await _loadCode();
    } on FormatException catch (e) {
      setState(() => _message = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Juftlash')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            "Bu juftlash kodi. Boshqa qurilmada kiritsangiz, o'sha do'kon ma'lumoti va "
            "foydalanuvchilari bilan ishlaydi. Kodni hech kimga bermang.",
          ),
          const SizedBox(height: 12),
          SelectableText(
            _code ?? "Do'kon hali yaratilmagan",
            style: const TextStyle(fontFamily: 'monospace'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _code == null
                ? null
                : () async {
                    await Clipboard.setData(ClipboardData(text: _code!));
                    if (mounted) setState(() => _message = 'Nusxalandi');
                  },
            icon: const Icon(Icons.copy),
            label: const Text('Nusxalash'),
          ),
          const Divider(height: 32),
          TextField(
            controller: _input,
            decoration: const InputDecoration(
              labelText: 'Boshqa qurilmadan juftlash kodi',
            ),
          ),
          const SizedBox(height: 8),
          FilledButton(onPressed: _join, child: const Text("Qo'shilish")),
          if (_message != null) ...[
            const SizedBox(height: 12),
            Text(_message!),
          ],
        ],
      ),
    );
  }
}

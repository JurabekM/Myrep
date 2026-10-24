import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:flutter/material.dart';

/// O'sib boradigan ro'yxatlar paginatsiyasi (MVP_PLAN Vazifa 15): avval
/// [pageSize] ta element quriladi, qolgani «Yana ko'rsatish» bilan.
/// Kunlik daromadli oilada oyiga yuzlab yozuv bo'ladi — hammasini birdan
/// qurish sekin telefonda ekranni qotiradi.
class PagedList extends StatefulWidget {
  const PagedList({
    required this.count,
    required this.itemBuilder,
    this.pageSize = defaultPageSize,
    this.separator,
    super.key,
  });

  static const defaultPageSize = 30;

  final int count;
  final IndexedWidgetBuilder itemBuilder;
  final int pageSize;
  final Widget? separator;

  @override
  State<PagedList> createState() => _PagedListState();
}

class _PagedListState extends State<PagedList> {
  late int _shown = widget.pageSize;

  @override
  Widget build(BuildContext context) {
    final visible = widget.count < _shown ? widget.count : _shown;
    final rest = widget.count - visible;
    final separator = widget.separator;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < visible; i++) ...[
          if (i > 0 && separator != null) separator,
          widget.itemBuilder(context, i),
        ],
        if (rest > 0)
          TextButton.icon(
            key: const Key('paged-more'),
            style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
            icon: const Icon(Icons.expand_more),
            label: Text(context.l10n.showMore(rest)),
            onPressed: () => setState(() => _shown += widget.pageSize),
          ),
      ],
    );
  }
}

// TAMGA standart siyosatlar to'plami (v1).
//
// Qoida: hamma narsaga ruxsat, `forbid` siyosatlari esa istisnolar. Har bir `forbid` uchun:
//   @id      — jurnal va Studio'da ko'rinadigan nom
//   @verdict — "deny" (bloklash) yoki "ask" (inson tasdig'i)
//   @reason  — agentga va foydalanuvchiga ko'rsatiladigan sabab
// Bir nechta siyosat mos kelsa: "deny" > "ask".

@id("allow-by-default")
permit (principal, action, resource);

@id("no-secret-exfil")
@verdict("deny")
@reason("maxfiy fayl yoki maxfiy qiymat tarmoqqa yuborilmoqda")
forbid (principal, action == Tamga::Action::"use_tool", resource)
when {
  context.network_egress &&
  (context.reads_secret_file || context.sends_tainted_secret || context.contains_secret_pattern)
};

@id("no-pipe-to-shell")
@verdict("deny")
@reason("internetdan yuklangan skript tekshiruvsiz ishga tushirilmoqda")
forbid (principal, action == Tamga::Action::"use_tool", resource)
when { context.pipes_to_shell };

@id("no-destructive-outside-workspace")
@verdict("deny")
@reason("ishchi papkadan tashqarida rekursiv o'chirish yoki formatlash")
forbid (principal, action == Tamga::Action::"use_tool", resource)
when { context.destructive_outside_workspace };

@id("ask-egress-after-secret-read")
@verdict("ask")
@reason("bu sessiya maxfiy ma'lumotni o'qigan, endi tarmoqqa chiqmoqda")
forbid (principal, action == Tamga::Action::"use_tool", resource)
when { context.network_egress && context.session_secret_read };

@id("ask-force-push")
@verdict("ask")
@reason("git tarixini majburan qayta yozish (force push)")
forbid (principal, action == Tamga::Action::"use_tool", resource)
when { context.force_push };

@id("ask-write-outside-workspace")
@verdict("ask")
@reason("ishchi papkadan tashqariga yozish")
forbid (principal, action == Tamga::Action::"use_tool", resource)
when { context.writes_outside_workspace };

@id("ask-system-change")
@verdict("ask")
@reason("tizim sozlamalari, xizmatlar yoki reestrni o'zgartirish")
forbid (principal, action == Tamga::Action::"use_tool", resource)
when { context.system_change };

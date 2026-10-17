# TAMGA — raqobatchilar tahlili

**Sana:** 2026-10-17. **Usul:** internet qidiruvi (~45 so'rov) va loyiha README, rasmiy hujjat,
arXiv va IETF Datatracker sahifalarini o'qish. Bu hujjat `docs/PLAN.md` §1 dagi yangilik
da'vosini tekshiradi.

**Qisqa javob.** Beshta mezonning **har biri alohida allaqachon bor**. Ularning ko'pi 2026-yilda
chiqqan. "Hash-zanjirli agent audit jurnali" esa juda gavjum toifaga aylangan (20 dan ortiq loyiha).
Lekin **beshtasini bitta lokal, serversiz vositada birlashtirgan loyiha topilmadi.**
Eng yaqin uchtasi: **AgentProvenance** (beshtasi ham qisman bor, lekin faqat Linux),
**Pipelock** va **Microsoft Agent Governance Toolkit** (1–2 mezon to'liq, 3-mezon qisman).
Bo'shliq ochiq, lekin tor va tez yopilmoqda. Tafsilot 12-bo'limda.

---

## 0. Belgilar

**Mezonlar** (PLAN.md §1 dagi da'vo):

| # | Mezon |
|---|---|
| **M1** | Ochiq yozuv formati + mustaqil verifikator + test vektorlari |
| **M2** | Agent harakatini bajarilishidan **oldin** siyosat bilan to'xtatish |
| **M3** | Xesh-zanjir + Merkle checkpoint + gibrid Ed25519/ML-DSA-65 imzo |
| **M4** | Agent e'lon qilgan harakat bilan OS kuzatgan harakatni solishtirish ("aytdi va qildi") |
| **M5** | Crypto-shredding: payload o'chirilsa ham zanjir tekshiriladi |

**Jadval belgilari:** ✅ manbada aniq bor · ◐ qisman yoki boshqa shaklda · — manbada topilmadi.
"—" belgisi funksiya **yo'qligini isbotlamaydi**, faqat biz o'qigan manbada u ko'rsatilmaganini bildiradi.

**Fakt darajasi** (har qator oxirida):

- **[F]** birlamchi manba (loyiha README, rasmiy hujjat, arXiv sahifasi, IETF matni) shu sessiyada o'qildi.
- **[I]** faqat ikkilamchi manba bor (yangilik sayti, katalog, blog). Birlamchi manba ko'rilmadi.
- **[B]** umumiy bilim. Shu sessiyada qayta tekshirilmadi.
- **[T]** bizning taxminimiz yoki xulosamiz.

---

## 1. LLM observability (tracing)

Bu vositalar dasturchi uchun yaratilgan: nima bo'lganini ko'rsatadi, lekin **dalil** bermaydi.
Hech birida tamper-evident jurnal yoki bajarilishdan oldin bloklash topilmadi.

| Vosita | Nima qiladi | M1 | M2 | M3 | M4 | M5 | Litsenziya | Manba |
|---|---|---|---|---|---|---|---|---|
| **LangSmith** (LangChain) | Trace, eval va monitoring SaaS. Self-host faqat Enterprise rejasida. "Audit log" ~70 ta **administrativ** amalni yozadi (API kalit va hokazo), agent harakatini emas. | — | — | — | — | — | yopiq | [kb.langchain.com](https://kb.langchain.com/articles/5478528798-enabling-audit-logs-in-self-hosted-langsmith) [I] |
| **Langfuse** | Ochiq LLM observability. 2026-yil yanvarda **ClickHouse sotib oldi**. | — | — | — | — | — | MIT | [ClickHouse blogi](https://clickhouse.com/blog/clickhouse-acquires-langfuse-open-source-llm-observability), [langfuse.com/press](https://langfuse.com/press/press) [F] |
| **Arize Phoenix** | OTel/OpenInference asosidagi tracing. Audit log faqat pullik Arize AX'da bor. | — | — | — | — | — | ELv2 (OSI emas) | [arize.com litsenziya](https://www.arize.com/docs/phoenix/self-hosting/license.md) [F] |
| **Helicone** | LLM proxy + observability. 2026-yil 3-martda **Mintlify sotib oldi**, hozir faqat texnik xizmat rejimida. | — | — | — | — | — | Apache-2.0 | [chatforest sharhi](https://chatforest.com/reviews/helicone-llm-observability-gateway/) [I] |
| **OpenTelemetry GenAI semconv** | `execute_tool`, `invoke_agent` span'lari uchun standart nomlar. Holati hali **Development**. Prompt va argumentlar standart holatda yozilmaydi. | ◐ ochiq format, yaxlitlik yo'q | — | — | — | — | Apache-2.0 | [opentelemetry.io](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans), [greptime](https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions) [F] |

**Xulosa [T]:** bu toifa raqobatchi emas, balki **integratsiya nuqtasi**. PLAN.md §9 dagi
"OTel GenAI'dan import" g'oyasi to'g'ri yo'nalish.

## 2. Guardrail va agent xavfsizligi

2025-yilda bu bozor yirik kompaniyalarga sotildi. Ular asosan **kontent filtri**
(prompt injection, ma'lumot sizishi) bilan shug'ullanadi. Kriptografik jurnal bermaydi.

| Vosita | Nima qiladi | M1 | M2 | M3 | M4 | M5 | Litsenziya | Manba |
|---|---|---|---|---|---|---|---|---|
| **Invariant Labs** (2025-yil 24-iyundan **Snyk**) | Guardrails qoidalar tili + Gateway (MCP/LLM proxy). Qoida buzilsa so'rovni bloklaydi. Explorer trace'larni ko'rsatadi. | — | ✅ | — | — | — | ochiq kod (litsenziya tekshirilmadi) | [invariantlabs.ai](https://invariantlabs.ai/blog/guardrails), [snyk.io](https://snyk.io/de/news/snyk-acquires-invariant-labs-to-accelerate-agentic-ai-security-innovation/) [F] |
| **Lakera** (2025-yil oktabridan **Check Point**, ~$201.8M) | Prompt injection va ma'lumot sizishidan himoya. | — | ◐ kontent | — | — | — | yopiq | [nand-research](https://nand-research.com/research-note-check-point-to-acquire-lakera-for-end-to-end-ai-security/), [tech-insider](https://tech-insider.org/lakera-vs-prisma-airs-vs-cisco-ai-defense-2026/) [I] |
| **Protect AI** (2025-yil iyulidan **Palo Alto Networks**) | Model skaneri (Guardian), red-team (Recon), runtime monitoring (Layer). | — | ◐ | — | — | — | yopiq | [tech-insider](https://tech-insider.org/lakera-vs-prisma-airs-vs-cisco-ai-defense-2026/) [I] |
| **NVIDIA NeMo Guardrails** | "Execution rails": tool kirishi va chiqishini chaqiruvdan oldin va keyin tekshiradi. | — | ✅ | — | — | — | Apache-2.0 (GitHub'da NOASSERTION ko'rinishi haqida xabar bor) | [docs.nvidia.com](https://docs.nvidia.com/nemo/guardrails/0.21.0/about/overview.html) [F] |

## 3. Bulut provayderlari va yirik kompaniyalar

| Vosita | Nima qiladi | M1 | M2 | M3 | M4 | M5 | Litsenziya | Manba |
|---|---|---|---|---|---|---|---|---|
| **AWS Bedrock AgentCore Policy** | 2026-yil 3-martda GA. Siyosat **Cedar** tilida, AgentCore Gateway har bir tool chaqiruvini bajarilishidan oldin tekshiradi. | — | ✅ | — | — | — | yopiq, bulut | [aws.amazon.com what's new](https://aws.amazon.com/de/about-aws/whats-new/2026/03/policy-amazon-bedrock-agentcore-generally-available/) [F] |
| **Google Agent Gateway + Model Armor** | Agent trafigi uchun boshqaruv tekisligi. Model Armor kontentni bloklaydi yoki faqat log yozadi (MCP, A2A, OpenAI formati). | — | ◐ kontent | — | — | — | yopiq, bulut | [docs.cloud.google.com](https://docs.cloud.google.com/model-armor/model-armor-agent-gateway-integration?hl=en) [F] |
| **Microsoft Agent Governance Toolkit (AGT)** | Agent harakatini ilova kodida ushlab, siyosat qo'llaydi (YAML; OPA/Cedar faqat diagrammada). **10 ta RFC 2119 spec + 992 conformance test**, `agt verify`. Audit "tamper-evident", "Merkle audit" deb tasvirlangan, imzo algoritmi aytilmagan. Rasman "OS yadrosi darajasida emas". Claude Code plagini `PreToolUse` da allow/deny/review qaytaradi. Holati: Public Preview, 6.4k ⭐. | ✅ | ✅ | ◐ PQ yo'q | — | — | MIT | [github.com/microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit), [Claude Code paketi](https://microsoft.github.io/agent-governance-toolkit/packages/claude-code-governance/) [F] |
| ↳ AGT'ning mustaqil sharhi | Audit xotirada saqlanadi va qayta ishga tushganda yo'qoladi; bufer to'lsa tekshiruv buziladi; verify funksiyasini testdan boshqa joy chaqirmaydi. | | | | | | | [flyingpenguin.com](https://www.flyingpenguin.com/category/security/page/4/) [I, tasdiqlanmagan] |
| **Microsoft Agent 365 / Entra Agent ID** | Agent identifikatsiyasi, reestri, Conditional Access. Bu identifikatsiya qatlami, jurnal emas. | — | ◐ kirish | — | — | — | yopiq | [learn.microsoft.com](https://learn.microsoft.com/en-us/entra/agent-id/whats-new-agent-id) [F] |
| **Endor Labs, CrowdStrike AIDR** (Claude Code kollektorlari) | Tijoriy hook kollektorlari. Hook xato bersa, Endor ruxsat beradi (fail-open). | — | ◐ | — | — | — | yopiq | [docs.endorlabs.com](https://docs.endorlabs.com/agent-governance/claude-code), [aidr-docs.crowdstrike.com](https://aidr-docs.crowdstrike.com/docs/aidr/collectors/agentic/claude-code) [I] |

## 4. MCP gateway va proxy

| Vosita | Nima qiladi | M1 | M2 | M3 | M4 | M5 | Litsenziya | Manba |
|---|---|---|---|---|---|---|---|---|
| **Pipelock** ⚠ eng kuchli raqobatchilardan | Go'da yozilgan "agent firewall": HTTP/WS/MCP/A2A trafigini tekshiradi, MCP tool siyosati xavfli chaqiruvni **bajarilishidan oldin** bloklaydi. Mediator imzolagan **action receipt**lar (Ed25519), hash-zanjirli JSONL "flight recorder", Ed25519 imzoli checkpoint'lar, ixtiyoriy Rekor. Spec: in-toto predicate + JCS (RFC 8785). **Go, TS, Rust va Python'da mustaqil verifikator** va umumiy conformance korpusi bor. DLP redaksiyasi bor. Izolyatsiya faqat Linux/macOS. Claude Code'ga hook orqali emas, MCP o'rash orqali ulanadi. 931 ⭐, v3.7.0. | ✅ | ✅ | ◐ Merkle va PQ topilmadi | — ("kernel-observed posture" bor, solishtirish emas) | ◐ redaksiya, shredding emas | Apache-2.0 yadro + ELv2 enterprise | [README](https://raw.githubusercontent.com/luckyPipewrench/pipelock/main/README.md), [GitHub](https://github.com/luckyPipewrench/pipelock), [helpnetsecurity](https://www.helpnetsecurity.com/2026/05/04/pipelock-open-source-ai-agent-firewall/) [F] |
| **Enkrypt AI MCP Gateway** | Tool chaqiruvini tasdiqlaydi, o'zgartiradi yoki bloklaydi. Qarorlar jurnali yuritadi. | — | ✅ | — | — | — | ochiq kod | [enkryptai.com](https://www.enkryptai.com/product/mcp-gateway) [I, sotuvchi sahifasi] |
| **cMCP** (agentrust-io) | Cedar siyosatini TEE ichida bajaradi va imzolangan attestatsiya yozuvlarini chiqaradi. | — | ✅ | ◐ | — | — | ? | [github.com/agentrust-io/cmcp](https://github.com/agentrust-io/cmcp) [I] |
| **GitHub gh-aw-mcpg** | WASM DIFC guard'lar har so'rovga maxfiylik va yaxlitlik yorlig'ini qo'llaydi. JSONL RPC log yuritadi. | — | ✅ | — | — | — | MIT? | [pkg.go.dev](https://pkg.go.dev/github.com/github/gh-aw-mcpg) [F] |
| **hoop.dev** | OIDC guruhiga qarab siyosat. Audit MCP server o'zgartira olmaydigan backend'ga yoziladi. | — | ✅ | — | — | — | MIT | [hoop.dev](https://hoop.dev/blog/policy-enforcement-for-mcp/) [I] |
| **Kichik OSS gateway'lar**: MCPGuard, McpVanguard, mcp-firewall, mcp-policy-gateway, mcp-audit-gateway | Siyosat + audit. Ba'zilarida hash-zanjirli `audit.jsonl` va dry-run rejimi bor, imzo topilmadi. | — | ✅ | ◐ | — | — | MIT / AGPL-3.0 | [glama MCPGuard](https://glama.ai/mcp/servers/piyushptiwari1/mcpguard), [mcp-firewall](https://github.com/ressl/mcp-firewall), [glama mcp-policy-gateway](https://glama.ai/mcp/servers/kbafe4fuxp) [I] |

## 5. Claude Code hook'lari asosidagi vositalar

Claude Code `PreToolUse` hook'i `hookSpecificOutput.permissionDecision` maydonida `allow`, `deny`, `ask`
yoki `defer` qaytara oladi. `permissionDecisionReason` matni Claude'ga ko'rsatiladi
([code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks) [F]). Bu interfeys hamma uchun
ochiq, shuning uchun hook orqali bloklashning o'zi **farq emas**.

| Vosita | Nima qiladi | M1 | M2 | M3 | M4 | M5 | Litsenziya | Manba |
|---|---|---|---|---|---|---|---|---|
| **Rampart** | Claude Code'ning native pre/post hook'lari orqali allow/ask/deny qaytaradi, siyosat YAML'da. MCP stdio proxy ham bor. Audit hash-zanjirli, `rampart audit verify` bilan tekshiriladi, imzo aytilmagan. Kalit shaklidagi sirlar yashiriladi. Rasman "sandbox emas", jarayon ichidagi syscall'larni ko'rmaydi. ~90 ⭐. | — | ✅ | ◐ | — | ◐ redaksiya | Apache-2.0 | [github.com/peg/rampart](https://github.com/peg/rampart) [F] |
| **cc-audit** | `PreToolUse` siyosat darvozasi + alohida jarayon yozadigan append-only JSONL. | — | ✅ | ◐? | — | — | ? | [pypi.org/project/cc-audit](https://pypi.org/project/cc-audit/) [I] |
| **Agentmetry** | Claude Code, Cursor, Codex va Antigravity hook'larini lokal yozadi: hash-zanjirli JSONL, regex DLP, ketma-ketlik detektori. Public alpha, bulutga hech narsa yubormaydi. | — | ◐ | ◐ | — | ◐ DLP | ? | [pypi.org/project/agentmetry](https://pypi.org/project/agentmetry/) [I] |
| **Microsoft AGT Claude Code paketi** | 3-bo'limga qarang. | | | | | | | |

## 6. Agent audit, receipt va "flight recorder"lar — eng yaqin toifa

Bu toifa 2026-yilda portladi. Hammasida asosiy g'oya bir xil: har bir harakat xeshlanadi va
oldingi yozuvga bog'lanadi, ba'zilarida yana imzolanadi. **Post-kvant imzoli** loyihalar ham bor
(asqav, QLog, pqattest), ammo ularning hech biri **gibrid** emas.

| Vosita | Nima qiladi | M1 | M2 | M3 | M4 | M5 | Litsenziya | Manba |
|---|---|---|---|---|---|---|---|---|
| **asqav** ⚠ | Python SDK. Har harakatni **ML-DSA-65** bilan imzolaydi, RFC 3161 va OpenTimestamps bilan vaqt muhri qo'yadi. Siyosatni bajarilishdan oldin baholaydi (masalan, `data:delete:*` ni bloklash). IETF draft (`draft-marques-asqav-compliance-receipts`, -09 faol) va test vektorlari (`asqav-03-chain-link`) bor. PyPI sahifasiga ko'ra ML-DSA **server tomonda** ishlaydi, `verify` uchun API kalit kerak. | ✅ | ✅ [I] | ◐ PQ bor, gibrid yo'q, Merkle ixtiyoriy | — (`sandbox_state` maydoni bor xolos) | — (draft payload'ni saqlashni talab qiladi) | MIT | [pypi.org/project/asqav](https://pypi.org/project/asqav/), [IETF draft -08](https://datatracker.ietf.org/doc/html/draft-marques-asqav-compliance-receipts-08) [F]; [helpnetsecurity](https://www.helpnetsecurity.com/2026/04/09/asqav-ai-agent-audit-trail/) [I] |
| **QLog** (Quantova) | Node SDK. ML-DSA-65 + SHA3-256 zanjir, imzoli checkpoint'lar Quantova **testnet**'iga ankor qilinadi (akkaunt kerak). "Intent first" faqat tekshirish paytida qo'llanadi, ish paytida bloklamaydi. 0 ⭐. | ◐ format va tartib bor, vektor yo'q | — | ◐ PQ, gibrid yo'q | — | — | Apache-2.0/MIT | [github.com/Quantova/QLog](https://github.com/Quantova/QLog) [F] |
| **pqattest** | TS. Faqat ML-DSA-65 + SHA-256 zanjir, `verify` CLI. Harakat bajarilgandan **keyin** yozadi. 0 ⭐. | ◐ | — | ◐ | — | — | Apache-2.0 | [github.com/AAH20/pqattest](https://github.com/AAH20/pqattest) [F] |
| **Agent Receipts** | TS. Ed25519 receipt'lar, lokal SQLite, MCP server. Serverga ishonmasdan tekshirish mumkin. 1 ⭐. | — | — | ◐ | — | — | MIT | [github.com/webaesbyamin/agent-receipts](https://github.com/webaesbyamin/agent-receipts) [F] |
| **Aegis** (acacian) | Har harakatga qaror (auto/approve/block) + SHA-256/SHA3 zanjir, `chain.verify()`. Imzo va Merkle topilmadi. | — | ◐ | ◐ | — | — | MIT | [acacian.github.io/aegis](https://acacian.github.io/aegis/solutions/ai-agent-audit-trail/) [F] |
| **OpenFang** | Rust'da yozilgan agent OS (v0.1.0, 2026-yil fevral). Merkle hash-zanjirli audit, Ed25519 manifest imzosi, taint tracking, capability gate'lar. | — | ◐ | ◐ | — | — | MIT | [i-scoop.eu](https://www.i-scoop.eu/openfang/), [hermes-agent #487](https://github.com/NousResearch/hermes-agent/issues/487) [I] |
| **AgentStamp** | Har hodisaga SHA-256 zanjir + Ed25519, verify-chain endpoint. | — | — | ◐ | — | — | ? | [dev.to](https://dev.to/vinaybhosle/how-we-built-a-tamper-evident-audit-trail-for-ai-agents-3jc6) [I] |
| **halo-record** | Bog'liqliksiz hash-zanjirli log (tool, model chaqiruvi, tasdiqlar), checkpoint orqali tekshiriladi. | — | — | ◐ | — | — | ? | [github.com/bkuan001/halo-record](https://github.com/bkuan001/halo-record) [I] |
| **BLACKBOX** (GreenAiSolution) | Python recorder + MCP server. Hash-zanjir, sirlarni kalit nomi va shakli bo'yicha tozalaydi. | — | — | ◐ | — | ◐ | MIT | [contra.com](https://contra.com/p/scERYgBW-blackbox-a-flight-recorder-for-ai-agents) [I] |
| **airblackbox/tombstone** | Tamper-evident ledger ustida "isbotlanadigan crypto-shredded o'chirish". 1 ⭐. | — | — | ◐ | — | ✅ (da'vo) | ? | [awesome.ecosyste.ms](https://awesome.ecosyste.ms/projects/github.com%2Fairblackbox%2Ftombstone) [I] |
| **sm-aae** (Attested Action Envelope) | Harakatdan **oldin** chiqariladigan imzoli qaror konverti: kim nima so'radi, qaysi siyosat nima dedi. Konvertlar xesh bilan zanjirlangan. | — | ◐ | ◐ | — | — | ? | [pypi.org/project/sm-aae](https://pypi.org/project/sm-aae/) [I] |
| **trustatom** | Ed25519 qaror receipt'lari. ML-DSA-65 kosignatura **rejada**: hozircha faqat mavjudligi tekshiriladi, kriptografik tekshirilmaydi. | — | — | ◐ | — | — | ? | [pypi.org/project/trustatom](https://pypi.org/project/trustatom/) [I] |
| Boshqalar: AgentLens, Agent Evidence Recorder, AgentFlightRecorder.Core (.NET), SuperLocalMemory 4.0 | Hash-zanjir va/yoki yozishdan oldingi redaksiya. | — | — | ◐ | — | ◐ | turli | [glama AgentLens](https://glama.ai/mcp/servers/agentkitai/agentlens), [nuget](https://www.nuget.org/packages/AgentFlightRecorder.Core), [arXiv 2608.08253](https://arxiv.org/pdf/2608.08253) [I] |

## 7. "Aytdi va qildi" (M4): OS darajasida kuzatish

Bu TAMGA'ning eng noyob mezoni deb hisoblangan edi. Natija: **g'oya allaqachon bor**.
Ochiq kodli implementatsiyalari esa faqat **Linux eBPF** asosida ishlaydi.

| Vosita | Nima qiladi | M1 | M2 | M3 | M4 | M5 | Litsenziya | Manba |
|---|---|---|---|---|---|---|---|---|
| **AgentProvenance** (ByteYellow) ⚠⚠ eng yaqin raqobatchi | Agent vazifasi, suhbati va tool chaqiruvlarini ular yaratgan jarayon, fayl va tarmoq faoliyati bilan birga yozadi. `intent diff` buyrug'i **"Intent-Runtime Diff"** chiqaradi: e'lon qilingan harakat va kuzatilgan ta'sir farqi, jumladan rad etilgandan keyin bajarilgan harakatlar. Kernel capture faqat **Linux** (eBPF), Windows'da faqat WSL ichida, macOS'da yadro darajasi yo'q. Claude Code hook log'larini `hooksbridge` o'qiydi, MCP orqali "action preflight" bor. Imzo ixtiyoriy (`--sign-key`), algoritmi aytilmagan. Dalillar content-hash va parent havolasi bilan bog'langan, zanjir yoki Merkle aniq aytilmagan. Sirlar redaksiya qilinadi, offline tekshiriladigan forensik bundle bor. v0.9.0, 2026-10-08. | ◐ OpenAPI + verify, test vektori yo'q | ◐ preflight, bloklash integratsiyaga bog'liq | ◐ | ✅ (Linux) | ◐ redaksiya | Apache-2.0 | [pkg.go.dev/github.com/byteyellow/agentprovenance](https://pkg.go.dev/github.com/byteyellow/agentprovenance) [F] |
| **AgentSight** (eunomia-bpf) | eBPF orqali TLS ichidagi LLM trafigini (niyat) va yadro hodisalarini (ta'sir) ushlab, ularni korrelyatsiya qiladi. Qo'shimcha yuk <3%. Faqat Linux. | — | — | — | ✅ (Linux) | — | ochiq kod | [arXiv 2508.02736](https://arxiv.org/abs/2508.02736v1), [docs.rs/agentsight](https://docs.rs/crate/agentsight/1.0.0) [F] |
| **AgentKernel** (arXiv 2609.29647, 2026-08-29) | "Trust-native" agent OS: Identity/Perception/Cognition/Execution ustunlari, "semantic-to-kernel enforcement". Kod havolasi yo'q. Ikkilamchi manbaga ko'ra reja va bajarilgan trace'ni moslaydi, eBPF bilan bloklaydi. | — | ◐ | — | ◐ [I] | — | CC (maqola) | [arXiv](https://arxiv.org/abs/2609.29647) [F]; [codex.danielvaughan.com](https://codex.danielvaughan.com/2026/06/09/ebpf-runtime-observability-codex-cli-agentsight-tetragon-kernel-level-agent-monitoring/) [I] |
| **Tetragon, Falco** | Umumiy eBPF runtime xavfsizligi. Agent semantikasini bilmaydi, AgentProvenance ular bilan manba sifatida ishlay oladi. | — | ◐ | — | ◐ | — | Apache-2.0 | [codex.danielvaughan.com](https://codex.danielvaughan.com/2026/06/09/ebpf-runtime-observability-codex-cli-agentsight-tetragon-kernel-level-agent-monitoring/) [I] |

**Xulosa [T]:** Windows'da **admin huquqisiz**, native ishlaydigan "aytdi va qildi" solishtiruvi
topilmadi. Topilgan hamma vosita Linux eBPF'ga tayanadi. Bu TAMGA'ning eng aniq farqi bo'lib qoladi
(QARCHIG'AY tajribasi shu yerda ishlatiladi).

## 8. Tadqiqot maqolalari (2026)

| Ish | Mazmuni | M1 | M2 | M3 | M4 | M5 | Manba |
|---|---|---|---|---|---|---|---|
| **Agent Flight Recorder** (Bindschaedler va boshq., arXiv 2609.01931, BCCA 2026) | Hash-zanjir + Merkle batching + L2 blokcheynga davriy ankor (100K hodisa uchun $2.30). Hodisaga ~48 µs va 512 bayt sarflanadi. Tahrir, o'chirish, tartib almashtirish va fork 100% aniqlanadi. Redaksiya bosqichi eski qatorlarning shifrlangan payload'ini tozalaydi, zanjir esa tekshirilaveradi. Kod havolasi yo'q. | — | — | ◐ imzo aytilmagan | — | ✅ [I] | [arXiv abstrakt](https://arxiv.org/abs/2609.01931) [F]; redaksiya tafsiloti [PDF](https://arxiv.org/pdf/2609.01931) [I] |
| **Notarized Agents** (arXiv 2606.04193) | Agent bilan gaplashgan har bir xizmat receipt'ni o'zi imzolaydi. Buzilgan agent o'z izini soxtalashtira olmaydi. | — | — | ◐ | — | — | [arXiv](https://arxiv.org/html/2606.04193v1) [I] |
| **AgentBound** (arXiv 2606.30970) | Receipt'ni agent va enforcement xizmati birga imzolaydi, append-only ledger'ga yoziladi. | — | ◐ | ◐ | — | — | [arXiv](https://arxiv.org/pdf/2606.30970) [I] |
| **PQ-resilient audit evidence** (arXiv 2512.00110) | Uzoq saqlanadigan audit dalili uchun gibrid klassik+PQ imzo, qayta imzolash, Merkle-ildiz ankori. M3 dizayni uchun nazariy asos. | — | — | ◐ | — | — | [arXiv](https://arxiv.org/pdf/2512.00110) [I] |

## 9. Standartlar va IETF draftlari

| Hujjat | Mazmuni | M1 | M2 | M3 | M4 | M5 | Manba |
|---|---|---|---|---|---|---|---|
| **draft-sharif-agent-audit-trail-08** (R. Sharif, CyberSecAI, 2026-10-13, individual draft, Standards Track maqsadida) ⚠ AAR uchun eng muhim | Agent yozuvi uchun JSON format. `prev_hash = SHA-256(JCS(oldingi yozuv))`, muqobil kanonikalashtirish taqiqlangan. Standart imzo ES256, ML-DSA-65 ixtiyoriy, **gibrid ES256 + ML-DSA-65** rejimi bor. Ixtiyoriy RFC 6962 Merkle batch. Rad etilgan yoki eskalatsiya qilingan qarorlar `record_phase: "pre_execution"` sifatida yozilishi **shart**. Recorder agentdan alohida OS principal ostida ishlashi kerak. O'chirish imzoli **tombstone** orqali, `content_fingerprint` saqlanadi. 10 qadamli verifikatsiya tartibi bor, test vektorlari biz o'qigan qismda topilmadi. Bu faqat spec, ishlaydigan vosita emas. | ✅ (vektorlarsiz) | ◐ qaror yoziladi, bloklash spec doirasida emas | ✅ (gibrid Ed25519 emas, ES256 bilan) | — | ✅ tombstone | [datatracker](https://datatracker.ietf.org/doc/draft-sharif-agent-audit-trail/) [F] |
| **draft-marques-asqav-compliance-receipts** (-08, 2026-08-31; -09 faol) | Imzoli receipt'larni EU AI Act, DORA, NIST AI RMF bilan bog'laydigan muvofiqlik profili. Ankor majburiy, DSSE/in-toto konvert ishlatiladi. | ✅ | ◐ | ◐ | — | — | [datatracker](https://datatracker.ietf.org/doc/html/draft-marques-asqav-compliance-receipts-08) [F] |
| **draft-maintainer-1f916-agent-record-01** (2026-08-12) | Agent identifikatsiyasi va tarixi uchun guvoh kontrimzoli event log: Ed25519, RFC 6962 Merkle, 5 daqiqalik checkpoint, 4 xil hukm. | ◐ | — | ◐ PQ yo'q | — | — | [datatracker](https://datatracker.ietf.org/doc/draft-maintainer-1f916-agent-record/) [F] |
| **draft-cowles-volt** | Agent trace'lari uchun hash-zanjir formati, content-addressed havolalar. | ◐ | — | ◐ | — | ◐ | [datatracker](https://datatracker.ietf.org/doc/draft-cowles-volt/) [I] |
| **draft-kamimura-scitt-vcp-03** | AI savdo tizimlari audit izi uchun SCITT profili. Crypto-shredding'ni GDPR bilan mos mexanizm sifatida tilga oladi. | ◐ | — | ◐ | — | ◐ | [ietf.org](https://www.ietf.org/archive/id/draft-kamimura-scitt-vcp-03.txt) [I] |
| **draft-kuehlewind-audit-architecture-00** | Agent auditi arxitekturasi: niyat, delegatsiya, avtorizatsiya va bajarishni bog'lash. | — | — | — | ◐ g'oya | — | [ietf mirror](https://ftp.sjtu.edu.cn/pub/internet-drafts/draft-kuehlewind-audit-architecture-00.xml) [I] |
| **SCITT — RFC 9943** (2026-yil iyun) | Shaffof ta'minot zanjiri arxitekturasi. SCRAPI hozir RFC Editor navbatida. Tashqi guvoh uchun tayyor infratuzilma. | — | — | ◐ guvoh | — | — | [datatracker SCITT](https://datatracker.ietf.org/wg/scitt/documents/) [I] |
| **C2PA** (2.2, 2025-yil may) | Kontent (rasm, video, hujjat) provenance manifesti. Agent harakatlari uchun assertion topilmadi. 2026-yilgi tahlil C2PA 2.2 xavfsizlik maqsadlariga erishmaganini ko'rsatadi. | — | — | — | — | — | [arXiv 2604.23280](https://arxiv.org/pdf/2604.23280), [eprint 2026/804](https://eprint.iacr.org/2026/804) [I] |

## 10. Tamper-evident log infratuzilmasi

Bular raqobatchi emas. TAMGA ulardan **guvoh** yoki **namuna** sifatida foydalanishi mumkin.

| Tizim | Holati | TAMGA uchun ahamiyati | Manba |
|---|---|---|---|
| **Sigstore Rekor v2** | 2025-yil oktabrda GA. Tile asosida ishlaydi (Trillian-Tessera), faqat `hashedrekord` va `dsse` yozuvlari. v1 texnik xizmat rejimida. | Checkpoint ildizini tashqi guvohga yuborish uchun tayyor ommaviy log | [blog.sigstore.dev](https://blog.sigstore.dev/rekor-v2-ga/) [F] |
| **RFC 9162** (CT v2.0, Experimental) | Merkle daraxti, inclusion va consistency proof, STH. | AAR Merkle qatlami shu uslubda quriladi | [rfc-editor.org](https://www.rfc-editor.org/rfc/rfc9162) [B] |
| **immudb** | Merkle asosidagi o'zgarmas ma'lumotlar bazasi. Yaxlitlikni mijoz tekshiradi. | Server kerak, agent semantikasi yo'q | [docs.immudb.io](https://docs.immudb.io/1.9.6/immudb) [I] |
| **AWS QLDB** | **2025-yil 31-iyulda yopildi.** AWS Aurora PostgreSQL'ga o'tishni tavsiya qiladi, unda kriptografik tekshiruv yo'q. | Bulutdagi ledger xizmatlariga tayanish xavfli ekaniga misol | [infoq.com](https://www.infoq.com/news/2024/07/aws-kill-qldb) [I] |
| **AWS CloudTrail** log file integrity validation | SHA-256 xesh + RSA imzoli digest fayllar. Faqat AWS API hodisalarini qamraydi. | Yaxshi namuna, lekin lokal agent harakatini ko'rmaydi | [docs.aws.amazon.com](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-validation-intro.html) [B] |

## 11. Regulyatsiya

- **EU AI Act 12-modda** [F, [artificialintelligenceact.eu](https://artificialintelligenceact.eu/article/12/)]: yuqori xavfli AI tizimi
  butun umri davomida hodisalarni **avtomatik** loglay olishi kerak. Loglar xavfli vaziyatlarni,
  post-market monitoringni (72-modda) va deployer monitoringini (26(5)-modda) qo'llab-quvvatlashi kerak.
  12-modda matnida kriptografik yaxlitlik yoki imzo **talab qilinmaydi** [T]. Tamper-evidence esa
  loglarning dalil sifatidagi ishonchliligini oshiradi.
- **Muddat o'zgardi.** Digital Omnibus, ya'ni Reglament (EU) 2026/1744, 2026-07-24 da OJ'da e'lon
  qilindi va 2026-07-27 da kuchga kirdi. Annex III tizimlari uchun muddat **2027-12-02**, Annex I
  uchun **2028-08-02** [I, [acompli.ie](https://acompli.ie/news/ai-omnibus-enters-into-force-july-2026/),
  [orrick.com](https://www.orrick.com/en/Insights/2026/07/EU-AI-Act-Update-Digital-Omnibus-Finalizes-8-Compliance-Changes),
  [technology.org](https://www.technology.org/2026/10/13/eu-ai-act-deadlines-after-the-digital-omnibus-what-applies-from-december-2026-to-august-2028/)].
  Ko'p raqobatchi bloglari hali ham "2026-yil avgust" deb yozadi. Bu eskirgan.
- **Saqlash muddati:** 19-modda (provayder) va 26(6)-modda (deployer) bo'yicha loglar kamida
  6 oy saqlanadi [B, [19-modda](https://artificialintelligenceact.eu/article/19/)].
- **Halol cheklov [T]:** Claude Code kabi kod yozuvchi agentlar odatda Annex III'dagi yuqori xavfli
  tizimlarga **kirmaydi**. Shuning uchun EU AI Act TAMGA uchun asosiy bozor drayveri emas. Haqiqiy
  drayverlar: korporativ siyosat, insident tergovi va mijozga dalil taqdim etish.
- **GDPR va crypto-shredding:** kalitni yo'q qilish 17-modda talabini qondirishi yurisdiksiyaga
  va metadata bog'lanishiga qarab farq qiladi. Bu huquqiy emas, texnik mexanizm
  [I, [arXiv 2609.01931](https://arxiv.org/pdf/2609.01931), [arkforge.tech](https://arkforge.tech/en/blog/gdpr-erasure-ai-act-logging-paradox/)].
  TAMGA hujjatlarida "GDPR bilan mos" deyish o'rniga "erasure'ni texnik jihatdan qo'llab-quvvatlaydi" deb yozish kerak.
- **NIST:** AI RMF 1.0 va GenAI profili (AI 600-1) ixtiyoriy hujjatlar [B, [nist.gov](https://www.nist.gov/itl/ai-risk-management-framework)].
  CAISI 2026-02-17 da **AI Agent Standards Initiative**'ni boshladi. NCCoE 2026-02-05 da agent identifikatsiyasi va
  avtorizatsiyasi bo'yicha konsepsiya hujjatini chiqardi, unda "agent nima qilganini qanday audit qilamiz?"
  savoli ochiq qo'yilgan. Yakuniy standart hali yo'q
  [I, [CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-nist-ai-agent-standards-initiative-2026040/), [pillsburylaw.com](https://www.pillsburylaw.com/en/news-and-insights/nist-ai-agent-standards.html)].

---

## 12. Bo'shliq hali ochiqmi? — halol xulosa

### 12.1. Eng yaqin raqobatchilar xaritasi

| Raqobatchi | M1 | M2 | M3 | M4 | M5 | Lokal, serversiz | Windows native | Turi |
|---|---|---|---|---|---|---|---|---|
| **AgentProvenance** | ◐ | ◐ | ◐ | ✅ Linux | ◐ | ✅ | — (WSL) | vosita |
| **Pipelock** | ✅ | ✅ | ◐ Ed25519, Merkle/PQ yo'q | — | ◐ | ✅ | — | vosita |
| **Microsoft AGT** | ✅ | ✅ | ◐ PQ yo'q | — (rasman) | — | ✅ | ? | vosita (preview) |
| **asqav** | ✅ | ✅ | ◐ PQ bor, gibrid yo'q | — | — | — (server tomonda imzo) | ? | SDK + xizmat |
| **draft-sharif-08** | ✅ | ◐ | ✅ (ES256 gibrid) | — | ✅ | — | — | faqat spec |
| **Agent Flight Recorder** | — | — | ◐ | — | ✅ | ◐ (L2 ankor) | — | maqola |
| **TAMGA (reja)** | ✅ | ✅ | ✅ Ed25519+ML-DSA-65 | ✅ | ✅ | ✅ | ✅ | vosita |

### 12.2. Tasdiqlangan faktlar

1. **Alohida mezonlarning hech biri yangi emas.** M1 (Pipelock, AGT, asqav), M2 (o'nlab vosita),
   PQ imzo (asqav, QLog, pqattest), M4 (AgentProvenance, AgentSight) va M5 (tombstone, draft-sharif,
   Agent Flight Recorder) hammasi 2026-10-17 holatida ochiq manbalarda bor [F].
2. **Ed25519 + ML-DSA-65 gibrid** imzoni ishlaydigan vositada amalga oshirgan loyiha topilmadi.
   draft-sharif'da gibrid faqat spec darajasida va **ES256** bilan. asqav, QLog va pqattest faqat
   ML-DSA ishlatadi. trustatom'da PQ kosignatura hali tekshirilmaydi [F].
3. Windows'da native ishlaydigan **"aytdi va qildi"** solishtiruvi topilmadi. AgentProvenance
   Windows'da faqat WSL orqali ishlaydi [F].
4. **Crypto-shredding** (har sessiyaga alohida kalit + kalitni o'chirgandan keyin ham zanjir
   tekshiriladi) ishlaydigan agent vositasida topilmadi. Bu faqat maqolalarda, draft'larda
   (tombstone) va 1 ⭐li loyihada bor [F/I].

### 12.3. Xulosa [T]

- **"TAMGA birinchi bo'lib … birlashtiradi" degan da'vo 2026-10-17 holatida biz topgan ma'lumotlarga
  zid emas.** Beshala mezonni bitta lokal vositada birlashtirgan loyiha topilmadi.
  Ammo bu **yo'qlikning isboti emas**: qidiruv ingliz tilidagi ochiq vebda bo'ldi, yopiq
  mahsulotlarda e'lon qilinmagan funksiyalar bo'lishi mumkin.
- **Bo'shliq tor.** AgentProvenance beshala mezonga qisman ega. Uning yetishmayotgan qismlari:
  Windows, PQ, aniq Merkle, test vektorlari va shredding. Pipelock (931 ⭐, faol) bitta relizda
  PQ va Merkle qo'shishi mumkin. Bo'shliq **oylar** ichida yopilishi mumkin.
- **"Butun dunyo uchun yangilik" ko'lamida** kutilmagan yangi g'oya emas, balki **kombinatsiya,
  sifat va platforma** (Windows) bo'yicha farq bor. Hujjatlarda shunday deb yozilishi kerak.

### 12.4. Farqlash yo'llari (tavsiyalar)

1. **Format bo'yicha raqobatlashma, mos kel.** AAR'ning xesh qoidasi
   (`SHA-256(JCS(...))`, oldingi yozuvga havola) draft-sharif-08 bilan deyarli bir xil.
   AAR-0.1'ni **draft-sharif profili + kengaytma** sifatida yoz: Ed25519+ML-DSA-65 gibridi,
   `os.observed` hodisasi, shredding semantikasi. Pipelock'ning in-toto predicate'iga va
   OTel GenAI span'lariga eksport qo'sh. Mustaqil standart yaratishdan ko'ra mos kelish
   kuchliroq pozitsiya beradi.
2. **Nom to'qnashuvi.** "Agent Action Receipt" (Pipelock/pipelab) va Pipelock'dagi "AARP"
   profili "AAR" bilan chalkashtirilishi mumkin. F1 dan oldin nomni tekshir:
   `AAR` qolsinmi yoki `TAMGA Record` bo'lsinmi?
3. **M4'ni asosiy farq qil.** Admin huquqisiz, Windows-native "aytdi va qildi" solishtiruvi
   (ETW / QARCHIG'AY tajribasi) hech kimda yo'q. Demo stsenariysi shu farqni ko'rsatishi kerak.
4. **Gibrid imzo "ikkalasi ham shart" qoidasi bilan.** NIST ACVP/KAT vektorlari, ikkita mustaqil
   verifikator (Rust + Python) va umumiy conformance korpusi kerak. Pipelock 4 tilda
   verifikator bilan shu darajaga chiqqan, TAMGA undan past bo'lmasligi kerak.
5. **Shredding uchun test vektori.** Ommaviy vektor qo'sh: "kalit o'chirildi → payload o'qilmaydi
   → zanjir va STH baribir tekshiriladi". draft-sharif'dagi tombstone semantikasi bilan birlashtir.
6. **Tashqi guvohni o'zing yozma.** Rekor v2, RFC 3161 TSA yoki SCITT (RFC 9943) dan foydalan.
   Bu PLAN.md §9 dagi ochiq savolga javob beradi.
7. **Regulyatsiyani oshirib yuborma.** Matnda "EU AI Act 12-modda (2027-12-02 dan) uchun
   tayyorgarlik" deb yoz, "avgust 2026 majburiyati" deb emas. Asosiy qiymat: insident forensikasi
   va dalil to'plami.
8. **O'lchanadigan sifat.** Agent Flight Recorder har hodisaga ~48 µs sarflaydi. TAMGA'ning
   <20 ms p99 hook byudjeti va tamper testlari ommaviy benchmark bilan ko'rsatilsin.

### 12.5. F1 dan oldin o'qish kerak

- draft-sharif-agent-audit-trail-08 to'liq matni, ayniqsa §5 (recorder mustaqilligi), §6 (zanjir,
  imzo, Merkle) va §9.3 (tombstone).
- Pipelock `docs/specs/in-toto-agent-action-receipt-v0.1.md` va `sdk/conformance/` korpusi.
- AgentProvenance `intent` paketi: Intent-Runtime Diff modeli.
- asqav test vektorlari (`asqav-03-chain-link`): mos kelishni sinash uchun.

// «Hakam uchun ish papkasi» (uy/SPEC 2F.8, U13): bitta PDF — mundarija, sahifa raqamlari.
// Bo'limlar: nizo va talablar, amaldagi shartnoma va versiyalar, hisob yozuvlari va zanjir
// tekshiruvi, ko'rik bayonnomalari, vazifa hodisalari, hakam qarori.
#import "common.typ": *

#let data = json("data.json")
#let L = data.labels
#show: doc => setup(doc, data)
// Sarlavha keyingi matndan sahifa oxirida ajralib qolmasin.
#show heading.where(level: 1): h => block(sticky: true, above: 16pt, below: 6pt)[
  #text(size: 13pt, weight: "bold")[#h.body]
]
#show heading.where(level: 2): h => block(sticky: true, above: 10pt, below: 4pt)[
  #text(size: 11pt, weight: "bold")[#h.body]
]

#title-block(L.at("folder.title"), data.name)

#kv((
  (L.at("contract.kind"), L.at("ptype." + data.kind)),
  (L.at("folder.arbiter"), data.arbiter),
  (L.at("folder.openedOn"), data.openedOn),
))

#block(fill: rgb("#F0EEE6"), inset: 10pt, radius: 4pt, width: 100%)[
  #text(size: 9.5pt)[#L.at("folder.purpose")]
]

#outline(title: L.at("folder.toc"), depth: 1, indent: 0pt)

#let entries-table(rows) = if rows.len() == 0 [
  #text(fill: muted)[—]
] else {
  table(
    columns: (auto, auto, 1fr, auto),
    table.header(
      text(weight: "bold")[#L.at("col.date")],
      text(weight: "bold")[#L.at("venture.kind")],
      text(weight: "bold")[#L.at("venture.note")],
      text(weight: "bold")[#L.at("col.amount")],
    ),
    ..rows.map(e => (
      [#e.date],
      [#L.at("ventry." + e.kind)#if e.category != none [ · #L.at("vcat." + e.category)]],
      [#e.note],
      align(right)[#e.amount],
    )).flatten(),
  )
}

= 1. #L.at("folder.s1")
#kv((
  (L.at("folder.subject"), data.subject),
  (L.at("folder.clauses"), data.clauses),
  (L.at("folder.openedBy"), data.openedBy),
))
#for c in data.claims [
  == #L.at("folder.claimOf") #c.party
  #c.claim
]

= 2. #L.at("folder.s2")
#kv(data.terms.map(t => (L.at(t.at(0)), t.at(1))))
== #L.at("folder.versions")
#table(
  columns: (auto, auto, auto, auto, 1fr),
  table.header(
    text(weight: "bold")[#L.at("contract.version")],
    text(weight: "bold")[#L.at("col.date")],
    text(weight: "bold")[#L.at("contract.hash")],
    text(weight: "bold")[#L.at("folder.signatures")],
    text(weight: "bold")[#L.at("venture.note")],
  ),
  ..data.versions.map(v => (
    [#v.no#if v.in_force [ #text(size: 8.5pt, fill: accent)[(#L.at("folder.inForce"))]]],
    [#v.date],
    [#v.hash_code],
    [#v.signatures],
    [#L.at("vnote." + v.note, default: v.note)],
  )).flatten(),
)

= 3. #L.at("folder.s3")
#block(stroke: 0.6pt + (if data.chainOk { rule } else { accent }), inset: 8pt, radius: 4pt, width: 100%)[
  #L.at(if data.chainOk { "folder.chainOk" } else { "folder.chainBroken" }) \
  #text(size: 9pt, fill: muted)[#L.at("folder.chainEntries"): #data.chainEntries · #L.at("chain.title"): #data.chainCode]
]
#for p in data.periods [
  == #L.at("venture.period") #p.title
  #kv(p.totals.map(t => (L.at(t.at(0)), t.at(1))))
  #entries-table(p.entries)
]

= 4. #L.at("folder.s4")
#if data.reviews.len() == 0 [
  #text(fill: muted)[—]
] else {
  table(
    columns: (auto, 1fr, auto, 1.8fr, 1fr),
    table.header(
      text(weight: "bold")[#L.at("protocol.no")],
      text(weight: "bold")[#L.at("protocol.range")],
      text(weight: "bold")[#L.at("protocol.heldOn")],
      text(weight: "bold")[#L.at("protocol.acks")],
      text(weight: "bold")[#L.at("folder.integrity")],
    ),
    ..data.reviews.map(r => (
      [#r.no], [#r.range], [#r.held_on],
      [#for a in r.acks [#a.party: #L.at("verdict." + a.verdict)#if a.note != "" [ — #a.note] \ ]],
      [#L.at("integrity." + r.integrity) \ #text(size: 8pt, fill: muted)[#r.chain_code]],
    )).flatten(),
  )
}

= 5. #L.at("folder.s5")
#if data.incidents.len() == 0 [
  #text(fill: muted)[#L.at("protocol.noIncidents")]
] else {
  for i in data.incidents [
    #text(weight: "bold")[#i.date — #i.duty] (#i.party) · #L.at("istatus." + i.status) \
    #i.reason#if i.solution != "" [ \ #text(fill: muted)[#L.at("protocol.solution"):] #i.solution]
    #v(4pt)
  ]
}

= 6. #L.at("folder.s6")
#if data.decision == none [
  #text(fill: muted)[#L.at("folder.noDecision")]
] else {
  let d = data.decision
  kv((
    (L.at("folder.decidedOn"), d.decided_on),
    (L.at("folder.arbiter"), d.arbiter),
    (L.at("folder.outcome"), L.at("outcome." + d.outcome)),
  ))
  [#d.decision]
}

#v(12pt)
#text(size: 9pt, fill: muted)[#L.at("folder.notLegal")]

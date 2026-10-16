// Ochiq hisob ko'rigi bayonnomasi (uy/SPEC 2F.5, U13): davr yozuvlari, yakun, ochiq hodisalar,
// tomonlar belgisi. Oxirida o'sha paytdagi zanjir boshi (QR + qisqa kod, 6.5) — bayonnomadan keyin
// o'tmishdagi yozuvni sezdirmasdan o'zgartirib bo'lmaydi.
#import "common.typ": *

#let data = json("data.json")
#let L = data.labels
#show: doc => setup(doc, data)

#title-block(L.at("protocol.title"), data.name)

#kv((
  (L.at("protocol.no"), str(data.reviewNo)),
  (L.at("protocol.range"), data.range),
  (L.at("protocol.heldOn"), data.heldOn),
  (L.at("protocol.reason"), L.at("preason." + data.reason)),
  (L.at("contract.version"), data.version),
))

#section(L.at("protocol.totals"))
#kv(data.totals.map(t => (L.at(t.at(0)), t.at(1))))

#section(L.at("venture.entries"))
#if data.entries.len() == 0 [
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
    ..data.entries.map(e => (
      [#e.date],
      [#L.at("ventry." + e.kind)#if e.category != none [ · #L.at("vcat." + e.category)]],
      [#e.note],
      align(right)[#e.amount],
    )).flatten(),
  )
}

#section(L.at("protocol.incidents"))
#if data.incidents.len() == 0 [
  #text(fill: muted)[#L.at("protocol.noIncidents")]
] else {
  for i in data.incidents [
    #text(weight: "bold")[#i.date — #i.duty] (#i.party) \
    #i.reason#if i.solution != "" [ \ #text(fill: muted)[#L.at("protocol.solution"):] #i.solution]
    #v(4pt)
  ]
}

#section(L.at("protocol.acks"))
#table(
  columns: (1fr, auto, 2fr),
  table.header(
    text(weight: "bold")[#L.at("contract.party")],
    text(weight: "bold")[#L.at("protocol.verdict")],
    text(weight: "bold")[#L.at("protocol.note")],
  ),
  ..data.acks.map(a => (
    [#a.party],
    [#L.at("verdict." + a.verdict)],
    [#a.note],
  )).flatten(),
)

#block(stroke: 0.6pt + (if data.chainOk { rule } else { accent }), inset: 8pt, radius: 4pt, width: 100%)[
  #text(size: 9.5pt)[#L.at(if data.chainOk { "protocol.chainOk" } else { "protocol.chainBroken" })]
]

#chain-block(L, data.chain_short_code)

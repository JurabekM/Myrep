// Sheriklik shartnomasi (uy/SPEC 2E.2, 2F.2–2F.3, U11): 9 savol, sheriklik shartlari, buyout,
// guvohlar va shu qurilmada chizilgan imzolar. Imzo rasmlari alohida SVG fayl sifatida beriladi.
#import "common.typ": *

#let data = json("data.json")
#let L = data.labels
#show: doc => setup(doc, data)

#title-block(L.at("contract.title"), data.name)

#kv((
  (L.at("contract.kind"), L.at("ptype." + data.kind)),
  (L.at("contract.version"), if data.version != none { data.version } else { L.at("contract.draft") }),
  (L.at("contract.hash"), data.hashCode),
))

#block(fill: rgb("#F0EEE6"), inset: 10pt, radius: 4pt, width: 100%)[
  #text(size: 9.5pt)[#L.at("contract.principle." + data.kind)]
]

#if data.reviewPending {
  v(6pt)
  block(stroke: 0.6pt + accent, inset: 8pt, radius: 4pt, width: 100%)[
    #text(size: 9pt, fill: accent)[#L.at("contract.reviewPending")]
  ]
}

#let clause(n, title, c, body) = {
  section(str(n) + ". " + title)
  if c.status == "NOT_APPLICABLE" [
    #text(fill: muted)[#L.at("contract.na"): #c.reason]
  ] else if c.status == "UNANSWERED" [
    #text(fill: accent)[#L.at("contract.unanswered")]
  ] else {
    body
    if c.rows.len() > 0 { kv(c.rows.map(r => (L.at(r.at(0)), r.at(1)))) }
  }
}

#section("1. " + L.at("contract.q1"))
#table(
  columns: (1fr, auto, auto, auto),
  table.header(
    text(weight: "bold")[#L.at("contract.party")],
    text(weight: "bold")[#L.at("contract.role")],
    text(weight: "bold")[#L.at("contract.capital")],
    text(weight: "bold")[#L.at("contract.profitShare")],
  ),
  ..data.parties.map(p => (
    [#p.name],
    [#L.at("prole." + p.role)],
    align(right)[#p.capital],
    align(right)[#p.profit_share],
  )).flatten(),
)

#section("2. " + L.at("contract.q2"))
#if data.capital.len() > 0 {
  table(
    columns: (auto, auto, 1fr, auto),
    ..data.capital.map(c => (
      [#c.party],
      [#L.at("capital." + c.kind)],
      [#c.description],
      align(right)[#c.amount],
    )).flatten(),
  )
}
#for p in data.parties.filter(p => p.role != "CAPITAL_PROVIDER") [
  #p.name — #L.at("contract.labor") \
]

#clause(3, L.at("contract.q3"), data.duties)[
  #for d in data.dutyRows [
    #text(weight: "bold")[#d.title] — #d.owner \
    #text(fill: muted)[#L.at("contract.breach"):] #d.breach
    #v(4pt)
  ]
]

#section("4. " + L.at("contract.q4"))
#for p in data.parties [
  #p.name: #text(weight: "bold")[#p.profit_share] \
]
#text(size: 9pt, fill: muted)[#L.at("contract.noFixedReturn")]

#section("5. " + L.at("contract.q5"))
#L.at("contract.loss." + data.kind)
#for p in data.parties.filter(p => p.loss_share != none) [
  \ #p.name: #text(weight: "bold")[#p.loss_share]
]
#if data.negligence != none [
  \ #text(fill: muted)[#L.at("contract.negligence"):] #data.negligence
]

#clause(6, L.at("contract.q6"), data.custody)[]

#clause(7, L.at("contract.q7"), data.exit)[]

#if data.buyout != none {
  let b = data.buyout
  section(L.at("contract.buyout"))
  kv(((L.at("contract.buyer"), b.buyer), (L.at("contract.seller"), b.seller)))
  table(
    columns: (auto, auto, 1fr, 1fr, auto, auto),
    table.header(
      text(weight: "bold")[#L.at("col.n")],
      text(weight: "bold")[#L.at("col.date")],
      text(weight: "bold")[#L.at("contract.payment")],
      text(weight: "bold")[#L.at("contract.remaining")],
      text(weight: "bold")[#b.seller],
      text(weight: "bold")[#b.buyer],
    ),
    ..b.rows.map(r => (
      [#r.period], [#r.date], align(right)[#r.payment], align(right)[#r.remaining],
      align(right)[#r.seller], align(right)[#r.buyer],
    )).flatten(),
  )
  text(size: 9pt, fill: muted)[#L.at("contract.buyoutPricing")]
}

#clause(8, L.at("contract.q8"), data.arbiter)[]

#clause(9, L.at("contract.q9"), data.term)[]

#if data.witnesses.len() > 0 {
  section(L.at("contract.witnesses"))
  for w in data.witnesses [
    #w \
  ]
}

// Imzolar: chizilgan bo'lsa — rasm, bo'lmasa — qo'lda imzolash uchun chiziq.
#block(breakable: false, width: 100%)[
  #section(L.at("signatures"))
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 24pt,
    row-gutter: 18pt,
    ..data.signers.map(s => block(width: 100%)[
      #box(height: 40pt, width: 100%)[
        #if s.file != none { align(bottom)[#image(s.file, height: 40pt)] }
      ]
      #line(length: 100%, stroke: 0.6pt + ink)
      #text(size: 9pt, fill: muted)[#L.at("signer." + s.role)] \
      #text(size: 10pt)[#s.name]
      #if s.signedAt != none [ \ #text(size: 8.5pt, fill: muted)[#s.signedAt]]
    ]),
  )
]

// Qarz tilxati = Agreement(type = LOAN) (uy/SPEC 2D.5, BARAKA_OILASI U8).
#import "common.typ": *

#let data = json("data.json")
#let L = data.labels
#show: doc => setup(doc, data)

#title-block(L.at("receipt.title"), data.place + ", " + data.issued_on)

#kv((
  (L.at("receipt.lender"), data.lender),
  (L.at("receipt.borrower"), data.borrower),
  (L.at("receipt.amount"), data.amount),
  (L.at("receipt.due"), data.due_on),
))

#block(fill: rgb("#F0EEE6"), inset: 10pt, radius: 4pt, width: 100%)[#L.at("receipt.interestFree")]

#if data.schedule.len() > 0 {
  section(L.at("receipt.schedule"))
  table(
    columns: (auto, 1fr, 1fr),
    table.header(
      text(weight: "bold")[#L.at("col.n")],
      text(weight: "bold")[#L.at("col.date")],
      text(weight: "bold")[#L.at("col.amount")],
    ),
    ..data.schedule.enumerate().map(((i, r)) => ([#(i + 1)], [#r.date], [#r.amount])).flatten(),
  )
}

#if data.note != none {
  section(L.at("receipt.note"))
  [#data.note]
}

#signatures(
  L.at("signatures"),
  (
    (role: L.at("role.lender"), name: data.lender),
    (role: L.at("role.borrower"), name: data.borrower),
    ..data.witnesses.map(w => (role: L.at("role.witness"), name: w)),
  ),
)

#chain-block(L, data.chain_short_code)

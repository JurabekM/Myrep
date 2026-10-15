// Marosim smetasi (uy/SPEC 2D.8, U10): tanlangan stsenariy, moliyalash manbalari va oilaviy muhokama.
#import "common.typ": *

#let data = json("data.json")
#let L = data.labels
#show: doc => setup(doc, data)

#title-block(L.at("estimate.title"), data.name)

#kv((
  (L.at("estimate.kind"), L.at("kind." + data.kind)),
  (L.at("estimate.date"), if data.date != none { data.date } else { "—" }),
  (L.at("estimate.scenario"), data.scenario),
  (L.at("estimate.guests"), data.guests),
  (L.at("estimate.status"), L.at("status." + data.status)),
))

#section(L.at("estimate.lines"))
#table(
  columns: (auto, 1fr, auto, auto, auto),
  table.header(
    text(weight: "bold")[#L.at("col.n")],
    text(weight: "bold")[#L.at("estimate.item")],
    text(weight: "bold")[#L.at("estimate.basis")],
    text(weight: "bold")[#L.at("col.amount")],
    text(weight: "bold")[#L.at("estimate.source")],
  ),
  ..data.lines.enumerate().map(((i, l)) => (
    [#(i + 1)],
    [#l.title],
    [#if l.kind == "PER_GUEST" { l.unit + " × " + l.guests } else { L.at("estimate.oneOff") }],
    align(right)[#l.amount],
    [#L.at("source." + l.source)],
  )).flatten(),
)

#section(L.at("estimate.sources"))
#kv(data.totals.map(t => (L.at("source." + t.source), t.amount)) + ((L.at("estimate.total"), data.total),))

#if data.payoff_months != none {
  block(fill: rgb("#F0EEE6"), inset: 10pt, radius: 4pt, width: 100%)[
    #L.at("estimate.payoff"): #text(weight: "bold")[#data.payoff_months #L.at("estimate.months")]
    #if data.payoff_date != none [ (#data.payoff_date)]
  ]
}

#if data.answers.len() > 0 {
  section(L.at("estimate.discussion"))
  for a in data.answers [
    #text(fill: muted)[#L.at("question." + a.key)] \
    #a.note
    #v(4pt)
  ]
}

#if data.agreed.len() > 0 {
  section(L.at("estimate.agreed"))
  for a in data.agreed [
    #a.name — #a.date \
  ]
}

#signatures(L.at("signatures"), data.adults.map(n => (role: L.at("estimate.member"), name: n)))

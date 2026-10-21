// Sheriklik davri hisoboti (uy/SPEC 2E.3, U12): kirim, xarajat, natija, taqsimot, buyout holati.
// Sherikka shaffoflik uchun; oxirida zanjir boshi (QR + qisqa kod, 6.5).
#import "common.typ": *

#let data = json("data.json")
#let L = data.labels
#show: doc => setup(doc, data)

#title-block(L.at("venture.title"), data.name)

#kv((
  (L.at("contract.kind"), L.at("ptype." + data.kind)),
  (L.at("venture.period"), str(data.periodNo) + ": " + data.start + " — " + data.end),
  (L.at("contract.version"), data.version),
))

#section(L.at("venture.totals"))
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
      [#e.note#if e.attachments > 0 [ #text(fill: muted)[(#L.at("venture.files"): #e.attachments)]]],
      align(right)[#e.amount],
    )).flatten(),
  )
}

#section(L.at("venture.distribution"))
#table(
  columns: (1fr, auto, auto, auto, auto),
  table.header(
    text(weight: "bold")[#L.at("contract.party")],
    text(weight: "bold")[#L.at("venture.share")],
    text(weight: "bold")[#L.at("venture.recovered")],
    text(weight: "bold")[#L.at("venture.payout")],
    text(weight: "bold")[#L.at("venture.capitalAfter")],
  ),
  ..data.parties.map(p => (
    [#p.name \ #text(size: 8.5pt, fill: muted)[#L.at("prole." + p.role)]],
    align(right)[#p.share],
    align(right)[#p.recovered],
    align(right)[#p.payout],
    align(right)[#p.capital_after],
  )).flatten(),
)
#text(size: 9pt, fill: muted)[#L.at("venture.policy." + data.lossPolicy)]

#if data.negligence != none {
  section(L.at("venture.negligence"))
  [#data.negligence]
}

#if data.buyout != none {
  let b = data.buyout
  section(L.at("contract.buyout"))
  kv((
    (L.at("contract.buyer"), b.buyer),
    (L.at("contract.seller"), b.seller),
    (L.at("venture.buyoutPaid"), b.paid),
    (L.at("venture.buyoutUnpaid"), b.unpaid),
    (L.at("contract.payment"), b.amount),
    (L.at("venture.buyoutProgress"), b.progress),
  ))
  text(size: 9pt, fill: muted)[#L.at("contract.buyoutPricing")]
}

#chain-block(L, data.chain_short_code)

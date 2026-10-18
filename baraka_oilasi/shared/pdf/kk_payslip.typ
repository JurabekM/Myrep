// Xodim bilan oylik hisob varaqchasi (kasbkor/SPEC 7.2, K6): haq, avansdan ushlangan, to'langan va
// qoldiq; oxirida ikki tomon imzosi. Avans foizsiz, kechikish uchun jarima yo'q.
#import "common.typ": *

#let data = json("data.json")
#let L = data.labels
#show: doc => setup(doc, data)

#title-block(L.at("kkslip.title"), data.business)

#kv((
  (L.at("kkslip.employee"), if data.role == none { data.employee } else { data.employee + " — " + data.role }),
  (L.at("kkslip.period"), data.period),
))

#section(L.at("kkslip.totals"))
#kv(data.rows.map(r => (L.at(r.at(0)), r.at(1))))
#text(size: 9pt, fill: muted)[#L.at("kkslip.balanceHint")]

#section(L.at("kkslip.payments"))
#if data.payments.len() == 0 [
  #text(fill: muted)[#L.at("kkslip.noPayments")]
] else {
  table(
    columns: (auto, 1fr, auto),
    table.header(
      text(fill: muted)[#L.at("kkslip.date")],
      text(fill: muted)[#L.at("kkslip.kind")],
      text(fill: muted)[#L.at("kkslip.amount")],
    ),
    ..data.payments.map(p => (p.at(0), L.at(p.at(1)), align(right)[#p.at(2)])).flatten(),
  )
}

#v(4pt)
#text(size: 9pt, fill: muted)[#L.at("kkslip.noPenalty")]

#signatures(L.at("kkslip.signatures"), (
  (role: L.at("kkagr.signer.employer"), name: data.business),
  (role: L.at("kkslip.signer.employee"), name: data.employee),
))

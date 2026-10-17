// Kasb-kor «Hisob kuni» bayonnomasi (kasbkor/SPEC 4.5, K3): oy yakunlari → soliq zaxirasi → egasi maoshi →
// qolgan pul → taqsimot. Yopilgandan keyin o'zgarmaydi; oxirida bayonnomalar zanjiri boshi (QR + kod).
#import "common.typ": *

#let data = json("data.json")
#let L = data.labels
#show: doc => setup(doc, data)

#title-block(L.at("kkclose.title"), data.business)

#kv((
  (L.at("kkclose.period"), data.period),
  (L.at("kkclose.closedOn"), data.closedOn),
))

#section(L.at("kkclose.totals"))
#kv(data.totals.map(t => (L.at(t.at(0)), t.at(1))))

#section(L.at("kkclose.rule"))
#kv(data.rule.map(t => (L.at(t.at(0)), t.at(1))))

#section(L.at("kkclose.allocation"))
#if data.allocation == none [
  #text(fill: muted)[#L.at("kkclose.noAllocation")]
] else {
  kv(data.allocation.map(t => (L.at(t.at(0)), t.at(1))))
}

#if data.explanation != none {
  section(L.at("kkclose.explanation"))
  [#data.explanation]
}

#for n in data.notes {
  par(text(size: 9pt, fill: muted)[#L.at(n)])
}

#text(size: 9pt, fill: muted)[#L.at("kkclose.disclaimer")]

#chain-block(L, data.chain_short_code)

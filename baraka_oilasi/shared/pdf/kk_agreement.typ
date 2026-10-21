// Kasb-kor xodim yoki ta'minotchi kelishuvi (kasbkor/SPEC 7, K6): 9 savol bandlari shablondan
// (`shared/content/templates`), matnlar yadroda to'ldirilgan. Shablon tekshirilmagan bo'lsa — belgi.
#import "common.typ": *

#let data = json("data.json")
#let L = data.labels
#show: doc => setup(doc, data)
#set page(background: if data.reviewPending {
  rotate(-35deg, text(size: 46pt, fill: rgb("#E8E5DA"), weight: "bold")[#L.at("kkagr.watermark")])
})

#title-block(data.title, data.business)

#kv((
  (L.at("kkagr.version"), if data.version == none { L.at("kkagr.draft") } else { data.version }),
  ..if data.signedOn != none { ((L.at("kkagr.signedOn"), data.signedOn),) },
  ..if data.effectiveFrom != none { ((L.at("kkagr.effectiveFrom"), data.effectiveFrom),) },
  ..if data.hashCode != none { ((L.at("kkagr.code"), data.hashCode),) },
))

#if data.reviewPending {
  block(stroke: 0.6pt + accent, inset: 8pt, radius: 4pt, width: 100%)[
    #text(size: 9pt, fill: accent)[#L.at("kkagr.reviewPending")]
  ]
}

#for c in data.clauses {
  section(str(c.n) + ". " + c.label)
  par(c.text)
}

#v(6pt)
#text(size: 9pt, fill: muted)[#data.disclaimer]

#signatures(L.at("kkagr.signatures"), data.signers)

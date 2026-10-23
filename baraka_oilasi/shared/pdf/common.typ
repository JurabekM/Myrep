// Umumiy bloklar (BARAKA_OILASI 9). Ma'lumot `data.json` dan o'qiladi — foydalanuvchi matni
// hech qachon typst kodi sifatida bajarilmaydi. PDF chop etish uchun: har doim oq fonda.

#let ink = rgb("#141413")
#let muted = rgb("#5E5D59")
#let rule = rgb("#DAD8CE")
#let accent = rgb("#A9502F")

#let setup(doc, data) = {
  let lang = if data.locale == "ru" { "ru" } else { "uz" }
  set document(title: data.title, author: "Baraka Dastur")
  set page(
    paper: "a4",
    margin: (x: 2cm, top: 2cm, bottom: 2.4cm),
    footer: context [
      #set text(size: 8pt, fill: muted)
      #data.labels.at("disclaimer")
      #h(1fr)
      #counter(page).display("1 / 1", both: true)
    ],
  )
  set text(font: "Noto Sans", size: 10.5pt, fill: ink, lang: lang)
  set par(leading: 0.7em)
  set table(stroke: 0.5pt + rule, inset: 6pt)
  doc
}

#let title-block(title, subtitle) = {
  text(font: "Noto Serif", size: 20pt, weight: "bold")[#title]
  if subtitle != none {
    linebreak()
    text(size: 10pt, fill: muted)[#subtitle]
  }
  v(4pt)
  line(length: 100%, stroke: 1pt + accent)
  v(8pt)
}

#let kv(rows) = table(
  columns: (38%, 1fr),
  stroke: none,
  inset: (x: 0pt, y: 5pt),
  ..rows.map(r => (text(fill: muted)[#r.at(0)], text(weight: "bold")[#r.at(1)])).flatten(),
)

// Bo'lim sarlavhasi sahifa oxirida yolg'iz qolmaydi (`sticky` — keyingi blok bilan birga ko'chadi).
#let section(title) = block(sticky: true, above: 14pt, below: 6pt)[
  #text(size: 12pt, weight: "bold")[#title]
]

// Imzolar sahifalar orasida bo'linmaydi: sarlavha imzo chiziqlaridan ajralib qolmasin.
#let signatures(title, signers) = block(breakable: false, width: 100%)[
  #section(title)
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 24pt,
    row-gutter: 22pt,
    ..signers.map(s => block(width: 100%)[
      #v(26pt)
      #line(length: 100%, stroke: 0.6pt + ink)
      #text(size: 9pt, fill: muted)[#s.role] \
      #text(size: 10pt)[#s.name]
    ]),
  )
]

// Zanjir boshi: QR (to'liq xesh) va qisqa kod (6.5). Kod bo'lmasa — blok chiqmaydi.
#let chain-block(labels, code) = if code != none {
  v(14pt)
  block(stroke: 0.6pt + rule, inset: 10pt, radius: 4pt, width: 100%, grid(
    columns: (auto, 1fr),
    column-gutter: 14pt,
    image("qr.svg", width: 2.4cm),
    align(horizon)[
      #text(weight: "bold")[#labels.at("chain.title")] \
      #text(size: 14pt, tracking: 1.5pt, weight: "bold")[#code] \
      #v(2pt)
      #text(size: 8.5pt, fill: muted)[#labels.at("chain.hint")]
    ],
  ))
}

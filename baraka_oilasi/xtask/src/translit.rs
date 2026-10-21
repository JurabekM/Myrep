//! Oʻzbek lotin → kirill transliteratsiyasi (`uz-Cyrl` uchun). ICU plaseholderlari (`{...}`)
//! oʻzgarmaydi. Istisnolar `shared/i18n/uz-Cyrl.overrides.json` da qoʻlda beriladi.

const APOS: [char; 4] = ['\'', '\u{2018}', '\u{2019}', '\u{02BB}'];

fn is_apos(c: Option<&char>) -> bool {
    c.is_some_and(|c| APOS.contains(c))
}

fn map_single(c: char) -> Option<&'static str> {
    Some(match c {
        'a' => "а",
        'b' => "б",
        'd' => "д",
        'e' => "е",
        'f' => "ф",
        'g' => "г",
        'h' => "ҳ",
        'i' => "и",
        'j' => "ж",
        'k' => "к",
        'l' => "л",
        'm' => "м",
        'n' => "н",
        'o' => "о",
        'p' => "п",
        'q' => "қ",
        'r' => "р",
        's' => "с",
        't' => "т",
        'u' => "у",
        'v' => "в",
        'x' => "х",
        'y' => "й",
        'z' => "з",
        'c' => "с",
        'w' => "в",
        '\u{02BC}' => "ъ",
        _ => return None,
    })
}

fn upper_first(s: &str, all: bool) -> String {
    if all {
        return s.to_uppercase();
    }
    let mut it = s.chars();
    match it.next() {
        Some(f) => f.to_uppercase().chain(it).collect(),
        None => String::new(),
    }
}

pub fn to_cyrillic(input: &str) -> String {
    let chars: Vec<char> = input.chars().collect();
    let mut out = String::with_capacity(input.len() * 2);
    let mut i = 0;
    let mut depth = 0usize;
    while i < chars.len() {
        let c = chars[i];
        if c == '{' {
            depth += 1;
        }
        if depth > 0 {
            if c == '}' {
                depth -= 1;
            }
            out.push(c);
            i += 1;
            continue;
        }
        let lower = c.to_lowercase().next().unwrap_or(c);
        let is_upper = c.is_uppercase();
        let next = chars.get(i + 1);
        let next_lower = next.map(|n| n.to_lowercase().next().unwrap_or(*n));
        let next_upper = next.is_some_and(|n| n.is_uppercase());
        let word_start = i == 0 || !chars[i - 1].is_alphabetic() && !APOS.contains(&chars[i - 1]);

        let (piece, consumed): (&str, usize) = match (lower, next_lower) {
            ('o', _) if is_apos(next) => ("ў", 2),
            ('g', _) if is_apos(next) => ("ғ", 2),
            ('s', Some('h')) => ("ш", 2),
            ('c', Some('h')) => ("ч", 2),
            ('y', Some('o')) if !is_apos(chars.get(i + 2)) => ("ё", 2),
            ('y', Some('u')) => ("ю", 2),
            ('y', Some('a')) => ("я", 2),
            ('y', Some('e')) => ("е", 2),
            ('e', _) if word_start => ("э", 1),
            (l, _) => match map_single(l) {
                Some(p) => (p, 1),
                None => {
                    out.push(c);
                    i += 1;
                    continue;
                }
            },
        };
        if is_upper {
            out.push_str(&upper_first(piece, consumed == 2 && next_upper));
        } else {
            out.push_str(piece);
        }
        i += consumed;
    }
    out
}

#[cfg(test)]
mod tests {
    use super::to_cyrillic;

    #[test]
    fn words() {
        assert_eq!(to_cyrillic("Oʻzingizga toʻlangan"), "Ўзингизга тўланган");
        assert_eq!(
            to_cyrillic("Shundan {amount} — kelajagingiz uchun"),
            "Шундан {amount} — келажагингиз учун"
        );
        assert_eq!(to_cyrillic("Yoʻl"), "Йўл");
        assert_eq!(to_cyrillic("Sovgʻalar"), "Совғалар");
        assert_eq!(to_cyrillic("Ehtiyot, maʼlumot"), "Эҳтиёт, маълумот");
        assert_eq!(to_cyrillic("Yangi PIN"), "Янги ПИН");
        assert_eq!(to_cyrillic("Choyxona va shirinlik"), "Чойхона ва ширинлик");
        assert_eq!(to_cyrillic("yuz yetti"), "юз етти");
    }
}

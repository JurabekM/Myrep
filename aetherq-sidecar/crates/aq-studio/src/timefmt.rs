//! Sana/vaqt yordamchilari (tashqi crate'siz): RFC 3339 (Go `time.Time` JSON bilan mos) va mahalliy vaqt.

use std::time::{SystemTime, UNIX_EPOCH};

pub fn now_unix() -> i64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs() as i64).unwrap_or(0)
}

/// Kunlar (1970-01-01 dan) — Howard Hinnant algoritmi.
pub fn days_from_civil(y: i64, m: u32, d: u32) -> i64 {
    let y = if m <= 2 { y - 1 } else { y };
    let era = if y >= 0 { y } else { y - 399 } / 400;
    let yoe = (y - era * 400) as u64;
    let mp = ((m + 9) % 12) as u64;
    let doy = (153 * mp + 2) / 5 + d as u64 - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146_097 + doe as i64 - 719_468
}

pub fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if m <= 2 { y + 1 } else { y }, m, d)
}

/// UTC sekund → "2026-10-17T12:34:56Z".
pub fn rfc3339(t: i64) -> String {
    let (days, secs) = (t.div_euclid(86_400), t.rem_euclid(86_400));
    let (y, m, d) = civil_from_days(days);
    format!("{y:04}-{m:02}-{d:02}T{:02}:{:02}:{:02}Z", secs / 3600, (secs % 3600) / 60, secs % 60)
}

/// RFC 3339 (Go `time.Time` JSON): kasr sekund va `Z` yoki `±hh:mm` bilan.
pub fn parse_rfc3339(s: &str) -> Option<i64> {
    let s = s.trim();
    let b = s.as_bytes();
    if b.len() < 20 || b[4] != b'-' || b[7] != b'-' || (b[10] != b'T' && b[10] != b't') || b[13] != b':' || b[16] != b':' {
        return None;
    }
    let num = |a: usize, z: usize| s.get(a..z)?.parse::<i64>().ok();
    let (y, mo, d, h, mi, se) = (num(0, 4)?, num(5, 7)?, num(8, 10)?, num(11, 13)?, num(14, 16)?, num(17, 19)?);
    if !(1..=12).contains(&mo) || !(1..=31).contains(&d) || h > 23 || mi > 59 || se > 60 {
        return None;
    }
    let mut i = 19;
    if b.get(i) == Some(&b'.') {
        i += 1;
        while b.get(i).is_some_and(|c| c.is_ascii_digit()) {
            i += 1;
        }
    }
    let offset = match b.get(i)? {
        b'Z' | b'z' if i + 1 == b.len() => 0,
        sign @ (b'+' | b'-') if i + 6 == b.len() && b[i + 3] == b':' => {
            let oh = num(i + 1, i + 3)?;
            let om = num(i + 4, i + 6)?;
            let o = oh * 3600 + om * 60;
            if *sign == b'+' {
                o
            } else {
                -o
            }
        }
        _ => return None,
    };
    Some(days_from_civil(y, mo as u32, d as u32) * 86_400 + h * 3600 + mi * 60 + se - offset)
}

/// Mahalliy vaqt zonasi siljishi (sekund). Windows'da tizimdan, boshqa OS'da 0 (UTC).
pub fn local_offset() -> i64 {
    #[cfg(windows)]
    {
        use windows_sys::Win32::Foundation::SYSTEMTIME;
        use windows_sys::Win32::System::SystemInformation::{GetLocalTime, GetSystemTime};
        let to_unix = |t: &SYSTEMTIME| {
            days_from_civil(t.wYear as i64, t.wMonth as u32, t.wDay as u32) * 86_400
                + t.wHour as i64 * 3600
                + t.wMinute as i64 * 60
                + t.wSecond as i64
        };
        // SAFETY: ikkala funksiya faqat berilgan SYSTEMTIME tuzilmasiga yozadi.
        let (mut l, mut u): (SYSTEMTIME, SYSTEMTIME) = unsafe { (std::mem::zeroed(), std::mem::zeroed()) };
        unsafe {
            GetLocalTime(&mut l);
            GetSystemTime(&mut u);
        }
        // Daqiqaga yaxlitlaymiz (ikki chaqiruv orasidagi soniya farqini yo'qotish uchun).
        ((to_unix(&l) - to_unix(&u)) as f64 / 60.0).round() as i64 * 60
    }
    #[cfg(not(windows))]
    {
        0
    }
}

/// Mahalliy sana: "2026-10-17".
pub fn local_date(t: i64, offset: i64) -> String {
    let (y, m, d) = civil_from_days((t + offset).div_euclid(86_400));
    format!("{y:04}-{m:02}-{d:02}")
}

/// Mahalliy vaqt: "14:05:09".
pub fn local_hms(t: i64, offset: i64) -> String {
    let s = (t + offset).rem_euclid(86_400);
    format!("{:02}:{:02}:{:02}", s / 3600, (s % 3600) / 60, s % 60)
}

/// Fayl nomi uchun: "20261017-140509".
pub fn stamp(t: i64, offset: i64) -> String {
    let lt = t + offset;
    let (y, m, d) = civil_from_days(lt.div_euclid(86_400));
    let s = lt.rem_euclid(86_400);
    format!("{y:04}{m:02}{d:02}-{:02}{:02}{:02}", s / 3600, (s % 3600) / 60, s % 60)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn civil_roundtrip_and_known_dates() {
        assert_eq!(days_from_civil(1970, 1, 1), 0);
        assert_eq!(days_from_civil(2000, 3, 1), 11_017);
        for z in [-800_000i64, -1, 0, 59, 60, 11_016, 20_000, 2_932_896] {
            let (y, m, d) = civil_from_days(z);
            assert_eq!(days_from_civil(y, m, d), z, "{y}-{m}-{d}");
        }
        assert_eq!(civil_from_days(days_from_civil(2024, 2, 29)), (2024, 2, 29));
    }

    #[test]
    fn rfc3339_matches_go_format() {
        // Go: time.Date(2026,10,12,14,13,14,203000000,time.UTC) → "2026-10-12T14:13:14.203Z"
        let t = parse_rfc3339("2026-10-12T14:13:14.203Z").unwrap();
        assert_eq!(rfc3339(t), "2026-10-12T14:13:14Z");
        assert_eq!(parse_rfc3339("2026-10-12T19:13:14+05:00"), Some(t));
        assert_eq!(parse_rfc3339("2026-10-12T09:13:14-05:00"), Some(t));
        assert_eq!(parse_rfc3339(&rfc3339(1_760_000_000)), Some(1_760_000_000));
        for bad in ["", "2026-10-12", "2026-13-01T00:00:00Z", "2026-10-12T14:13:14", "2026-10-12T14:13:14Zx"] {
            assert_eq!(parse_rfc3339(bad), None, "{bad}");
        }
    }

    #[test]
    fn local_formatting() {
        let t = parse_rfc3339("2026-10-17T19:30:05Z").unwrap();
        assert_eq!(local_hms(t, 5 * 3600), "00:30:05");
        assert_eq!(local_date(t, 5 * 3600), "2026-10-18");
        assert_eq!(stamp(t, 0), "20261017-193005");
    }
}

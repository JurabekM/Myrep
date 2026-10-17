//! RFC 9162 §2.1 Merkle daraxti: ildiz, inclusion va consistency isbotlari (spec §6).
//!
//! Barglar — yozuv xeshlari; ular allaqachon `H(0x00 || ...)` ko'rinishidagi barg xeshlari.

use crate::digest::Digest;

pub const NODE_PREFIX: u8 = 0x01;

fn node(left: &Digest, right: &Digest) -> Digest {
    Digest::of(&[&[NODE_PREFIX], &left.0, &right.0])
}

/// `n` dan kichik eng katta 2 ning darajasi (`n >= 2`).
fn split(n: usize) -> usize {
    debug_assert!(n >= 2);
    1 << (usize::BITS - 1 - (n - 1).leading_zeros())
}

/// Merkle Tree Hash. Bo'sh daraxt uchun `H("")`.
pub fn root(leaves: &[Digest]) -> Digest {
    match leaves.len() {
        0 => Digest::of(&[]),
        1 => leaves[0],
        n => {
            let k = split(n);
            node(&root(&leaves[..k]), &root(&leaves[k..]))
        }
    }
}

/// `PATH(m, D[n])` — `index` bargining inclusion isboti.
pub fn inclusion_proof(index: usize, leaves: &[Digest]) -> Option<Vec<Digest>> {
    (index < leaves.len()).then(|| path(index, leaves))
}

fn path(m: usize, d: &[Digest]) -> Vec<Digest> {
    let n = d.len();
    if n <= 1 {
        return Vec::new();
    }
    let k = split(n);
    if m < k {
        let mut p = path(m, &d[..k]);
        p.push(root(&d[k..]));
        p
    } else {
        let mut p = path(m - k, &d[k..]);
        p.push(root(&d[..k]));
        p
    }
}

/// RFC 9162 §2.1.3.2 inclusion isbotini tekshirish.
pub fn verify_inclusion(
    index: u64,
    size: u64,
    leaf: &Digest,
    proof: &[Digest],
    root: &Digest,
) -> bool {
    if index >= size {
        return false;
    }
    let (mut fnode, mut snode) = (index, size - 1);
    let mut r = *leaf;
    for p in proof {
        if snode == 0 {
            return false;
        }
        if fnode & 1 == 1 || fnode == snode {
            r = node(p, &r);
            if fnode & 1 == 0 {
                while fnode & 1 == 0 && fnode != 0 {
                    fnode >>= 1;
                    snode >>= 1;
                }
            }
        } else {
            r = node(&r, p);
        }
        fnode >>= 1;
        snode >>= 1;
    }
    snode == 0 && r == *root
}

/// `PROOF(m, D[n])` — birinchi `m` barg daraxti to'liq `n` bargli daraxtning boshi ekani isboti.
/// `0 < m <= n` bo'lishi shart; `m == n` uchun isbot bo'sh.
pub fn consistency_proof(m: usize, leaves: &[Digest]) -> Option<Vec<Digest>> {
    (m >= 1 && m <= leaves.len()).then(|| subproof(m, leaves, true))
}

fn subproof(m: usize, d: &[Digest], b: bool) -> Vec<Digest> {
    let n = d.len();
    if m == n {
        return if b { Vec::new() } else { vec![root(d)] };
    }
    let k = split(n);
    if m <= k {
        let mut p = subproof(m, &d[..k], b);
        p.push(root(&d[k..]));
        p
    } else {
        let mut p = subproof(m - k, &d[k..], false);
        p.push(root(&d[..k]));
        p
    }
}

/// RFC 9162 §2.1.4.2 consistency isbotini tekshirish.
pub fn verify_consistency(
    first: u64,
    second: u64,
    first_root: &Digest,
    second_root: &Digest,
    proof: &[Digest],
) -> bool {
    if first == 0 || first > second {
        return false;
    }
    if first == second {
        return proof.is_empty() && first_root == second_root;
    }
    let mut path: Vec<Digest> = Vec::with_capacity(proof.len() + 1);
    if first.is_power_of_two() {
        path.push(*first_root);
    }
    path.extend_from_slice(proof);
    let Some((head, rest)) = path.split_first() else {
        return false;
    };

    let (mut fnode, mut snode) = (first - 1, second - 1);
    while fnode & 1 == 1 {
        fnode >>= 1;
        snode >>= 1;
    }
    let (mut fr, mut sr) = (*head, *head);
    for c in rest {
        if snode == 0 {
            return false;
        }
        if fnode & 1 == 1 || fnode == snode {
            fr = node(c, &fr);
            sr = node(c, &sr);
            if fnode & 1 == 0 {
                while fnode & 1 == 0 && fnode != 0 {
                    fnode >>= 1;
                    snode >>= 1;
                }
            }
        } else {
            sr = node(&sr, c);
        }
        fnode >>= 1;
        snode >>= 1;
    }
    fr == *first_root && sr == *second_root && snode == 0
}

#[cfg(test)]
mod tests {
    use super::*;

    fn leaves(n: usize) -> Vec<Digest> {
        (0..n)
            .map(|i| Digest::of(&[&[0u8], &(i as u64).to_be_bytes()]))
            .collect()
    }

    #[test]
    fn small_roots_follow_definition() {
        let d = leaves(3);
        assert_eq!(root(&[]), Digest::of(&[]));
        assert_eq!(root(&d[..1]), d[0]);
        assert_eq!(root(&d[..2]), node(&d[0], &d[1]));
        assert_eq!(root(&d), node(&node(&d[0], &d[1]), &d[2]));
        assert_eq!(split(2), 1);
        assert_eq!(split(5), 4);
        assert_eq!(split(8), 4);
        assert_eq!(split(9), 8);
    }

    #[test]
    fn every_inclusion_proof_verifies_and_tamper_fails() {
        for n in 1..=40 {
            let d = leaves(n);
            let r = root(&d);
            for m in 0..n {
                let p = inclusion_proof(m, &d).unwrap();
                assert!(
                    verify_inclusion(m as u64, n as u64, &d[m], &p, &r),
                    "n={n} m={m}"
                );
                let other = Digest::of(&[b"boshqa"]);
                assert!(!verify_inclusion(m as u64, n as u64, &other, &p, &r));
                // Eslatma: isbot daraxt o'lchamini o'zi bog'lamaydi (masalan, n=3, m=0 isboti
                // size=4 sifatida ham o'tadi). O'lcham va ildizni checkpoint imzosi bog'laydi.
                if !p.is_empty() {
                    let mut bad = p.clone();
                    bad[0].0[0] ^= 1;
                    assert!(!verify_inclusion(m as u64, n as u64, &d[m], &bad, &r));
                    assert!(!verify_inclusion(m as u64, n as u64, &d[m], &p[1..], &r));
                }
            }
            assert!(inclusion_proof(n, &d).is_none());
        }
    }

    #[test]
    fn every_consistency_proof_verifies_and_tamper_fails() {
        for n in 1..=40 {
            let d = leaves(n);
            let rn = root(&d);
            for m in 1..=n {
                let rm = root(&d[..m]);
                let p = consistency_proof(m, &d).unwrap();
                assert!(
                    verify_consistency(m as u64, n as u64, &rm, &rn, &p),
                    "m={m} n={n}"
                );
                // Boshqa tarix: birinchi daraxtning bitta bargi o'zgargan.
                let mut forged = d.clone();
                forged[m - 1].0[0] ^= 1;
                let rm_forged = root(&forged[..m]);
                assert!(
                    !verify_consistency(m as u64, n as u64, &rm_forged, &rn, &p),
                    "m={m} n={n}"
                );
                if !p.is_empty() {
                    let mut bad = p.clone();
                    let last = bad.len() - 1;
                    bad[last].0[0] ^= 1;
                    assert!(!verify_consistency(m as u64, n as u64, &rm, &rn, &bad));
                }
            }
            assert!(consistency_proof(0, &d).is_none());
            assert!(consistency_proof(n + 1, &d).is_none());
        }
    }
}

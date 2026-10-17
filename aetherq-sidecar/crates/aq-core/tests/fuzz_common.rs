// Umumiy fuzz yordamchilari (fuzz.rs va fuzz_long.rs ikkalasi ishlatadi).

pub struct Lcg(pub u64);

impl Lcg {
    pub fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        self.0 >> 33
    }
    pub fn below(&mut self, n: usize) -> usize {
        (self.next() as usize) % n.max(1)
    }
}

pub fn mutate(rng: &mut Lcg, data: &[u8]) -> Vec<u8> {
    let mut v = data.to_vec();
    match rng.below(6) {
        0 => {
            if !v.is_empty() {
                let i = rng.below(v.len());
                v[i] ^= 1 << rng.below(8);
            }
        }
        1 => {
            let n = rng.below(v.len() + 1);
            v.truncate(n);
        }
        2 => {
            for _ in 0..(rng.below(8) + 1) {
                v.push(rng.next() as u8);
            }
        }
        3 => {
            if v.len() >= 4 {
                let i = rng.below(v.len() - 3);
                v[i..i + 4].copy_from_slice(&(rng.next() as u32).to_be_bytes());
            }
        }
        4 => {
            // uzunlik maydoni (3-5 bayt) ataylab buzish
            if v.len() >= 6 {
                v[3..6].copy_from_slice(&[(rng.next() as u8), 0xFF, 0xFF]);
            }
        }
        _ => {
            // ikki baytni almashtirish
            if v.len() >= 2 {
                let (i, j) = (rng.below(v.len()), rng.below(v.len()));
                v.swap(i, j);
            }
        }
    }
    v
}

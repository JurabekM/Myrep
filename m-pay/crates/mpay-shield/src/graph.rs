//! Qurilma–karta bipartit grafi: union-find bilan bog'langan komponentlar, darajalar,
//! qirralarning birinchi ko'rilgan vaqti.
//!
//! Tugunlar — `DeviceId` va `PanFingerprint` (kalitsiz qaytarib bo'lmaydigan HMAC). Graf faqat
//! xotirada (sandbox); `TODO(spec):` ko'p instansiyali deployment uchun tashqi graf ombori.

use std::collections::HashMap;

/// Tugun.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Node {
    Device([u8; 32]),
    Card([u8; 32]),
}

#[derive(Debug, Default)]
struct UnionFind {
    parent: Vec<usize>,
    size: Vec<u32>,
}

impl UnionFind {
    fn add(&mut self) -> usize {
        let i = self.parent.len();
        self.parent.push(i);
        self.size.push(1);
        i
    }

    fn find(&mut self, mut x: usize) -> usize {
        while self.parent[x] != x {
            // Yo'lni yarmiga qisqartirish.
            self.parent[x] = self.parent[self.parent[x]];
            x = self.parent[x];
        }
        x
    }

    fn union(&mut self, a: usize, b: usize) -> usize {
        let (mut ra, mut rb) = (self.find(a), self.find(b));
        if ra == rb {
            return ra;
        }
        if self.size[ra] < self.size[rb] {
            std::mem::swap(&mut ra, &mut rb);
        }
        self.parent[rb] = ra;
        self.size[ra] += self.size[rb];
        ra
    }
}

/// Qirra qo'shish natijasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EdgeInfo {
    /// Qirra birinchi marta ko'rilgan vaqt (yangi bo'lsa — hozirgi).
    pub first_seen: i64,
    pub is_new: bool,
    /// Qurilmadagi turli kartalar soni (shu qirradan keyin).
    pub device_degree: u32,
    /// Kartadagi turli qurilmalar soni.
    pub card_degree: u32,
    /// Bog'langan komponent hajmi (tugunlar).
    pub component_size: u32,
}

/// Graf.
#[derive(Debug, Default)]
pub struct DeviceCardGraph {
    index: HashMap<Node, usize>,
    uf: UnionFind,
    degree: Vec<u32>,
    edges: HashMap<(usize, usize), i64>,
}

impl DeviceCardGraph {
    fn node(&mut self, n: Node) -> usize {
        if let Some(i) = self.index.get(&n) {
            return *i;
        }
        let i = self.uf.add();
        self.degree.push(0);
        self.index.insert(n, i);
        i
    }

    /// Qirra qo'shadi (mavjud bo'lsa o'zgartirmaydi) va holatini qaytaradi.
    pub fn touch(&mut self, device: [u8; 32], card: [u8; 32], now: i64) -> EdgeInfo {
        let d = self.node(Node::Device(device));
        let c = self.node(Node::Card(card));
        let (first_seen, is_new) = match self.edges.get(&(d, c)) {
            Some(t) => (*t, false),
            None => {
                self.edges.insert((d, c), now);
                self.degree[d] += 1;
                self.degree[c] += 1;
                self.uf.union(d, c);
                (now, true)
            }
        };
        let root = self.uf.find(d);
        EdgeInfo {
            first_seen,
            is_new,
            device_degree: self.degree[d],
            card_degree: self.degree[c],
            component_size: self.uf.size[root],
        }
    }

    /// Qirra qo'shmasdan qurilma darajasi.
    pub fn device_degree(&self, device: [u8; 32]) -> u32 {
        self.index
            .get(&Node::Device(device))
            .map(|i| self.degree[*i])
            .unwrap_or(0)
    }

    pub fn nodes(&self) -> usize {
        self.index.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn id(n: u8) -> [u8; 32] {
        [n; 32]
    }

    #[test]
    fn components_and_degrees() {
        let mut g = DeviceCardGraph::default();
        let e = g.touch(id(1), id(10), 100);
        assert!(e.is_new);
        assert_eq!(
            (e.device_degree, e.card_degree, e.component_size),
            (1, 1, 2)
        );
        let e = g.touch(id(1), id(10), 200);
        assert!(!e.is_new);
        assert_eq!(e.first_seen, 100);
        // Mule halqasi: 2 qurilma × 2 karta.
        g.touch(id(1), id(11), 300);
        g.touch(id(2), id(11), 300);
        let e = g.touch(id(2), id(12), 400);
        assert_eq!(e.component_size, 5);
        assert_eq!(g.device_degree(id(1)), 2);
        // Alohida komponent.
        let e = g.touch(id(3), id(20), 500);
        assert_eq!(e.component_size, 2);
        assert_eq!(g.nodes(), 7);
    }
}

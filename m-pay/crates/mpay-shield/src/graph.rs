//! Qurilma–karta bipartit grafi: union-find bilan bog'langan komponentlar, darajalar,
//! qirralarning birinchi ko'rilgan vaqti.
//!
//! Tugunlar — `DeviceId` va `PanFingerprint` (kalitsiz qaytarib bo'lmaydigan HMAC). Graf xotirada;
//! API instansiyalari uni Shield roli orqali bo'lishadi (ADR-0019), yetakchi Shield uni belgilar
//! ombori bilan birga snapshot'ga yozadi va zaxira tiklaydi (ADR-0026).
//!
//! Qurilma kaliti almashtirilsa (ADR-0015) yangi ID eski qurilma tuguniga **taxallus** bo'ladi:
//! alohida tugun yaratilmaydi, kartalar soni ikki barobar bo'lmaydi va `card_device_count` oshmaydi.

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
    /// Yangi qurilma ID → asl (birinchi) qurilma ID.
    aliases: HashMap<[u8; 32], [u8; 32]>,
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

    /// Qurilmaning asl ID'si (kalit almashtirishlar zanjiri bo'yicha).
    pub fn canonical(&self, device: [u8; 32]) -> [u8; 32] {
        self.aliases.get(&device).copied().unwrap_or(device)
    }

    /// `new` ni `old` qurilmasining davomi sifatida bog'laydi. `new` grafda allaqachon bo'lsa (o'z
    /// tarixi bor) yoki o'ziga bog'lansa — `false`, hech narsa o'zgarmaydi.
    pub fn link_device(&mut self, old: [u8; 32], new: [u8; 32]) -> bool {
        let root = self.canonical(old);
        if new == root
            || self.aliases.contains_key(&new)
            || self.index.contains_key(&Node::Device(new))
        {
            return false;
        }
        self.aliases.insert(new, root);
        true
    }

    /// Qirra qo'shadi (mavjud bo'lsa o'zgartirmaydi) va holatini qaytaradi.
    pub fn touch(&mut self, device: [u8; 32], card: [u8; 32], now: i64) -> EdgeInfo {
        let d = self.node(Node::Device(self.canonical(device)));
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
            .get(&Node::Device(self.canonical(device)))
            .map(|i| self.degree[*i])
            .unwrap_or(0)
    }

    pub fn nodes(&self) -> usize {
        self.index.len()
    }

    /// Snapshot (ADR-0026): tugunlar indeks tartibida, qirralar va taxalluslar saralangan.
    pub(crate) fn encode(&self, w: &mut crate::snapshot::W) {
        let mut nodes: Vec<(usize, Node)> = self.index.iter().map(|(n, i)| (*i, *n)).collect();
        nodes.sort_unstable_by_key(|(i, _)| *i);
        w.len(nodes.len());
        for (i, n) in &nodes {
            match n {
                Node::Device(id) => {
                    w.u8(0);
                    w.a32(id);
                }
                Node::Card(id) => {
                    w.u8(1);
                    w.a32(id);
                }
            }
            w.u64(self.uf.parent[*i] as u64);
            w.u32(self.uf.size[*i]);
            w.u32(self.degree[*i]);
        }
        let mut edges: Vec<_> = self.edges.iter().collect();
        edges.sort_unstable();
        w.len(edges.len());
        for ((d, c), t) in edges {
            w.u64(*d as u64);
            w.u64(*c as u64);
            w.i64(*t);
        }
        let mut aliases: Vec<_> = self.aliases.iter().collect();
        aliases.sort_unstable();
        w.len(aliases.len());
        for (new, root) in aliases {
            w.a32(new);
            w.a32(root);
        }
    }

    pub(crate) fn decode(r: &mut crate::snapshot::R<'_>) -> crate::snapshot::Result<Self> {
        use crate::snapshot::SnapshotError::Format;
        let n = r.len(1 + 32 + 8 + 4 + 4)?;
        let mut g = Self::default();
        for i in 0..n {
            let id = |r: &mut crate::snapshot::R<'_>, tag| match tag {
                0 => Ok(Node::Device(r.a32()?)),
                1 => Ok(Node::Card(r.a32()?)),
                _ => Err(Format("tugun turi")),
            };
            let tag = r.u8()?;
            let node = id(r, tag)?;
            if g.index.insert(node, i).is_some() {
                return Err(Format("takroriy tugun"));
            }
            let parent = r.u64()?;
            if parent >= n as u64 {
                return Err(Format("union-find ota tuguni"));
            }
            g.uf.parent.push(parent as usize);
            g.uf.size.push(r.u32()?);
            g.degree.push(r.u32()?);
        }
        // Ota zanjirlari ildizga yetishi shart (aylana bo'lsa `find` tugamas edi).
        let mut seen = vec![0u8; n]; // 0 — noma'lum, 1 — tekshirilmoqda, 2 — ildizga yetadi
        for start in 0..n {
            let mut path = Vec::new();
            let mut x = start;
            while seen[x] == 0 && g.uf.parent[x] != x {
                seen[x] = 1;
                path.push(x);
                x = g.uf.parent[x];
            }
            if seen[x] == 1 {
                return Err(Format("union-find aylanasi"));
            }
            seen[x] = 2;
            for p in path {
                seen[p] = 2;
            }
        }
        let m = r.len(8 + 8 + 8)?;
        for _ in 0..m {
            let (d, c, t) = (r.u64()?, r.u64()?, r.i64()?);
            if d >= n as u64 || c >= n as u64 {
                return Err(Format("qirra tuguni"));
            }
            if g.edges.insert((d as usize, c as usize), t).is_some() {
                return Err(Format("takroriy qirra"));
            }
        }
        let a = r.len(64)?;
        for _ in 0..a {
            let (new, root) = (r.a32()?, r.a32()?);
            if g.aliases.insert(new, root).is_some() {
                return Err(Format("takroriy taxallus"));
            }
        }
        Ok(g)
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

    #[test]
    fn rekeyed_device_is_alias_of_original() {
        let mut g = DeviceCardGraph::default();
        g.touch(id(1), id(10), 100);
        g.touch(id(1), id(11), 100);
        // 1 → 4 → 5 (ikki marta kalit almashtirildi).
        assert!(g.link_device(id(1), id(4)));
        assert!(g.link_device(id(4), id(5)));
        assert_eq!(g.canonical(id(5)), id(1));
        // Eski karta yangi kalit bilan — o'sha qirra, karta bitta qurilmada.
        let e = g.touch(id(5), id(10), 900);
        assert!(!e.is_new);
        assert_eq!((e.first_seen, e.card_degree, e.device_degree), (100, 1, 2));
        assert_eq!(g.device_degree(id(4)), 2);
        assert_eq!(g.nodes(), 3);
        // O'z tarixi bor qurilmani, takroriy va o'ziga bog'lash — rad.
        g.touch(id(7), id(20), 100);
        assert!(!g.link_device(id(1), id(7)));
        assert!(!g.link_device(id(1), id(5)));
        assert!(!g.link_device(id(5), id(1)));
        assert_eq!(g.device_degree(id(7)), 1);
    }
}

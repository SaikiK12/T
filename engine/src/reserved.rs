//! Reserved samples (docs/GATES.md): rows before 2021-01-01 and the venues' `reserved/` folders are read only by a
//! frozen batch PREREG that declares them. Every qx command calls `check` before it reads data. A spec that touches a
//! reserved sample must name that PREREG in `reserved_prereg`: a PREREG.md holding the sample's token, frozen by
//! `lab.prereg.freeze()` (its PREREG.sha256 sidecar matches its bytes). Anything else is refused.

use crate::data;
use anyhow::{Result, anyhow};
use std::path::Path;

pub const START: &str = "2021-01-01";
pub const TOKEN_2020: &str = "RESERVED-2020-READ";
pub const TOKEN_GATE: &str = "RESERVED-GATE-READ";
pub const TOKEN_VENUE: &str = "RESERVED-VENUE-READ";

/// The tokens a run needs: 2020 when it starts before START, Gate's or the other venues' when a data path has a
/// `reserved` folder.
pub fn needed(start: &str, paths: &[&str]) -> Result<Vec<&'static str>> {
    let mut need = Vec::new();
    if data::ms(start)? < data::ms(START)? {
        need.push(TOKEN_2020);
    }
    for p in paths {
        if p.split(['/', '\\']).any(|seg| seg == "reserved") {
            let t = if p.trim_start_matches("./").starts_with("gate_hist") { TOKEN_GATE } else { TOKEN_VENUE };
            if !need.contains(&t) {
                need.push(t);
            }
        }
    }
    Ok(need)
}

pub fn check(start: &str, paths: &[&str], prereg: Option<&str>) -> Result<()> {
    let need = needed(start, paths)?;
    if need.is_empty() {
        return Ok(());
    }
    let path = prereg.ok_or_else(|| {
        anyhow!("this spec reads reserved samples ({}); only a frozen batch PREREG named in `reserved_prereg` may (docs/GATES.md)",
                need.join(", "))
    })?;
    let text = std::fs::read(path).map_err(|e| anyhow!("reserved_prereg {path}: {e}"))?;
    let side = Path::new(path).with_extension("sha256");
    let frozen = std::fs::read_to_string(&side).map_err(|_| anyhow!("{path} is not frozen: {} is missing", side.display()))?;
    if hex(&sha256(&text)) != frozen.trim() {
        return Err(anyhow!("{path} changed after freezing: its sha256 differs from {}", side.display()));
    }
    let s = String::from_utf8_lossy(&text);
    for t in need {
        if !s.contains(t) {
            return Err(anyhow!("{path} does not declare {t}"));
        }
    }
    Ok(())
}

fn hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}

/// SHA-256 (FIPS 180-4), so the engine checks a frozen PREREG without another crate.
pub fn sha256(msg: &[u8]) -> [u8; 32] {
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98,
        0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
        0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8,
        0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819,
        0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
        0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
        0xc67178f2,
    ];
    let mut h: [u32; 8] =
        [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
    let mut m = msg.to_vec();
    m.push(0x80);
    while m.len() % 64 != 56 {
        m.push(0);
    }
    m.extend_from_slice(&((msg.len() as u64) * 8).to_be_bytes());
    for block in m.chunks(64) {
        let mut w = [0u32; 64];
        for i in 0..16 {
            w[i] = u32::from_be_bytes([block[4 * i], block[4 * i + 1], block[4 * i + 2], block[4 * i + 3]]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16].wrapping_add(s0).wrapping_add(w[i - 7]).wrapping_add(s1);
        }
        let mut v = h;
        for i in 0..64 {
            let s1 = v[4].rotate_right(6) ^ v[4].rotate_right(11) ^ v[4].rotate_right(25);
            let ch = (v[4] & v[5]) ^ (!v[4] & v[6]);
            let t1 = v[7].wrapping_add(s1).wrapping_add(ch).wrapping_add(K[i]).wrapping_add(w[i]);
            let s0 = v[0].rotate_right(2) ^ v[0].rotate_right(13) ^ v[0].rotate_right(22);
            let maj = (v[0] & v[1]) ^ (v[0] & v[2]) ^ (v[1] & v[2]);
            let t2 = s0.wrapping_add(maj);
            v = [t1.wrapping_add(t2), v[0], v[1], v[2], v[3].wrapping_add(t1), v[4], v[5], v[6]];
        }
        for i in 0..8 {
            h[i] = h[i].wrapping_add(v[i]);
        }
    }
    let mut out = [0u8; 32];
    for i in 0..8 {
        out[4 * i..4 * i + 4].copy_from_slice(&h[i].to_be_bytes());
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sha256_known_vectors() {
        assert_eq!(hex(&sha256(b"")), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
        assert_eq!(hex(&sha256(b"abc")), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
        assert_eq!(hex(&sha256(b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq")),
                   "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1");
        assert_eq!(hex(&sha256(&[b'a'; 1000])), "41edece42d63e8d9bf515a9ba6932e1c20cbc9f5a5d134645adb5db1b9737ea3");
    }

    #[test]
    fn what_needs_a_token() {
        assert!(needed("2021-01-01", &["klines_1h", "gate_hist/open/candlesticks_1h"]).unwrap().is_empty());
        assert_eq!(needed("2020-06-01", &["klines_1h"]).unwrap(), vec![TOKEN_2020]);
        assert_eq!(needed("2021-01-01", &["gate_hist/reserved/candlesticks_1h"]).unwrap(), vec![TOKEN_GATE]);
        assert_eq!(needed("2020-01-01", &["kucoin_hist/reserved/funding", "dydx_hist/reserved/x"]).unwrap(),
                   vec![TOKEN_2020, TOKEN_VENUE]);
        assert!(check("2021-03-01", &["klines_1h"], None).is_ok());
        assert!(check("2020-03-01", &["klines_1h"], None).is_err());
    }

    #[test]
    fn only_a_frozen_prereg_with_the_token() {
        let dir = std::env::temp_dir().join(format!("qx_reserved_{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let p = dir.join("PREREG.md");
        let side = dir.join("PREREG.sha256");
        let ps = p.to_str().unwrap();
        std::fs::write(&p, "batch: RESERVED-2020-READ\n").unwrap();
        assert!(check("2020-01-01", &["klines_1h"], Some(ps)).is_err());               // not frozen
        std::fs::write(&side, format!("{}\n", hex(&sha256(b"batch: RESERVED-2020-READ\n")))).unwrap();
        assert!(check("2020-01-01", &["klines_1h"], Some(ps)).is_ok());
        assert!(check("2020-01-01", &["gate_hist/reserved/c"], Some(ps)).is_err());      // Gate token missing
        std::fs::write(&p, "batch: RESERVED-2020-READ edited\n").unwrap();
        assert!(check("2020-01-01", &["klines_1h"], Some(ps)).is_err());               // changed after freezing
        std::fs::remove_dir_all(&dir).unwrap();
    }
}

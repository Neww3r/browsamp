//! Stereo reverb: pre-delay → allpass diffusion → 8-line feedback delay network with a
//! Hadamard mixing matrix and per-line damping.

use crate::smooth::Smoother;

const LINES: usize = 8;
const LINE_MS: [f32; LINES] = [29.7, 37.1, 41.1, 43.7, 47.9, 53.3, 59.1, 67.3];
const DIFF_MS: [f32; 4] = [4.77, 3.59, 12.73, 9.30];
const MAX_PREDELAY_MS: f32 = 200.0;

struct Allpass {
    buf: Vec<f32>,
    i: usize,
}

impl Allpass {
    fn new(len: usize) -> Self {
        Self { buf: vec![0.0; len.max(1)], i: 0 }
    }

    #[inline]
    fn process(&mut self, x: f32, g: f32) -> f32 {
        let d = self.buf[self.i];
        let v = x + g * d;
        self.buf[self.i] = v;
        self.i = (self.i + 1) % self.buf.len();
        d - g * v
    }
}

#[inline]
fn hadamard8(v: &mut [f32; LINES]) {
    let mut h = 1;
    while h < LINES {
        let mut i = 0;
        while i < LINES {
            for j in i..i + h {
                let (a, b) = (v[j], v[j + h]);
                v[j] = a + b;
                v[j + h] = a - b;
            }
            i += h * 2;
        }
        h *= 2;
    }
    let s = 1.0 / (LINES as f32).sqrt();
    for x in v.iter_mut() {
        *x *= s;
    }
}

pub struct Reverb {
    sr: f32,
    pre: Vec<f32>,
    pre_w: usize,
    pre_len: Smoother,
    diff: [Allpass; 4],
    lines: [Vec<f32>; LINES],
    idx: [usize; LINES],
    gains: [f32; LINES],
    damp_state: [f32; LINES],
    damp: f32,
    decay_s: f32,
}

impl Reverb {
    pub fn new(sr: f32) -> Self {
        let ms = |m: f32| (m * 0.001 * sr) as usize;
        let mut r = Self {
            sr,
            pre: vec![0.0; ms(MAX_PREDELAY_MS) + 2],
            pre_w: 0,
            pre_len: Smoother::new(ms(10.0) as f32, 50.0, sr),
            diff: DIFF_MS.map(|m| Allpass::new(ms(m))),
            lines: LINE_MS.map(|m| vec![0.0; ms(m)]),
            idx: [0; LINES],
            gains: [0.0; LINES],
            damp_state: [0.0; LINES],
            damp: 0.3,
            decay_s: 2.0,
        };
        r.set_decay(2.0);
        r
    }

    /// RT60 in seconds.
    pub fn set_decay(&mut self, seconds: f32) {
        self.decay_s = seconds.clamp(0.2, 12.0);
        for i in 0..LINES {
            let len = self.lines[i].len() as f32 / self.sr;
            self.gains[i] = 10f32.powf(-3.0 * len / self.decay_s);
        }
    }

    /// 0 = bright, 1 = very dark.
    pub fn set_damping(&mut self, d: f32) {
        self.damp = d.clamp(0.0, 0.95);
    }

    pub fn set_predelay_ms(&mut self, ms: f32) {
        let max = (self.pre.len() - 2) as f32;
        self.pre_len.set((ms.clamp(0.0, MAX_PREDELAY_MS) * 0.001 * self.sr).clamp(0.0, max));
    }

    #[inline]
    pub fn process(&mut self, x: f32) -> (f32, f32) {
        let plen = self.pre.len();
        self.pre[self.pre_w] = x;
        let d = self.pre_len.next() as usize;
        let mut s = self.pre[(self.pre_w + plen - d) % plen];
        self.pre_w = (self.pre_w + 1) % plen;

        for ap in &mut self.diff {
            s = ap.process(s, 0.6);
        }

        let mut v = [0f32; LINES];
        for i in 0..LINES {
            let o = self.lines[i][self.idx[i]];
            self.damp_state[i] = o * (1.0 - self.damp) + self.damp_state[i] * self.damp;
            if self.damp_state[i].abs() < 1e-20 {
                self.damp_state[i] = 0.0;
            }
            v[i] = self.damp_state[i];
        }
        let l = v[0] - v[2] + v[4] - v[6];
        let r = v[1] - v[3] + v[5] - v[7];

        for i in 0..LINES {
            v[i] *= self.gains[i];
        }
        hadamard8(&mut v);
        for i in 0..LINES {
            let sign = if i & 1 == 0 { 1.0 } else { -1.0 };
            self.lines[i][self.idx[i]] = v[i] + s * sign;
            self.idx[i] = (self.idx[i] + 1) % self.lines[i].len();
        }
        (l * 0.35, r * 0.35)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tail_decays_roughly_at_rt60() {
        let sr = 48000.0;
        let mut r = Reverb::new(sr);
        r.set_decay(1.0);
        r.set_damping(0.0);
        let energy = |from: usize, to: usize, r: &mut Reverb, start: usize| {
            let mut e = 0.0;
            for i in start..to {
                let (l, rr) = r.process(if i == 0 { 1.0 } else { 0.0 });
                if i >= from {
                    e += l * l + rr * rr;
                }
            }
            e
        };
        let e1 = energy(4800, 9600, &mut r, 0);
        let e2 = energy(52800, 57600, &mut r, 9600);
        let drop_db = 10.0 * (e1 / e2).log10();
        // 1 s later, a 1 s RT60 should be ~60 dB down (loose tolerance: diffusion + modal effects).
        assert!(drop_db > 45.0 && drop_db < 75.0, "{drop_db:.1} dB");
    }

    #[test]
    fn stable_at_max_decay() {
        let mut r = Reverb::new(48000.0);
        r.set_decay(12.0);
        r.set_damping(0.0);
        let mut peak = 0f32;
        for i in 0..(48000 * 10) {
            let (l, rr) = r.process(if i < 4800 { 0.5 } else { 0.0 });
            peak = peak.max(l.abs()).max(rr.abs());
            assert!(l.is_finite());
        }
        assert!(peak < 2.0);
    }
}

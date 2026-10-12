//! Fender/Marshall/Mesa (FMV) passive tone stack, from D. T. Yeh's analytic model,
//! discretized with the bilinear transform. Third-order, f64.

#[derive(Clone, Copy, Debug)]
pub struct TsComponents {
    pub r1: f64,
    pub r2: f64,
    pub r3: f64,
    pub r4: f64,
    pub c1: f64,
    pub c2: f64,
    pub c3: f64,
}

pub const FENDER: TsComponents =
    TsComponents { r1: 250e3, r2: 1e6, r3: 25e3, r4: 56e3, c1: 250e-12, c2: 20e-9, c3: 20e-9 };
pub const MARSHALL: TsComponents =
    TsComponents { r1: 220e3, r2: 1e6, r3: 22e3, r4: 33e3, c1: 470e-12, c2: 22e-9, c3: 22e-9 };
pub const MODERN: TsComponents =
    TsComponents { r1: 250e3, r2: 1e6, r3: 25e3, r4: 47e3, c1: 470e-12, c2: 47e-9, c3: 22e-9 };

/// Bass pots are audio taper.
fn bass_taper(b: f64) -> f64 {
    ((b.clamp(0.0, 1.0) - 1.0) * 3.4).exp()
}

/// Analog transfer function H(s) = (b1 s + b2 s² + b3 s³) / (1 + a1 s + a2 s² + a3 s³).
fn analog(k: &TsComponents, bass: f64, mid: f64, treble: f64) -> ([f64; 4], [f64; 4]) {
    let TsComponents { r1, r2, r3, r4, c1, c2, c3 } = *k;
    let (l, m, t) = (bass_taper(bass), mid.clamp(0.0, 1.0), treble.clamp(0.0, 1.0));
    let mm = m * m;

    let b1 = t * c1 * r1 + m * c3 * r3 + l * (c1 * r2 + c2 * r2) + (c1 * r3 + c2 * r3);
    let b2 = t * (c1 * c2 * r1 * r4 + c1 * c3 * r1 * r4)
        - mm * (c1 * c3 * r3 * r3 + c2 * c3 * r3 * r3)
        + m * (c1 * c3 * r1 * r3 + c1 * c3 * r3 * r3 + c2 * c3 * r3 * r3)
        + l * (c1 * c2 * r1 * r2 + c1 * c2 * r2 * r4 + c1 * c3 * r2 * r4)
        + l * m * (c1 * c3 * r2 * r3 + c2 * c3 * r2 * r3)
        + (c1 * c2 * r1 * r3 + c1 * c2 * r3 * r4 + c1 * c3 * r3 * r4);
    let c123 = c1 * c2 * c3;
    let b3 = l * m * (c123 * r1 * r2 * r3 + c123 * r2 * r3 * r4)
        - mm * (c123 * r1 * r3 * r3 + c123 * r3 * r3 * r4)
        + m * (c123 * r1 * r3 * r3 + c123 * r3 * r3 * r4)
        + t * c123 * r1 * r3 * r4
        - t * m * c123 * r1 * r3 * r4
        + t * l * c123 * r1 * r2 * r4;

    let a1 = (c1 * r1 + c1 * r3 + c2 * r3 + c2 * r4 + c3 * r4) + m * c3 * r3 + l * (c1 * r2 + c2 * r2);
    let a2 = m * (c1 * c3 * r1 * r3 - c2 * c3 * r3 * r4 + c1 * c3 * r3 * r3 + c2 * c3 * r3 * r3)
        + l * m * (c1 * c3 * r2 * r3 + c2 * c3 * r2 * r3)
        - mm * (c1 * c3 * r3 * r3 + c2 * c3 * r3 * r3)
        + l * (c1 * c2 * r2 * r4 + c1 * c2 * r1 * r2 + c1 * c3 * r2 * r4 + c2 * c3 * r2 * r4)
        + (c1 * c2 * r1 * r4 + c1 * c3 * r1 * r4 + c1 * c2 * r3 * r4 + c1 * c2 * r1 * r3 + c1 * c3 * r3 * r4
            + c2 * c3 * r3 * r4);
    let a3 = l * m * (c123 * r1 * r2 * r3 + c123 * r2 * r3 * r4)
        - mm * (c123 * r1 * r3 * r3 + c123 * r3 * r3 * r4)
        + m * (c123 * r3 * r3 * r4 + c123 * r1 * r3 * r3 - c123 * r1 * r3 * r4)
        + l * c123 * r1 * r2 * r4
        + c123 * r1 * r3 * r4;

    ([0.0, b1, b2, b3], [1.0, a1, a2, a3])
}

/// |H(j·2πf)| of the analog prototype.
pub fn analog_magnitude(k: &TsComponents, bass: f64, mid: f64, treble: f64, f: f64) -> f64 {
    let (b, a) = analog(k, bass, mid, treble);
    let w = 2.0 * std::f64::consts::PI * f;
    // s = jw: s² = -w², s³ = -j w³
    let (nr, ni) = (b[0] - b[2] * w * w, b[1] * w - b[3] * w * w * w);
    let (dr, di) = (a[0] - a[2] * w * w, a[1] * w - a[3] * w * w * w);
    ((nr * nr + ni * ni) / (dr * dr + di * di)).sqrt()
}

pub struct Tonestack {
    k: TsComponents,
    fs: f64,
    b: [f64; 4],
    a: [f64; 4],
    z: [f64; 3],
    makeup: f64,
    last: [f32; 3],
}

impl Tonestack {
    pub fn new(k: TsComponents, fs: f32) -> Self {
        let mut ts = Self { k, fs: fs as f64, b: [0.0; 4], a: [0.0; 4], z: [0.0; 3], makeup: 1.0, last: [-1.0; 3] };
        ts.set_components(k);
        ts
    }

    pub fn set_components(&mut self, k: TsComponents) {
        self.k = k;
        // Normalize so the peak of the response at noon settings sits at 0 dB.
        let mut peak: f64 = 0.0;
        let mut f = 40.0;
        while f < 10000.0 {
            peak = peak.max(analog_magnitude(&k, 0.5, 0.5, 0.5, f));
            f *= 1.1;
        }
        self.makeup = 1.0 / peak;
        self.last = [-1.0; 3];
        self.z = [0.0; 3];
    }

    pub fn set(&mut self, bass: f32, mid: f32, treble: f32) {
        if self.last == [bass, mid, treble] {
            return;
        }
        self.last = [bass, mid, treble];
        let (b, a) = analog(&self.k, bass as f64, mid as f64, treble as f64);
        let c = 2.0 * self.fs;
        let (c2, c3) = (c * c, c * c * c);
        let bz = [
            b[0] + b[1] * c + b[2] * c2 + b[3] * c3,
            3.0 * b[0] + b[1] * c - b[2] * c2 - 3.0 * b[3] * c3,
            3.0 * b[0] - b[1] * c - b[2] * c2 + 3.0 * b[3] * c3,
            b[0] - b[1] * c + b[2] * c2 - b[3] * c3,
        ];
        let az = [
            a[0] + a[1] * c + a[2] * c2 + a[3] * c3,
            3.0 * a[0] + a[1] * c - a[2] * c2 - 3.0 * a[3] * c3,
            3.0 * a[0] - a[1] * c - a[2] * c2 + 3.0 * a[3] * c3,
            a[0] - a[1] * c + a[2] * c2 - a[3] * c3,
        ];
        let n = 1.0 / az[0];
        for i in 0..4 {
            self.b[i] = bz[i] * n * self.makeup;
            self.a[i] = az[i] * n;
        }
    }

    #[inline]
    pub fn process(&mut self, x: f32) -> f32 {
        let x = x as f64;
        let y = self.b[0] * x + self.z[0];
        self.z[0] = self.b[1] * x - self.a[1] * y + self.z[1];
        self.z[1] = self.b[2] * x - self.a[2] * y + self.z[2];
        self.z[2] = self.b[3] * x - self.a[3] * y;
        for z in &mut self.z {
            if z.abs() < 1e-30 {
                *z = 0.0;
            }
        }
        y as f32
    }

    /// Digital magnitude response (for tests).
    pub fn magnitude(&self, f: f64) -> f64 {
        let w = 2.0 * std::f64::consts::PI * f / self.fs;
        let (mut nr, mut ni, mut dr, mut di) = (0.0, 0.0, 0.0, 0.0);
        for i in 0..4 {
            let (c, s) = ((w * i as f64).cos(), -(w * i as f64).sin());
            nr += self.b[i] * c;
            ni += self.b[i] * s;
            dr += self.a[i] * c;
            di += self.a[i] * s;
        }
        ((nr * nr + ni * ni) / (dr * dr + di * di)).sqrt()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn db(x: f64) -> f64 {
        20.0 * x.log10()
    }

    #[test]
    fn digital_matches_analog_in_audio_band() {
        for k in [FENDER, MARSHALL, MODERN] {
            for fs in [48000.0f32, 192000.0] {
                let mut ts = Tonestack::new(k, fs);
                for &(b, m, t) in &[(0.5, 0.5, 0.5), (1.0, 0.0, 1.0), (0.0, 1.0, 0.2), (0.8, 0.3, 0.7)] {
                    ts.set(b, m, t);
                    for &f in &[60.0, 200.0, 500.0, 1000.0, 3000.0, 6000.0] {
                        let ana = db(analog_magnitude(&k, b as f64, m as f64, t as f64, f) * ts.makeup);
                        let dig = db(ts.magnitude(f));
                        assert!((ana - dig).abs() < 0.5, "fs={fs} f={f} ana={ana:.2} dig={dig:.2}");
                    }
                }
            }
        }
    }

    #[test]
    fn controls_do_what_they_say() {
        let mut ts = Tonestack::new(MARSHALL, 192000.0);
        ts.set(0.0, 0.5, 0.5);
        let low_bass = ts.magnitude(80.0);
        ts.set(1.0, 0.5, 0.5);
        assert!(db(ts.magnitude(80.0) / low_bass) > 4.0, "bass knob");
        ts.set(0.5, 0.5, 0.0);
        let low_treble = ts.magnitude(5000.0);
        ts.set(0.5, 0.5, 1.0);
        assert!(db(ts.magnitude(5000.0) / low_treble) > 6.0, "treble knob");
        ts.set(0.5, 0.0, 0.5);
        let low_mid = ts.magnitude(600.0);
        ts.set(0.5, 1.0, 0.5);
        assert!(db(ts.magnitude(600.0) / low_mid) > 4.0, "mid knob");
    }

    #[test]
    fn classic_mid_scoop_at_noon() {
        // The FMV stack famously scoops the mids around 400-700 Hz.
        let k = FENDER;
        let lo = analog_magnitude(&k, 0.5, 0.5, 0.5, 100.0);
        let mid = analog_magnitude(&k, 0.5, 0.5, 0.5, 500.0);
        let hi = analog_magnitude(&k, 0.5, 0.5, 0.5, 4000.0);
        assert!(mid < lo && mid < hi);
    }
}

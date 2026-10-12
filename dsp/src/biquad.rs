//! RBJ biquads in transposed direct form II. Coefficients and state are f64 so that
//! low cutoffs stay accurate even when running at the 4x oversampled rate.

use std::f64::consts::PI;

#[derive(Clone, Copy, Debug)]
pub struct Biquad {
    b0: f64,
    b1: f64,
    b2: f64,
    a1: f64,
    a2: f64,
    z1: f64,
    z2: f64,
}

impl Default for Biquad {
    fn default() -> Self {
        Self::identity()
    }
}

impl Biquad {
    pub fn identity() -> Self {
        Self { b0: 1.0, b1: 0.0, b2: 0.0, a1: 0.0, a2: 0.0, z1: 0.0, z2: 0.0 }
    }

    fn norm(b0: f64, b1: f64, b2: f64, a0: f64, a1: f64, a2: f64) -> Self {
        Self { b0: b0 / a0, b1: b1 / a0, b2: b2 / a0, a1: a1 / a0, a2: a2 / a0, z1: 0.0, z2: 0.0 }
    }

    fn w0(fs: f32, f: f32) -> (f64, f64) {
        let f = (f as f64).clamp(1.0, fs as f64 * 0.49);
        let w = 2.0 * PI * f / fs as f64;
        (w.sin(), w.cos())
    }

    pub fn lowpass(fs: f32, f: f32, q: f32) -> Self {
        let (s, c) = Self::w0(fs, f);
        let al = s / (2.0 * q as f64);
        Self::norm((1.0 - c) / 2.0, 1.0 - c, (1.0 - c) / 2.0, 1.0 + al, -2.0 * c, 1.0 - al)
    }

    pub fn highpass(fs: f32, f: f32, q: f32) -> Self {
        let (s, c) = Self::w0(fs, f);
        let al = s / (2.0 * q as f64);
        Self::norm((1.0 + c) / 2.0, -(1.0 + c), (1.0 + c) / 2.0, 1.0 + al, -2.0 * c, 1.0 - al)
    }

    pub fn peaking(fs: f32, f: f32, q: f32, db: f32) -> Self {
        let (s, c) = Self::w0(fs, f);
        let a = 10f64.powf(db as f64 / 40.0);
        let al = s / (2.0 * q as f64);
        Self::norm(1.0 + al * a, -2.0 * c, 1.0 - al * a, 1.0 + al / a, -2.0 * c, 1.0 - al / a)
    }

    pub fn lowshelf(fs: f32, f: f32, db: f32) -> Self {
        let (s, c) = Self::w0(fs, f);
        let a = 10f64.powf(db as f64 / 40.0);
        let k = 2.0 * a.sqrt() * s / 2.0 * 2f64.sqrt();
        Self::norm(
            a * ((a + 1.0) - (a - 1.0) * c + k),
            2.0 * a * ((a - 1.0) - (a + 1.0) * c),
            a * ((a + 1.0) - (a - 1.0) * c - k),
            (a + 1.0) + (a - 1.0) * c + k,
            -2.0 * ((a - 1.0) + (a + 1.0) * c),
            (a + 1.0) + (a - 1.0) * c - k,
        )
    }

    pub fn highshelf(fs: f32, f: f32, db: f32) -> Self {
        let (s, c) = Self::w0(fs, f);
        let a = 10f64.powf(db as f64 / 40.0);
        let k = 2.0 * a.sqrt() * s / 2.0 * 2f64.sqrt();
        Self::norm(
            a * ((a + 1.0) + (a - 1.0) * c + k),
            -2.0 * a * ((a - 1.0) + (a + 1.0) * c),
            a * ((a + 1.0) + (a - 1.0) * c - k),
            (a + 1.0) - (a - 1.0) * c + k,
            2.0 * ((a - 1.0) - (a + 1.0) * c),
            (a + 1.0) - (a - 1.0) * c - k,
        )
    }

    /// First-order low-pass (bilinear, prewarped).
    pub fn lowpass1(fs: f32, f: f32) -> Self {
        let k = (PI * (f as f64).min(fs as f64 * 0.49) / fs as f64).tan();
        let b0 = k / (1.0 + k);
        Self { b0, b1: b0, b2: 0.0, a1: (k - 1.0) / (k + 1.0), a2: 0.0, z1: 0.0, z2: 0.0 }
    }

    /// First-order high-pass (bilinear, prewarped).
    pub fn highpass1(fs: f32, f: f32) -> Self {
        let k = (PI * (f as f64).min(fs as f64 * 0.49) / fs as f64).tan();
        let b0 = 1.0 / (1.0 + k);
        Self { b0, b1: -b0, b2: 0.0, a1: (k - 1.0) / (k + 1.0), a2: 0.0, z1: 0.0, z2: 0.0 }
    }

    /// Replace the coefficients while keeping the filter state (no click on parameter change).
    pub fn set_coefs(&mut self, o: &Biquad) {
        self.b0 = o.b0;
        self.b1 = o.b1;
        self.b2 = o.b2;
        self.a1 = o.a1;
        self.a2 = o.a2;
    }

    pub fn reset(&mut self) {
        self.z1 = 0.0;
        self.z2 = 0.0;
    }

    #[inline]
    pub fn process(&mut self, x: f32) -> f32 {
        let x = x as f64;
        let y = self.b0 * x + self.z1;
        self.z1 = self.b1 * x - self.a1 * y + self.z2;
        self.z2 = self.b2 * x - self.a2 * y;
        // WASM cannot enable flush-to-zero: keep the state out of the subnormal range.
        if self.z1.abs() < 1e-30 {
            self.z1 = 0.0;
        }
        if self.z2.abs() < 1e-30 {
            self.z2 = 0.0;
        }
        y as f32
    }

    /// Magnitude response at `f` Hz (for tests and calibration).
    pub fn magnitude(&self, f: f32, fs: f32) -> f64 {
        let w = 2.0 * PI * f as f64 / fs as f64;
        let (c1, s1) = (w.cos(), -w.sin());
        let (c2, s2) = ((2.0 * w).cos(), -(2.0 * w).sin());
        let nr = self.b0 + self.b1 * c1 + self.b2 * c2;
        let ni = self.b1 * s1 + self.b2 * s2;
        let dr = 1.0 + self.a1 * c1 + self.a2 * c2;
        let di = self.a1 * s1 + self.a2 * s2;
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
    fn responses() {
        let fs = 48000.0;
        let lp = Biquad::lowpass(fs, 1000.0, 0.7071);
        assert!((db(lp.magnitude(1000.0, fs)) + 3.01).abs() < 0.1);
        assert!(db(lp.magnitude(10000.0, fs)) < -35.0);
        let hp = Biquad::highpass(fs, 100.0, 0.7071);
        assert!((db(hp.magnitude(100.0, fs)) + 3.01).abs() < 0.1);
        let pk = Biquad::peaking(fs, 1000.0, 1.0, 6.0);
        assert!((db(pk.magnitude(1000.0, fs)) - 6.0).abs() < 0.05);
        let ls = Biquad::lowshelf(fs, 200.0, 6.0);
        assert!((db(ls.magnitude(20.0, fs)) - 6.0).abs() < 0.2);
        assert!(db(ls.magnitude(5000.0, fs)).abs() < 0.2);
        let hs = Biquad::highshelf(fs, 3000.0, -6.0);
        assert!((db(hs.magnitude(20000.0, fs)) + 6.0).abs() < 0.3);
        assert!(db(hs.magnitude(100.0, fs)).abs() < 0.1);
        let lp1 = Biquad::lowpass1(192000.0, 5000.0);
        assert!((db(lp1.magnitude(5000.0, 192000.0)) + 3.01).abs() < 0.1);
        let hp1 = Biquad::highpass1(192000.0, 20.0);
        assert!((db(hp1.magnitude(20.0, 192000.0)) + 3.01).abs() < 0.1);
    }
}

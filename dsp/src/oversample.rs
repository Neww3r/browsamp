//! 4x oversampling built from two cascaded polyphase IIR half-band stages
//! (allpass-based, after Laurent de Soras' HIIR). Near-zero group delay, unlike a linear-phase FIR.

use std::f64::consts::PI;

/// Half-band allpass coefficients for `n` coefficients and a normalized transition bandwidth.
pub fn design_halfband(n: usize, transition: f64) -> Vec<f64> {
    let order = n * 2 + 1;
    let mut k = ((1.0 - transition * 2.0) * PI / 4.0).tan();
    k *= k;
    let kksqrt = (1.0 - k * k).powf(0.25);
    let e = 0.5 * (1.0 - kksqrt) / (1.0 + kksqrt);
    let e4 = e.powi(4);
    let q = e * (1.0 + e4 * (2.0 + e4 * (15.0 + 150.0 * e4)));
    (0..n)
        .map(|i| {
            let c = (i + 1) as f64;
            let num = acc_num(q, order, c) * q.powf(0.25);
            let den = acc_den(q, order, c) + 0.5;
            let ww = num / den;
            let wwsq = ww * ww;
            let x = ((1.0 - wwsq * k) * (1.0 - wwsq / k)).sqrt() / (1.0 + wwsq);
            (1.0 - x) / (1.0 + x)
        })
        .collect()
}

fn acc_num(q: f64, order: usize, c: f64) -> f64 {
    let (mut r, mut j) = (0.0, 1.0);
    for i in 0..1000i32 {
        let t = q.powi(i * (i + 1)) * (((i * 2 + 1) as f64) * c * PI / order as f64).sin() * j;
        r += t;
        j = -j;
        if t.abs() <= 1e-100 {
            break;
        }
    }
    r
}

fn acc_den(q: f64, order: usize, c: f64) -> f64 {
    let (mut r, mut j) = (0.0, -1.0);
    for i in 1..1000i32 {
        let t = q.powi(i * i) * (((i * 2) as f64) * c * PI / order as f64).cos() * j;
        r += t;
        j = -j;
        if t.abs() <= 1e-100 {
            break;
        }
    }
    r
}

/// Two parallel chains of first-order allpasses (in z^-2 of the high rate). `N` must be even.
#[derive(Clone, Copy)]
struct AllpassPair<const N: usize> {
    c: [f32; N],
    x: [f32; N],
    y: [f32; N],
}

impl<const N: usize> AllpassPair<N> {
    fn new(transition: f64) -> Self {
        let mut c = [0f32; N];
        for (d, s) in c.iter_mut().zip(design_halfband(N, transition)) {
            *d = s as f32;
        }
        Self { c, x: [0.0; N], y: [0.0; N] }
    }

    #[inline(always)]
    fn run(&mut self, mut s0: f32, mut s1: f32) -> (f32, f32) {
        let mut i = 0;
        while i < N {
            let t0 = (s0 - self.y[i]) * self.c[i] + self.x[i];
            let t1 = (s1 - self.y[i + 1]) * self.c[i + 1] + self.x[i + 1];
            self.x[i] = s0;
            self.x[i + 1] = s1;
            self.y[i] = t0;
            self.y[i + 1] = t1;
            s0 = t0;
            s1 = t1;
            i += 2;
        }
        (s0, s1)
    }

    fn reset(&mut self) {
        self.x = [0.0; N];
        self.y = [0.0; N];
    }
}

#[derive(Clone, Copy)]
pub struct Up2<const N: usize>(AllpassPair<N>);
#[derive(Clone, Copy)]
pub struct Down2<const N: usize>(AllpassPair<N>);

impl<const N: usize> Up2<N> {
    pub fn new(transition: f64) -> Self {
        Self(AllpassPair::new(transition))
    }
    #[inline(always)]
    pub fn process(&mut self, x: f32) -> (f32, f32) {
        self.0.run(x, x)
    }
}

impl<const N: usize> Down2<N> {
    pub fn new(transition: f64) -> Self {
        Self(AllpassPair::new(transition))
    }
    /// `a` is the earlier sample, `b` the later one.
    #[inline(always)]
    pub fn process(&mut self, a: f32, b: f32) -> f32 {
        let (s0, s1) = self.0.run(b, a);
        0.5 * (s0 + s1)
    }
}

/// Inner stage (1x <-> 2x) needs a steep transition; outer stage (2x <-> 4x) can be relaxed
/// because the signal is already band-limited by the inner stage.
const N1: usize = 12;
const TBW1: f64 = 0.035;
const N2: usize = 4;
const TBW2: f64 = 0.15;

/// Tiny DC bias keeping allpass states out of the (slow) subnormal range during silence.
const ANTI_DENORMAL: f32 = 1e-18;

pub struct Oversampler4 {
    up1: Up2<N1>,
    up2: Up2<N2>,
    dn2: Down2<N2>,
    dn1: Down2<N1>,
}

impl Default for Oversampler4 {
    fn default() -> Self {
        Self::new()
    }
}

impl Oversampler4 {
    pub const FACTOR: usize = 4;

    pub fn new() -> Self {
        Self { up1: Up2::new(TBW1), up2: Up2::new(TBW2), dn2: Down2::new(TBW2), dn1: Down2::new(TBW1) }
    }

    pub fn reset(&mut self) {
        self.up1.0.reset();
        self.up2.0.reset();
        self.dn2.0.reset();
        self.dn1.0.reset();
    }

    /// Runs `f` on the four oversampled samples corresponding to one input sample.
    #[inline(always)]
    pub fn process(&mut self, x: f32, mut f: impl FnMut(f32) -> f32) -> f32 {
        let (a, b) = self.up1.process(x + ANTI_DENORMAL);
        let (a0, a1) = self.up2.process(a);
        let (b0, b1) = self.up2.process(b);
        let (a0, a1, b0, b1) = (f(a0), f(a1), f(b0), f(b1));
        let a = self.dn2.process(a0, a1);
        let b = self.dn2.process(b0, b1);
        self.dn1.process(a, b)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sine_rms_through(f: impl Fn(&mut Oversampler4, f32) -> f32, freq: f64, fs: f64) -> f64 {
        let mut os = Oversampler4::new();
        let n = 48000;
        let mut acc = 0.0;
        for i in 0..n {
            let x = (2.0 * PI * freq * i as f64 / fs).sin() as f32;
            let y = f(&mut os, x) as f64;
            if i > n / 2 {
                acc += y * y;
            }
        }
        (acc / (n / 2) as f64).sqrt() * 2f64.sqrt()
    }

    #[test]
    fn coefficients_are_valid_allpass() {
        for c in design_halfband(N1, TBW1).iter().chain(design_halfband(N2, TBW2).iter()) {
            assert!(*c > 0.0 && *c < 1.0, "coef {c}");
        }
    }

    #[test]
    fn passband_is_flat() {
        let fs = 48000.0;
        for &f in &[100.0, 1000.0, 5000.0, 12000.0, 18000.0] {
            let g = sine_rms_through(|os, x| os.process(x, |s| s), f, fs);
            let db = 20.0 * g.log10();
            assert!(db.abs() < 0.1, "passband {f} Hz: {db:.3} dB");
        }
    }

    /// Feeds a tone that only exists at the high rate (above the base Nyquist) into the
    /// downsampler: anything that comes out is aliasing.
    #[test]
    fn alias_rejection() {
        let fs = 48000.0;
        for &f_hi in &[28000.0, 40000.0, 60000.0, 90000.0] {
            let mut dn2 = Down2::<N2>::new(TBW2);
            let mut dn1 = Down2::<N1>::new(TBW1);
            let fs4 = fs * 4.0;
            let n = 48000;
            let mut acc = 0.0;
            for i in 0..n {
                let s = |k: usize| (2.0 * PI * f_hi * (4 * i + k) as f64 / fs4).sin() as f32;
                let a = dn2.process(s(0), s(1));
                let b = dn2.process(s(2), s(3));
                let y = dn1.process(a, b) as f64;
                if i > n / 2 {
                    acc += y * y;
                }
            }
            let rms = (acc / (n / 2) as f64).sqrt() * 2f64.sqrt();
            let db = 20.0 * rms.log10();
            assert!(db < -80.0, "alias at {f_hi} Hz: {db:.1} dB");
        }
    }
}

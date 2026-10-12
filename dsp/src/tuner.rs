//! YIN pitch detector on a decimated copy of the input. Analysis runs ~20 times per second,
//! spread over the following samples (one lag per decimated sample) so that no audio block
//! ever pays for a whole analysis at once.

use crate::biquad::Biquad;

const TARGET_RATE: f32 = 16000.0;
const WINDOW: usize = 1024;
const MAX_TAU: usize = 320; // ~50 Hz at 16 kHz
const BUF: usize = WINDOW + MAX_TAU;
const THRESHOLD: f32 = 0.12;

pub struct Tuner {
    decim: usize,
    phase: usize,
    rate: f32,
    aa1: Biquad,
    aa2: Biquad,
    ring: Vec<f32>,
    w: usize,
    hop: usize,
    since: usize,
    lin: Vec<f32>,
    diff: Vec<f32>,
    raw: Vec<f32>,
    /// Next lag to evaluate, 0 when no analysis is in progress.
    next_tau: usize,
    running: f32,
    freq: f32,
    clarity: f32,
}

impl Tuner {
    pub fn new(sr: f32) -> Self {
        let decim = (sr / TARGET_RATE).round().max(1.0) as usize;
        let rate = sr / decim as f32;
        Self {
            decim,
            phase: 0,
            rate,
            aa1: Biquad::lowpass(sr, rate * 0.4, 0.54),
            aa2: Biquad::lowpass(sr, rate * 0.4, 1.31),
            ring: vec![0.0; BUF],
            w: 0,
            // An analysis takes MAX_TAU samples, so it must finish before the next one starts.
            hop: ((rate / 20.0) as usize).max(MAX_TAU + 1),
            since: 0,
            lin: vec![0.0; BUF],
            diff: vec![0.0; MAX_TAU + 1],
            raw: vec![0.0; MAX_TAU + 1],
            next_tau: 0,
            running: 0.0,
            freq: 0.0,
            clarity: 0.0,
        }
    }

    /// Detected fundamental in Hz, 0 when nothing reliable is playing.
    pub fn freq(&self) -> f32 {
        self.freq
    }

    pub fn clarity(&self) -> f32 {
        self.clarity
    }

    #[inline]
    pub fn push(&mut self, x: f32) {
        let y = self.aa2.process(self.aa1.process(x));
        self.phase += 1;
        if self.phase < self.decim {
            return;
        }
        self.phase = 0;
        self.ring[self.w] = y;
        self.w = (self.w + 1) % BUF;
        self.since += 1;
        if self.next_tau > 0 {
            self.step();
        }
        if self.since >= self.hop {
            self.since = 0;
            self.begin();
        }
    }

    /// Snapshots the ring buffer and starts a new analysis.
    fn begin(&mut self) {
        let (a, b) = self.ring.split_at(self.w);
        self.lin[..b.len()].copy_from_slice(b);
        self.lin[b.len()..].copy_from_slice(a);
        let x = &self.lin;

        let energy: f32 = x[..WINDOW].iter().map(|v| v * v).sum::<f32>() / WINDOW as f32;
        if energy < 1e-7 {
            // below about -70 dBFS RMS: nothing to tune
            self.freq = 0.0;
            self.clarity = 0.0;
            self.next_tau = 0;
            return;
        }
        self.diff[0] = 1.0;
        self.running = 0.0;
        self.next_tau = 1;
    }

    /// Difference function + cumulative mean normalization for one lag.
    fn step(&mut self) {
        let tau = self.next_tau;
        let x = &self.lin;
        let mut d = 0.0;
        for j in 0..WINDOW {
            let t = x[j] - x[j + tau];
            d += t * t;
        }
        self.running += d;
        self.raw[tau] = d;
        self.diff[tau] = if self.running > 0.0 { d * tau as f32 / self.running } else { 1.0 };
        if tau == MAX_TAU {
            self.next_tau = 0;
            self.pick();
        } else {
            self.next_tau += 1;
        }
    }

    fn pick(&mut self) {
        let min_tau = (self.rate / 1400.0) as usize;
        let mut tau = min_tau.max(2);
        let mut found = None;
        while tau < MAX_TAU {
            if self.diff[tau] < THRESHOLD {
                while tau + 1 < MAX_TAU && self.diff[tau + 1] < self.diff[tau] {
                    tau += 1;
                }
                found = Some(tau);
                break;
            }
            tau += 1;
        }
        let Some(t) = found else {
            self.freq = 0.0;
            self.clarity = 0.0;
            return;
        };
        // Parabolic interpolation on the raw difference function: the normalized one is
        // skewed by the running mean and biases high notes by a cent or more.
        let (y0, y1, y2) = (self.raw[t - 1], self.raw[t], self.raw[t + 1]);
        let den = y0 - 2.0 * y1 + y2;
        let shift = if den.abs() > 1e-12 { 0.5 * (y0 - y2) / den } else { 0.0 };
        self.freq = self.rate / (t as f32 + shift);
        self.clarity = 1.0 - self.diff[t];
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f32::consts::PI;

    fn cents(a: f32, b: f32) -> f32 {
        1200.0 * (a / b).log2()
    }

    #[test]
    fn sines_within_one_cent() {
        let sr = 48000.0;
        for &f in &[82.41f32, 110.0, 146.83, 196.0, 246.94, 329.63, 440.0, 659.26] {
            let mut t = Tuner::new(sr);
            for i in 0..(sr as usize / 2) {
                t.push(0.2 * (2.0 * PI * f * i as f32 / sr).sin());
            }
            let c = cents(t.freq(), f);
            assert!(c.abs() < 1.0, "{f} Hz -> {} Hz ({c:.2} cents)", t.freq());
        }
    }

    #[test]
    fn string_like_signal() {
        // Rich harmonics with a weak fundamental: YIN must not jump an octave.
        let sr = 44100.0;
        let f = 82.41f32;
        let mut t = Tuner::new(sr);
        for i in 0..(sr as usize / 2) {
            let ph = 2.0 * PI * f * i as f32 / sr;
            let x = 0.3 * ph.sin() + 0.5 * (2.0 * ph).sin() + 0.4 * (3.0 * ph).sin() + 0.2 * (4.0 * ph).sin();
            t.push(0.3 * x);
        }
        let c = cents(t.freq(), f);
        assert!(c.abs() < 1.5, "{} Hz ({c:.2} cents)", t.freq());
    }

    #[test]
    fn silence_reports_nothing() {
        let mut t = Tuner::new(48000.0);
        for _ in 0..24000 {
            t.push(0.0);
        }
        assert_eq!(t.freq(), 0.0);
    }
}

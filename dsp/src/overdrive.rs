//! Tube-Screamer-style overdrive. Runs at the oversampled rate, in front of the amp.
//!
//! The clipping branch only sees the signal above ~720 Hz and is added back to the clean
//! signal, which is what gives this circuit its mid hump and keeps the low end tight.

use crate::biquad::Biquad;
use crate::smooth::Smoother;
use crate::util::{fast_tanh, log_map};

pub struct Overdrive {
    fs: f32,
    hp: Biquad,
    clip_lp: Biquad,
    tone: Biquad,
    tone_knob: f32,
    drive: Smoother,
    level: Smoother,
    on: Smoother,
}

impl Overdrive {
    pub fn new(fs: f32) -> Self {
        let mut o = Self {
            fs,
            hp: Biquad::highpass1(fs, 720.0),
            clip_lp: Biquad::lowpass1(fs, 6000.0),
            tone: Biquad::lowpass1(fs, 2000.0),
            tone_knob: -1.0,
            drive: Smoother::new(10.0, 20.0, fs),
            level: Smoother::new(1.0, 20.0, fs),
            on: Smoother::new(0.0, 8.0, fs),
        };
        o.set_tone(5.0);
        o
    }

    /// 0..10 → clipping gain 2..120.
    pub fn set_drive(&mut self, d: f32) {
        self.drive.set(log_map(d.clamp(0.0, 10.0) / 10.0, 2.0, 120.0));
    }

    /// 0..10 → tone low-pass 550 Hz..7 kHz.
    pub fn set_tone(&mut self, t: f32) {
        let t = t.clamp(0.0, 10.0);
        if t != self.tone_knob {
            self.tone_knob = t;
            self.tone.set_coefs(&Biquad::lowpass1(self.fs, log_map(t / 10.0, 550.0, 7000.0)));
        }
    }

    /// 0..10 → -20..+20 dB, unity at noon.
    pub fn set_level(&mut self, l: f32) {
        self.level.set(log_map(l.clamp(0.0, 10.0) / 10.0, 0.1, 10.0));
    }

    pub fn set_on(&mut self, on: bool) {
        self.on.set(if on { 1.0 } else { 0.0 });
    }

    #[inline]
    pub fn process(&mut self, x: f32) -> f32 {
        let on = self.on.next();
        let drive = self.drive.next();
        let level = self.level.next();
        if on <= 1e-4 {
            return x;
        }
        // Silicon diodes in the feedback loop: soft and symmetric. The clipped branch peaks
        // around a typical pickup level so the pedal stays near unity at noon.
        let clipped = 0.22 * fast_tanh(self.hp.process(x) * drive * 4.0);
        let y = self.tone.process(x + self.clip_lp.process(clipped)) * level;
        x + (y - x) * on
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f32::consts::PI;

    /// Share of the output power that is not the fundamental (distortion + harmonics).
    fn harmonic_share(od: &mut Overdrive, fs: f32) -> f32 {
        let f = 440.0f64;
        let n = (fs * 0.5) as usize;
        let out: Vec<f64> = (0..n).map(|i| od.process(0.25 * (2.0 * PI * f as f32 * i as f32 / fs).sin()) as f64).collect();
        let tail = &out[n / 2..];
        let (mut c, mut s) = (0.0, 0.0);
        for (i, v) in tail.iter().enumerate() {
            let ph = 2.0 * std::f64::consts::PI * f * (i + n / 2) as f64 / fs as f64;
            c += v * ph.cos();
            s += v * ph.sin();
        }
        let amp = 2.0 * (c * c + s * s).sqrt() / tail.len() as f64;
        let total = tail.iter().map(|v| v * v).sum::<f64>() / tail.len() as f64;
        (1.0 - (amp * amp / 2.0) / total).max(0.0) as f32
    }

    #[test]
    fn drive_adds_harmonics() {
        let fs = 192000.0;
        let mut lo = Overdrive::new(fs);
        lo.set_on(true);
        lo.set_drive(0.0);
        lo.drive.reset(2.0);
        let mut hi = Overdrive::new(fs);
        hi.set_on(true);
        hi.set_drive(10.0);
        hi.drive.reset(120.0);
        let a = harmonic_share(&mut lo, fs);
        let b = harmonic_share(&mut hi, fs);
        assert!(b > a * 2.0, "low drive {a:.3}, high drive {b:.3}");
    }

    #[test]
    fn switching_does_not_click() {
        let fs = 192000.0;
        let mut od = Overdrive::new(fs);
        od.set_drive(8.0);
        let mut prev = 0.0;
        let mut worst = 0f32;
        for i in 0..(fs as usize) {
            if i == 20000 {
                od.set_on(true);
            }
            if i == 120000 {
                od.set_on(false);
            }
            let y = od.process(0.3 * (2.0 * PI * 110.0 * i as f32 / fs).sin());
            assert!(y.is_finite());
            worst = worst.max((y - prev).abs());
            prev = y;
        }
        // A 110 Hz sine at 192 kHz moves by ~0.001 per sample: a click would be far larger.
        assert!(worst < 0.05, "{worst}");
    }
}

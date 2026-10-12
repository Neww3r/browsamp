//! Optical-style compressor pedal: RMS detection, soft knee, 4:1, slow program-dependent
//! release, automatic make-up gain and a dry/wet blend for parallel compression.

use crate::smooth::Smoother;
use crate::util::{db_to_lin, one_pole_coef};

const RATIO: f32 = 4.0;
const KNEE_DB: f32 = 8.0;

pub struct Comp {
    sr: f32,
    env: f32,
    env_coef: f32,
    gr_db: f32,
    att: f32,
    rel_fast: f32,
    rel_slow: f32,
    threshold_db: f32,
    makeup_db: f32,
    level: Smoother,
    blend: Smoother,
    on: Smoother,
}

impl Comp {
    pub fn new(sr: f32) -> Self {
        let mut c = Self {
            sr,
            env: 0.0,
            env_coef: one_pole_coef(5.0, sr),
            gr_db: 0.0,
            att: 0.0,
            rel_fast: one_pole_coef(90.0, sr),
            rel_slow: one_pole_coef(700.0, sr),
            threshold_db: -25.0,
            makeup_db: 0.0,
            level: Smoother::new(1.0, 20.0, sr),
            blend: Smoother::new(1.0, 20.0, sr),
            on: Smoother::new(0.0, 8.0, sr),
        };
        c.set_sustain(5.0);
        c.set_attack(5.0);
        c
    }

    /// 0..10: lower threshold and more make-up gain.
    pub fn set_sustain(&mut self, s: f32) {
        let s = s.clamp(0.0, 10.0);
        self.threshold_db = -12.0 - s * 3.3;
        // Compensate part of the gain reduction a typical guitar note gets.
        self.makeup_db = -self.threshold_db * (1.0 - 1.0 / RATIO) * 0.4;
    }

    /// 0..10: 1 ms (snappy, squashes the pick) to 40 ms (lets the attack through).
    pub fn set_attack(&mut self, a: f32) {
        self.att = one_pole_coef(1.0 + a.clamp(0.0, 10.0) * 3.9, self.sr);
    }

    pub fn set_level_db(&mut self, db: f32) {
        self.level.set(db_to_lin(db.clamp(-24.0, 24.0)));
    }

    pub fn set_blend(&mut self, b: f32) {
        self.blend.set(b.clamp(0.0, 1.0));
    }

    pub fn set_on(&mut self, on: bool) {
        self.on.set(if on { 1.0 } else { 0.0 });
    }

    fn gain_reduction_db(&self, level_db: f32) -> f32 {
        let over = level_db - self.threshold_db;
        let slope = 1.0 - 1.0 / RATIO;
        if over <= -KNEE_DB / 2.0 {
            0.0
        } else if over >= KNEE_DB / 2.0 {
            over * slope
        } else {
            let t = over + KNEE_DB / 2.0;
            slope * t * t / (2.0 * KNEE_DB)
        }
    }

    pub fn current_gr_db(&self) -> f32 {
        self.gr_db
    }

    #[inline]
    pub fn process(&mut self, x: f32) -> f32 {
        let on = self.on.next();
        let level = self.level.next();
        let blend = self.blend.next();
        // Keep the detector running while bypassed so switching on is seamless.
        self.env += (x * x - self.env) * self.env_coef;
        let level_db = 10.0 * (self.env + 1e-12).log10() + 3.0; // RMS of a sine ≈ peak - 3 dB
        let target = self.gain_reduction_db(level_db);
        let c = if target > self.gr_db {
            self.att
        } else if self.gr_db > 6.0 {
            // Opto cells release fast from deep compression, then slowly.
            self.rel_fast
        } else {
            self.rel_slow
        };
        self.gr_db += (target - self.gr_db) * c;
        let wet = x * db_to_lin(self.makeup_db - self.gr_db);
        let out = (x + (wet - x) * blend) * level;
        if on <= 1e-4 { x } else { x + (out - x) * on }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f32::consts::PI;

    fn run(c: &mut Comp, amp: f32, n: usize) -> f32 {
        let mut peak = 0f32;
        for i in 0..n {
            let y = c.process(amp * (2.0 * PI * 220.0 * i as f32 / 48000.0).sin());
            if i > n / 2 {
                peak = peak.max(y.abs());
            }
        }
        peak
    }

    #[test]
    fn more_sustain_more_reduction() {
        let mut lo = Comp::new(48000.0);
        lo.set_on(true);
        lo.set_sustain(1.0);
        let mut hi = Comp::new(48000.0);
        hi.set_on(true);
        hi.set_sustain(9.0);
        run(&mut lo, 0.3, 48000);
        run(&mut hi, 0.3, 48000);
        assert!(hi.current_gr_db() > lo.current_gr_db() + 10.0, "{} vs {}", hi.current_gr_db(), lo.current_gr_db());
    }

    #[test]
    fn evens_out_dynamics() {
        let mut c = Comp::new(48000.0);
        c.set_on(true);
        c.set_sustain(7.0);
        let loud = run(&mut c, 0.5, 96000);
        let soft = run(&mut c, 0.05, 96000);
        let in_ratio = 20.0 * (0.5f32 / 0.05).log10();
        let out_ratio = 20.0 * (loud / soft).log10();
        assert!(out_ratio < in_ratio * 0.6, "in {in_ratio:.1} dB, out {out_ratio:.1} dB");
    }

    #[test]
    fn zero_blend_and_bypass_are_transparent() {
        let mut c = Comp::new(48000.0);
        c.set_on(true);
        c.set_blend(0.0);
        c.blend.reset(0.0);
        c.on.reset(1.0);
        for i in 0..4800 {
            let x = 0.4 * (i as f32 * 0.03).sin();
            assert!((c.process(x) - x).abs() < 1e-6);
        }
        let mut off = Comp::new(48000.0);
        for i in 0..4800 {
            let x = 0.4 * (i as f32 * 0.03).sin();
            assert_eq!(off.process(x), x);
        }
    }
}

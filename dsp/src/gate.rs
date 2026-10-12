//! Noise gate with hysteresis and hold, placed before the preamp.

use crate::util::{db_to_lin, one_pole_coef};

pub struct Gate {
    enabled: bool,
    thr_open: f32,
    thr_close: f32,
    env: f32,
    env_att: f32,
    env_rel: f32,
    gain: f32,
    g_att: f32,
    g_rel: f32,
    hold: u32,
    hold_ctr: u32,
    open: bool,
}

impl Gate {
    /// Threshold at or below this value disables the gate.
    pub const OFF_DB: f32 = -90.0;

    pub fn new(sr: f32) -> Self {
        let mut g = Self {
            enabled: false,
            thr_open: 0.0,
            thr_close: 0.0,
            env: 0.0,
            env_att: one_pole_coef(0.3, sr),
            env_rel: one_pole_coef(15.0, sr),
            gain: 1.0,
            g_att: one_pole_coef(0.5, sr),
            g_rel: one_pole_coef(60.0, sr),
            hold: (0.04 * sr) as u32,
            hold_ctr: 0,
            open: true,
        };
        g.set_threshold_db(Self::OFF_DB);
        g
    }

    pub fn set_threshold_db(&mut self, db: f32) {
        self.enabled = db > Self::OFF_DB + 0.5;
        self.thr_open = db_to_lin(db);
        self.thr_close = self.thr_open * 0.5; // 6 dB hysteresis
    }

    #[inline]
    pub fn process(&mut self, x: f32) -> f32 {
        if !self.enabled {
            self.gain = 1.0;
            self.open = true;
            return x;
        }
        let a = x.abs();
        let c = if a > self.env { self.env_att } else { self.env_rel };
        self.env += (a - self.env) * c;

        if !self.open {
            if self.env > self.thr_open {
                self.open = true;
                self.hold_ctr = self.hold;
            }
        } else if self.env > self.thr_close {
            self.hold_ctr = self.hold;
        } else if self.hold_ctr > 0 {
            self.hold_ctr -= 1;
        } else {
            self.open = false;
        }

        let target = if self.open { 1.0 } else { 0.0 };
        let c = if target > self.gain { self.g_att } else { self.g_rel };
        self.gain += (target - self.gain) * c;
        x * self.gain
    }

    pub fn is_open(&self) -> bool {
        self.open
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn closes_on_noise_and_opens_on_notes() {
        let sr = 48000.0;
        let mut g = Gate::new(sr);
        g.set_threshold_db(-50.0);
        // Noise floor around -60 dBFS: must end up closed and strongly attenuated.
        let mut seed = 1u32;
        let mut noise = || {
            seed = seed.wrapping_mul(1664525).wrapping_add(1013904223);
            ((seed >> 9) as f32 / (1 << 23) as f32 - 0.5) * 0.002
        };
        let mut last = 0.0;
        for _ in 0..(sr as usize) {
            last = g.process(noise());
        }
        assert!(!g.is_open());
        assert!(last.abs() < 1e-5);
        // A note at -20 dBFS must open within 2 ms.
        let mut opened_at = None;
        for i in 0..(sr as usize / 10) {
            let x = 0.1 * (i as f32 * 0.05).sin();
            g.process(x);
            if g.is_open() && opened_at.is_none() {
                opened_at = Some(i);
            }
        }
        assert!(opened_at.unwrap() < (0.002 * sr) as usize);
    }

    #[test]
    fn disabled_is_transparent() {
        let mut g = Gate::new(48000.0);
        for i in 0..1000 {
            let x = (i as f32 * 0.01).sin() * 1e-4;
            assert_eq!(g.process(x), x);
        }
    }
}

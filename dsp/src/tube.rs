//! Triode gain stage: coupling cap → gain → asymmetric saturation with grid-conduction
//! bias shift ("blocking") → Miller-capacitance low-pass. Runs at the oversampled rate.

use crate::biquad::Biquad;
use crate::util::{fast_tanh, one_pole_coef};

/// Asymmetric transfer curve: soft limit at +1 (grid conduction), more headroom before
/// cutoff on the negative side. The asymmetry produces even harmonics.
#[inline]
pub fn triode(x: f32) -> f32 {
    if x >= 0.0 { fast_tanh(x) } else { 1.6 * fast_tanh(x * (1.0 / 1.6)) }
}

#[derive(Clone, Copy, Debug)]
pub struct StageDef {
    pub gain: f32,
    pub bias: f32,
    pub hp_hz: f32,
    pub lp_hz: f32,
    /// Amount of bias shift caused by positive grid excursions.
    pub blocking: f32,
}

#[derive(Clone, Copy)]
pub struct TubeStage {
    hp: Biquad,
    lp: Biquad,
    gain: f32,
    bias: f32,
    dc: f32,
    blocking: f32,
    shift: f32,
    shift_att: f32,
    shift_rel: f32,
}

impl TubeStage {
    pub fn new(def: &StageDef, fs: f32) -> Self {
        Self {
            hp: Biquad::highpass1(fs, def.hp_hz),
            lp: Biquad::lowpass1(fs, def.lp_hz),
            gain: def.gain,
            bias: def.bias,
            dc: triode(def.bias),
            blocking: def.blocking,
            shift: 0.0,
            shift_att: one_pole_coef(4.0, fs),
            shift_rel: one_pole_coef(120.0, fs),
        }
    }

    #[inline]
    pub fn process(&mut self, x: f32) -> f32 {
        let v = self.hp.process(x) * self.gain;
        let g = v + self.bias - self.shift;
        // Grid current charges the coupling cap on strong positive swings and pushes the
        // operating point down, which is what gives tube preamps their "sag" on attacks.
        let target = self.blocking * (g - 0.5).max(0.0);
        let c = if target > self.shift { self.shift_att } else { self.shift_rel };
        self.shift += (target - self.shift) * c;
        // Tubes invert: alternating stages clip on alternating half-waves.
        -self.lp.process(triode(g) - self.dc)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn curve_is_bounded_and_asymmetric() {
        assert!(triode(100.0) <= 1.0);
        assert!(triode(-100.0) >= -1.6);
        assert!((triode(0.5) + triode(-0.5)).abs() > 1e-3);
        assert!((triode(1e-3) - 1e-3).abs() < 1e-6);
    }
}

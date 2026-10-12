//! Post-cabinet effects: delay → reverb → output level → safety clip. Mono in, stereo out.

use crate::amp::MAX_BLOCK;
use crate::delay::Delay;
use crate::reverb::Reverb;
use crate::smooth::Smoother;
use crate::util::{db_to_lin, safety_clip};

pub const F_DELAY_MIX: u32 = 0; // 0..1
pub const F_DELAY_TIME: u32 = 1; // ms
pub const F_DELAY_FB: u32 = 2; // 0..0.95
pub const F_DELAY_TONE: u32 = 3; // Hz
pub const F_REVERB_MIX: u32 = 4; // 0..1
pub const F_REVERB_DECAY: u32 = 5; // s
pub const F_REVERB_DAMP: u32 = 6; // 0..1
pub const F_REVERB_PREDELAY: u32 = 7; // ms
pub const F_OUTPUT: u32 = 8; // dB

pub struct Fx {
    pub in_buf: Vec<f32>,
    pub out_l: Vec<f32>,
    pub out_r: Vec<f32>,
    delay: Delay,
    reverb: Reverb,
    delay_mix: Smoother,
    reverb_mix: Smoother,
    level: Smoother,
}

impl Fx {
    pub fn new(sr: f32) -> Self {
        Self {
            in_buf: vec![0.0; MAX_BLOCK],
            out_l: vec![0.0; MAX_BLOCK],
            out_r: vec![0.0; MAX_BLOCK],
            delay: Delay::new(sr),
            reverb: Reverb::new(sr),
            delay_mix: Smoother::new(0.0, 20.0, sr),
            reverb_mix: Smoother::new(0.0, 20.0, sr),
            level: Smoother::new(1.0, 20.0, sr),
        }
    }

    pub fn set_param(&mut self, id: u32, v: f32) {
        match id {
            F_DELAY_MIX => self.delay_mix.set(v.clamp(0.0, 1.0)),
            F_DELAY_TIME => self.delay.set_time_ms(v),
            F_DELAY_FB => self.delay.set_feedback(v),
            F_DELAY_TONE => self.delay.set_tone_hz(v.clamp(500.0, 12000.0)),
            F_REVERB_MIX => self.reverb_mix.set(v.clamp(0.0, 1.0)),
            F_REVERB_DECAY => self.reverb.set_decay(v),
            F_REVERB_DAMP => self.reverb.set_damping(v),
            F_REVERB_PREDELAY => self.reverb.set_predelay_ms(v),
            F_OUTPUT => self.level.set(db_to_lin(v.clamp(-60.0, 12.0))),
            _ => {}
        }
    }

    pub fn process(&mut self, n: usize) {
        for i in 0..n.min(MAX_BLOCK) {
            let x = self.in_buf[i];
            let y = x + self.delay.process(x) * self.delay_mix.next();
            let (rl, rr) = self.reverb.process(y);
            let rm = self.reverb_mix.next();
            let g = self.level.next();
            self.out_l[i] = safety_clip((y + rl * rm) * g);
            self.out_r[i] = safety_clip((y + rr * rm) * g);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dry_path_is_transparent_and_output_bounded() {
        let mut fx = Fx::new(48000.0);
        for i in 0..128 {
            fx.in_buf[i] = 0.5 * (i as f32 * 0.1).sin();
        }
        fx.process(128);
        for i in 0..128 {
            assert!((fx.out_l[i] - fx.in_buf[i]).abs() < 1e-6);
        }
        fx.set_param(F_OUTPUT, 12.0);
        for _ in 0..100 {
            fx.in_buf[..128].fill(1.0);
            fx.process(128);
        }
        assert!(fx.out_l[..128].iter().all(|v| v.abs() <= 1.0));
    }
}

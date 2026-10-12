//! One-pole parameter smoothing to avoid zipper noise.

use crate::util::one_pole_coef;

#[derive(Clone, Copy, Debug)]
pub struct Smoother {
    cur: f32,
    target: f32,
    coef: f32,
}

impl Smoother {
    pub fn new(value: f32, time_ms: f32, sr: f32) -> Self {
        Self { cur: value, target: value, coef: one_pole_coef(time_ms, sr) }
    }

    pub fn set(&mut self, v: f32) {
        self.target = v;
    }

    pub fn reset(&mut self, v: f32) {
        self.cur = v;
        self.target = v;
    }

    pub fn target(&self) -> f32 {
        self.target
    }

    pub fn value(&self) -> f32 {
        self.cur
    }

    #[inline]
    pub fn next(&mut self) -> f32 {
        self.cur += (self.target - self.cur) * self.coef;
        self.cur
    }
}

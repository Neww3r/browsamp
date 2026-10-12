//! Mono digital delay with a darkening, softly saturating feedback loop.

use crate::biquad::Biquad;
use crate::smooth::Smoother;
use crate::util::fast_tanh;

pub struct Delay {
    sr: f32,
    buf: Vec<f32>,
    w: usize,
    time: Smoother,
    feedback: Smoother,
    lp: Biquad,
    hp: Biquad,
    tone_hz: f32,
}

impl Delay {
    pub const MAX_SECONDS: f32 = 2.0;

    pub fn new(sr: f32) -> Self {
        let len = (sr * Self::MAX_SECONDS) as usize + 4;
        Self {
            sr,
            buf: vec![0.0; len],
            w: 0,
            // Slow time smoothing gives a tape-like glide instead of clicks when turning the knob.
            time: Smoother::new(sr * 0.35, 120.0, sr),
            feedback: Smoother::new(0.35, 20.0, sr),
            lp: Biquad::lowpass1(sr, 4000.0),
            hp: Biquad::highpass1(sr, 120.0),
            tone_hz: 4000.0,
        }
    }

    pub fn set_time_ms(&mut self, ms: f32) {
        let max = (self.buf.len() - 3) as f32;
        self.time.set((ms * 0.001 * self.sr).clamp(1.0, max));
    }

    pub fn set_feedback(&mut self, fb: f32) {
        self.feedback.set(fb.clamp(0.0, 0.95));
    }

    pub fn set_tone_hz(&mut self, hz: f32) {
        if hz != self.tone_hz {
            self.tone_hz = hz;
            self.lp.set_coefs(&Biquad::lowpass1(self.sr, hz));
        }
    }

    /// Returns the wet signal only.
    #[inline]
    pub fn process(&mut self, x: f32) -> f32 {
        let len = self.buf.len();
        let d = self.time.next();
        let di = d as usize;
        let frac = d - di as f32;
        let i0 = (self.w + len - di) % len;
        let i1 = (i0 + len - 1) % len;
        let wet = self.buf[i0] + (self.buf[i1] - self.buf[i0]) * frac;
        let fb = self.hp.process(self.lp.process(wet)) * self.feedback.next();
        self.buf[self.w] = fast_tanh(x + fb);
        self.w = (self.w + 1) % len;
        wet
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn echo_arrives_on_time() {
        let sr = 48000.0;
        let mut d = Delay::new(sr);
        d.set_time_ms(100.0);
        d.time.reset(sr * 0.1);
        d.set_feedback(0.0);
        let mut first = None;
        for i in 0..10000 {
            let y = d.process(if i == 0 { 0.5 } else { 0.0 });
            if y.abs() > 0.1 && first.is_none() {
                first = Some(i);
            }
        }
        assert_eq!(first, Some(4800));
    }

    #[test]
    fn max_feedback_decays() {
        let sr = 48000.0;
        let mut d = Delay::new(sr);
        d.set_time_ms(50.0);
        d.set_feedback(1.0);
        let mut peak_late = 0f32;
        for i in 0..(sr as usize * 20) {
            let y = d.process(if i < 100 { 0.8 } else { 0.0 });
            if i > sr as usize * 18 {
                peak_late = peak_late.max(y.abs());
            }
        }
        assert!(peak_late < 0.05, "{peak_late}");
    }
}

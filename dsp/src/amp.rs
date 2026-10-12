//! Full amp chain: input gain → gate → compressor → [4x: overdrive → pre-filters → preamp
//! stages → tone stack → power stage] → DC block → output. The tuner taps the signal right
//! after the input gain.

use crate::biquad::Biquad;
use crate::comp::Comp;
use crate::gate::Gate;
use crate::models::{MAX_STAGES, MODELS, ModelDef};
use crate::overdrive::Overdrive;
use crate::oversample::Oversampler4;
use crate::poweramp::PowerAmp;
use crate::smooth::Smoother;
use crate::tonestack::Tonestack;
use crate::tube::{StageDef, TubeStage};
use crate::tuner::Tuner;
use crate::util::{db_to_lin, log_map};

pub const P_INPUT: u32 = 0; // dB
pub const P_GATE: u32 = 1; // dB, -90 = off
pub const P_GAIN: u32 = 2; // 0..10
pub const P_BASS: u32 = 3; // 0..1
pub const P_MID: u32 = 4;
pub const P_TREBLE: u32 = 5;
pub const P_PRESENCE: u32 = 6; // 0..1
pub const P_RESONANCE: u32 = 7; // 0..1
pub const P_MASTER: u32 = 8; // 0..1
pub const P_TUNER: u32 = 9; // 0/1
pub const P_TUNER_MUTE: u32 = 10; // 0/1
pub const P_COMP_ON: u32 = 11; // 0/1
pub const P_COMP_SUSTAIN: u32 = 12; // 0..10
pub const P_COMP_ATTACK: u32 = 13; // 0..10
pub const P_COMP_LEVEL: u32 = 14; // dB
pub const P_COMP_BLEND: u32 = 15; // 0..1
pub const P_OD_ON: u32 = 16; // 0/1
pub const P_OD_DRIVE: u32 = 17; // 0..10
pub const P_OD_TONE: u32 = 18; // 0..10
pub const P_OD_LEVEL: u32 = 19; // 0..10

pub const MAX_BLOCK: usize = 1024;

const IDLE_STAGE: StageDef = StageDef { gain: 1.0, bias: 0.0, hp_hz: 20.0, lp_hz: 20000.0, blocking: 0.0 };

pub struct Amp {
    os_sr: f32,
    pub in_buf: Vec<f32>,
    pub out_buf: Vec<f32>,
    model: &'static ModelDef,
    input_gain: Smoother,
    drive: Smoother,
    gate: Gate,
    comp: Comp,
    od: Overdrive,
    pre_hp: Biquad,
    pre_bright: Biquad,
    pre_mid: Biquad,
    os: Oversampler4,
    stages: [TubeStage; MAX_STAGES],
    n_stages: usize,
    ts: Tonestack,
    tone_target: [f32; 3],
    tone_cur: [f32; 3],
    power: PowerAmp,
    dc_out: Biquad,
    out_gain: Smoother,
    mute: Smoother,
    tuner: Tuner,
    tuner_on: bool,
    tuner_mute: bool,
    gain_knob: f32,
    master: f32,
}

impl Amp {
    pub fn new(sr: f32) -> Self {
        let os_sr = sr * Oversampler4::FACTOR as f32;
        let model = &MODELS[0];
        let mut amp = Self {
            os_sr,
            in_buf: vec![0.0; MAX_BLOCK],
            out_buf: vec![0.0; MAX_BLOCK],
            model,
            input_gain: Smoother::new(1.0, 20.0, sr),
            drive: Smoother::new(1.0, 20.0, sr),
            gate: Gate::new(sr),
            comp: Comp::new(sr),
            od: Overdrive::new(os_sr),
            pre_hp: Biquad::identity(),
            pre_bright: Biquad::identity(),
            pre_mid: Biquad::identity(),
            os: Oversampler4::new(),
            stages: [TubeStage::new(&IDLE_STAGE, os_sr); MAX_STAGES],
            n_stages: 0,
            ts: Tonestack::new(model.tonestack, os_sr),
            tone_target: [0.5; 3],
            tone_cur: [0.5; 3],
            power: PowerAmp::new(os_sr),
            dc_out: Biquad::highpass1(sr, 10.0),
            out_gain: Smoother::new(1.0, 20.0, sr),
            mute: Smoother::new(1.0, 8.0, sr),
            tuner: Tuner::new(sr),
            tuner_on: false,
            tuner_mute: false,
            gain_knob: 5.0,
            master: 0.5,
        };
        amp.set_model(1);
        amp.set_param(P_PRESENCE, 0.5);
        amp.set_param(P_RESONANCE, 0.5);
        amp
    }

    pub fn model_count() -> usize {
        MODELS.len()
    }

    pub fn set_model(&mut self, id: u32) {
        let m = &MODELS[(id as usize).min(MODELS.len() - 1)];
        self.model = m;
        // Pre-filters run oversampled, after the overdrive pedal, like the amp's input stage.
        self.pre_hp = Biquad::highpass(self.os_sr, m.pre_hp_hz, 0.707);
        self.pre_bright = Biquad::highshelf(self.os_sr, m.bright_hz, m.bright_db);
        self.pre_mid = Biquad::peaking(self.os_sr, m.mid_hz, 0.7, m.mid_db);
        self.n_stages = m.stages.len().min(MAX_STAGES);
        for (i, d) in m.stages.iter().take(MAX_STAGES).enumerate() {
            self.stages[i] = TubeStage::new(d, self.os_sr);
        }
        self.ts.set_components(m.tonestack);
        self.ts.set(self.tone_cur[0], self.tone_cur[1], self.tone_cur[2]);
        self.power.configure(m.sag, m.resonance_hz, m.presence_hz);
        self.os.reset();
        // Fade back in from silence so the switch never clicks.
        self.mute.reset(0.0);
        self.update_drives(true);
        self.out_gain.reset(m.out_gain);
    }

    fn update_drives(&mut self, snap: bool) {
        let d = log_map(self.gain_knob / 10.0, self.model.drive_min, self.model.drive_max);
        let p = log_map(self.master, self.model.power_min, self.model.power_max);
        if snap {
            self.drive.reset(d);
            self.power.reset_drive(p);
        } else {
            self.drive.set(d);
            self.power.set_drive(p);
        }
    }

    pub fn set_param(&mut self, id: u32, v: f32) {
        match id {
            P_INPUT => self.input_gain.set(db_to_lin(v.clamp(-24.0, 24.0))),
            P_GATE => self.gate.set_threshold_db(v),
            P_GAIN => {
                self.gain_knob = v.clamp(0.0, 10.0);
                self.update_drives(false);
            }
            P_BASS => self.tone_target[0] = v.clamp(0.0, 1.0),
            P_MID => self.tone_target[1] = v.clamp(0.0, 1.0),
            P_TREBLE => self.tone_target[2] = v.clamp(0.0, 1.0),
            P_PRESENCE => self.power.set_presence(v.clamp(0.0, 1.0) * 10.0 - 2.0),
            P_RESONANCE => self.power.set_resonance(v.clamp(0.0, 1.0) * 10.0 - 2.0),
            P_MASTER => {
                self.master = v.clamp(0.0, 1.0);
                self.update_drives(false);
            }
            P_TUNER => self.tuner_on = v > 0.5,
            P_TUNER_MUTE => self.tuner_mute = v > 0.5,
            P_COMP_ON => self.comp.set_on(v > 0.5),
            P_COMP_SUSTAIN => self.comp.set_sustain(v),
            P_COMP_ATTACK => self.comp.set_attack(v),
            P_COMP_LEVEL => self.comp.set_level_db(v),
            P_COMP_BLEND => self.comp.set_blend(v),
            P_OD_ON => self.od.set_on(v > 0.5),
            P_OD_DRIVE => self.od.set_drive(v),
            P_OD_TONE => self.od.set_tone(v),
            P_OD_LEVEL => self.od.set_level(v),
            _ => {}
        }
    }

    pub fn tuner_freq(&self) -> f32 {
        if self.tuner_on { self.tuner.freq() } else { 0.0 }
    }

    pub fn tuner_clarity(&self) -> f32 {
        self.tuner.clarity()
    }

    /// Processes `n` samples from `in_buf` into `out_buf`.
    pub fn process(&mut self, n: usize) {
        let n = n.min(MAX_BLOCK);

        // Tone controls are smoothed at block rate (recomputing a 3rd-order filter per sample
        // would be wasteful and is inaudible at 128-sample granularity).
        let mut changed = false;
        for i in 0..3 {
            let d = self.tone_target[i] - self.tone_cur[i];
            if d.abs() > 1e-4 {
                self.tone_cur[i] += d * 0.35;
                changed = true;
            }
        }
        if changed {
            self.ts.set(self.tone_cur[0], self.tone_cur[1], self.tone_cur[2]);
        }
        self.mute.set(if self.tuner_on && self.tuner_mute { 0.0 } else { 1.0 });

        let Self {
            in_buf, out_buf, input_gain, drive, gate, comp, od, pre_hp, pre_bright, pre_mid, os, stages, n_stages,
            ts, power, dc_out, out_gain, mute, tuner, tuner_on, ..
        } = self;
        let stages = &mut stages[..*n_stages];

        for i in 0..n {
            let x = in_buf[i] * input_gain.next();
            if *tuner_on {
                tuner.push(x);
            }
            let x = comp.process(gate.process(x));
            let d = drive.next();
            let y = os.process(x, |s| {
                let mut s = pre_mid.process(pre_bright.process(pre_hp.process(od.process(s)))) * d;
                for st in stages.iter_mut() {
                    s = st.process(s);
                }
                power.process(ts.process(s))
            });
            out_buf[i] = dc_out.process(y) * out_gain.next() * mute.next();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f32::consts::PI;

    /// Decaying plucked-string-like test signal at a typical DI level (~-12 dBFS peak).
    fn pluck(sr: f32, f: f32, len: usize) -> Vec<f32> {
        (0..len)
            .map(|i| {
                let t = i as f32 / sr;
                let env = (-t * 3.0).exp();
                let ph = 2.0 * PI * f * t;
                0.25 * env * (ph.sin() + 0.5 * (2.0 * ph).sin() + 0.3 * (3.0 * ph).sin() + 0.15 * (5.0 * ph).sin())
                    / 1.95
            })
            .collect()
    }

    fn run(amp: &mut Amp, input: &[f32]) -> Vec<f32> {
        let mut out = Vec::with_capacity(input.len());
        for chunk in input.chunks(128) {
            amp.in_buf[..chunk.len()].copy_from_slice(chunk);
            amp.process(chunk.len());
            out.extend_from_slice(&amp.out_buf[..chunk.len()]);
        }
        out
    }

    fn rms(x: &[f32]) -> f32 {
        (x.iter().map(|v| v * v).sum::<f32>() / x.len() as f32).sqrt()
    }

    #[test]
    fn stable_on_extreme_input() {
        let sr = 48000.0;
        for m in 0..Amp::model_count() as u32 {
            let mut amp = Amp::new(sr);
            amp.set_model(m);
            for (id, v) in [(P_GAIN, 10.0), (P_MASTER, 1.0), (P_BASS, 1.0), (P_TREBLE, 1.0), (P_INPUT, 24.0)] {
                amp.set_param(id, v);
            }
            let mut seed = 7u32;
            let input: Vec<f32> = (0..48000)
                .map(|i| {
                    seed = seed.wrapping_mul(1664525).wrapping_add(1013904223);
                    let noise = (seed >> 9) as f32 / (1 << 23) as f32 * 2.0 - 1.0;
                    if i < 24000 { noise } else { (i as f32 * 0.3).sin() }
                })
                .collect();
            let out = run(&mut amp, &input);
            for v in &out {
                assert!(v.is_finite() && v.abs() < 4.0, "model {m}: {v}");
            }
        }
    }

    #[test]
    fn silence_stays_silent_and_finite() {
        let mut amp = Amp::new(48000.0);
        amp.set_model(2);
        amp.set_param(P_GAIN, 10.0);
        let out = run(&mut amp, &vec![0.0; 96000]);
        assert!(out.iter().all(|v| v.is_finite()));
        assert!(rms(&out[48000..]) < 1e-4);
    }

    #[test]
    fn gain_knob_adds_harmonics() {
        let sr = 48000.0;
        let input = pluck(sr, 110.0, 24000);
        let mut lo = Amp::new(sr);
        lo.set_model(1);
        lo.set_param(P_GAIN, 0.0);
        let mut hi = Amp::new(sr);
        hi.set_model(1);
        hi.set_param(P_GAIN, 10.0);
        let a = run(&mut lo, &input);
        let b = run(&mut hi, &input);
        // Crest factor drops as the amp saturates.
        let crest = |x: &[f32]| x.iter().fold(0f32, |m, v| m.max(v.abs())) / rms(x);
        assert!(crest(&b[4800..]) < crest(&a[4800..]));
    }

    /// Prints the loudness of each model at noon settings (used to calibrate `out_gain`).
    #[test]
    fn model_levels() {
        let sr = 48000.0;
        let input = pluck(sr, 110.0, 48000);
        for m in 0..Amp::model_count() as u32 {
            let mut amp = Amp::new(sr);
            amp.set_model(m);
            let out = run(&mut amp, &input);
            let db = 20.0 * rms(&out[2400..24000]).log10();
            println!("model {} ({}): {db:.1} dBFS RMS", m, MODELS[m as usize].name);
            assert!(db > -40.0 && db < 0.0);
        }
    }

    #[test]
    fn realtime_budget() {
        let sr = 48000.0;
        let mut amp = Amp::new(sr);
        amp.set_model(2);
        amp.set_param(P_TUNER, 1.0);
        let input = pluck(sr, 82.0, 48000 * 4);
        let t = std::time::Instant::now();
        run(&mut amp, &input);
        let secs = t.elapsed().as_secs_f64();
        let load = secs / 4.0;
        println!("amp CPU load (native, {}): {:.2}%", if cfg!(debug_assertions) { "debug" } else { "release" }, load * 100.0);
        if !cfg!(debug_assertions) {
            assert!(load < 0.15);
        }
    }
}

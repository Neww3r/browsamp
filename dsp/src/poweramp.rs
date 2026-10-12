//! Push-pull power stage with supply sag, presence/resonance (negative-feedback shaping)
//! and output-transformer band limiting. Runs at the oversampled rate.

use crate::biquad::Biquad;
use crate::smooth::Smoother;
use crate::util::{fast_tanh, one_pole_coef};

pub struct PowerAmp {
    fs: f32,
    drive: Smoother,
    resonance: Biquad,
    presence: Biquad,
    res_hz: f32,
    pres_hz: f32,
    res_db: f32,
    pres_db: f32,
    sag_amount: f32,
    sag_env: f32,
    sag_att: f32,
    sag_rel: f32,
    ot_hp: Biquad,
    ot_lp: Biquad,
}

impl PowerAmp {
    pub fn new(fs: f32) -> Self {
        Self {
            fs,
            drive: Smoother::new(1.0, 20.0, fs),
            resonance: Biquad::identity(),
            presence: Biquad::identity(),
            res_hz: 100.0,
            pres_hz: 3500.0,
            res_db: 0.0,
            pres_db: 0.0,
            sag_amount: 0.0,
            sag_env: 0.0,
            sag_att: one_pole_coef(15.0, fs),
            sag_rel: one_pole_coef(200.0, fs),
            ot_hp: Biquad::highpass(fs, 45.0, 0.6),
            ot_lp: Biquad::lowpass(fs, 13000.0, 0.6),
        }
    }

    pub fn configure(&mut self, sag: f32, res_hz: f32, pres_hz: f32) {
        self.sag_amount = sag;
        self.res_hz = res_hz;
        self.pres_hz = pres_hz;
        self.set_resonance(self.res_db);
        self.set_presence(self.pres_db);
    }

    pub fn set_drive(&mut self, d: f32) {
        self.drive.set(d);
    }

    pub fn reset_drive(&mut self, d: f32) {
        self.drive.reset(d);
    }

    pub fn set_resonance(&mut self, db: f32) {
        self.res_db = db;
        self.resonance.set_coefs(&Biquad::peaking(self.fs, self.res_hz, 0.9, db));
    }

    pub fn set_presence(&mut self, db: f32) {
        self.pres_db = db;
        self.presence.set_coefs(&Biquad::highshelf(self.fs, self.pres_hz, db));
    }

    #[inline]
    pub fn process(&mut self, x: f32) -> f32 {
        let x = self.presence.process(self.resonance.process(x)) * self.drive.next();
        // Sagging supply lowers the clipping ceiling, compressing and fattening hard attacks.
        let supply = 1.0 - self.sag_amount * self.sag_env.min(1.0) * 0.5;
        let y = supply * fast_tanh(x / supply);
        let a = y.abs();
        let c = if a > self.sag_env { self.sag_att } else { self.sag_rel };
        self.sag_env += (a - self.sag_env) * c;
        self.ot_lp.process(self.ot_hp.process(y))
    }
}

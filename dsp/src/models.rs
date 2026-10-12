//! Amp voicings. Each model fixes the pre-filters, the preamp stage chain, the tone stack
//! components and the power stage character.

use crate::tonestack::{FENDER, MARSHALL, MODERN, TsComponents};
use crate::tube::StageDef;

pub struct ModelDef {
    pub name: &'static str,
    /// Input high-pass before the preamp: tightens the low end in high-gain voicings.
    pub pre_hp_hz: f32,
    pub bright_hz: f32,
    pub bright_db: f32,
    /// Mid push before the preamp ("tube screamer in front" for the high-gain model).
    pub mid_hz: f32,
    pub mid_db: f32,
    /// Range of the Gain knob (linear drive into the first stage).
    pub drive_min: f32,
    pub drive_max: f32,
    pub stages: &'static [StageDef],
    pub tonestack: TsComponents,
    /// Range of the Master knob (drive into the power stage).
    pub power_min: f32,
    pub power_max: f32,
    pub sag: f32,
    pub resonance_hz: f32,
    pub presence_hz: f32,
    /// Level compensation so models sit at a similar loudness.
    pub out_gain: f32,
}

pub const MODELS: [ModelDef; 3] = [
    ModelDef {
        name: "Clean",
        pre_hp_hz: 30.0,
        bright_hz: 2500.0,
        bright_db: 3.0,
        mid_hz: 800.0,
        mid_db: 0.0,
        drive_min: 0.25,
        drive_max: 5.0,
        stages: &[
            StageDef { gain: 1.0, bias: 0.15, hp_hz: 20.0, lp_hz: 16000.0, blocking: 0.05 },
            StageDef { gain: 2.0, bias: 0.2, hp_hz: 25.0, lp_hz: 13000.0, blocking: 0.1 },
        ],
        tonestack: FENDER,
        power_min: 0.3,
        power_max: 2.5,
        sag: 0.35,
        resonance_hz: 90.0,
        presence_hz: 4000.0,
        out_gain: 2.0,
    },
    ModelDef {
        name: "Crunch",
        pre_hp_hz: 60.0,
        bright_hz: 2000.0,
        bright_db: 4.0,
        mid_hz: 800.0,
        mid_db: 0.0,
        drive_min: 0.5,
        drive_max: 20.0,
        stages: &[
            StageDef { gain: 1.0, bias: 0.25, hp_hz: 30.0, lp_hz: 14000.0, blocking: 0.2 },
            StageDef { gain: 4.0, bias: 0.3, hp_hz: 60.0, lp_hz: 10000.0, blocking: 0.3 },
            StageDef { gain: 1.5, bias: 0.1, hp_hz: 20.0, lp_hz: 12000.0, blocking: 0.1 },
        ],
        tonestack: MARSHALL,
        power_min: 0.4,
        power_max: 3.5,
        sag: 0.25,
        resonance_hz: 100.0,
        presence_hz: 3500.0,
        out_gain: 0.4,
    },
    ModelDef {
        name: "High-gain",
        pre_hp_hz: 140.0,
        bright_hz: 3000.0,
        bright_db: 0.0,
        mid_hz: 750.0,
        mid_db: 6.0,
        drive_min: 1.0,
        drive_max: 50.0,
        stages: &[
            StageDef { gain: 1.0, bias: 0.3, hp_hz: 80.0, lp_hz: 12000.0, blocking: 0.3 },
            StageDef { gain: 6.0, bias: 0.3, hp_hz: 100.0, lp_hz: 8000.0, blocking: 0.3 },
            StageDef { gain: 4.0, bias: 0.25, hp_hz: 50.0, lp_hz: 7000.0, blocking: 0.3 },
            StageDef { gain: 1.5, bias: 0.1, hp_hz: 25.0, lp_hz: 9000.0, blocking: 0.1 },
        ],
        tonestack: MODERN,
        power_min: 0.4,
        power_max: 3.0,
        sag: 0.15,
        resonance_hz: 85.0,
        presence_hz: 3000.0,
        out_gain: 0.28,
    },
];

pub const MAX_STAGES: usize = 4;

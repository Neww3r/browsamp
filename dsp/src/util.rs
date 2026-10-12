//! Small numeric helpers shared by every DSP block.

#[inline]
pub fn db_to_lin(db: f32) -> f32 {
    10f32.powf(db / 20.0)
}

#[inline]
pub fn lin_to_db(lin: f32) -> f32 {
    20.0 * lin.max(1e-12).log10()
}

/// One-pole smoothing coefficient for a time constant in milliseconds.
#[inline]
pub fn one_pole_coef(ms: f32, sr: f32) -> f32 {
    if ms <= 0.0 {
        1.0
    } else {
        1.0 - (-1.0 / (ms * 0.001 * sr)).exp()
    }
}

/// Padé tanh approximation, exact at ±3 with zero slope there (C1 continuous).
#[inline]
pub fn fast_tanh(x: f32) -> f32 {
    let x = x.clamp(-3.0, 3.0);
    let x2 = x * x;
    x * (27.0 + x2) / (27.0 + 9.0 * x2)
}

/// Transparent below `knee`, then smoothly saturates to 1.0. Used as an ear-safety stage.
#[inline]
pub fn safety_clip(x: f32) -> f32 {
    const KNEE: f32 = 0.9;
    let a = x.abs();
    if a <= KNEE {
        x
    } else {
        let y = KNEE + (1.0 - KNEE) * fast_tanh((a - KNEE) / (1.0 - KNEE));
        y.copysign(x)
    }
}

/// Log mapping of a 0..1 control onto [min, max].
#[inline]
pub fn log_map(t: f32, min: f32, max: f32) -> f32 {
    min * (max / min).powf(t.clamp(0.0, 1.0))
}

//! browsamp DSP core, compiled to WebAssembly and driven from AudioWorklets.
//!
//! The ABI is plain `extern "C"` (no wasm-bindgen): the AudioWorklet scope has no
//! `TextDecoder`/`fetch`, and we want zero glue code on the audio thread. Each worklet
//! instantiates its own module instance, so the globals below are per-worklet.

pub mod amp;
pub mod biquad;
pub mod comp;
pub mod delay;
pub mod fx;
pub mod gate;
pub mod models;
pub mod overdrive;
pub mod oversample;
pub mod poweramp;
pub mod reverb;
pub mod smooth;
pub mod tonestack;
pub mod tube;
pub mod tuner;
pub mod util;

use std::ptr::addr_of_mut;

static mut AMP: Option<amp::Amp> = None;
static mut FX: Option<fx::Fx> = None;

fn amp() -> &'static mut amp::Amp {
    // SAFETY: a module instance is only ever driven from its own AudioWorklet thread.
    unsafe { (*addr_of_mut!(AMP)).as_mut().expect("amp_init not called") }
}

fn fx() -> &'static mut fx::Fx {
    // SAFETY: see `amp()`.
    unsafe { (*addr_of_mut!(FX)).as_mut().expect("fx_init not called") }
}

#[unsafe(no_mangle)]
pub extern "C" fn max_block() -> u32 {
    amp::MAX_BLOCK as u32
}

#[unsafe(no_mangle)]
pub extern "C" fn amp_init(sample_rate: f32) {
    // SAFETY: called once from the worklet constructor, before any processing.
    unsafe { *addr_of_mut!(AMP) = Some(amp::Amp::new(sample_rate)) }
}

#[unsafe(no_mangle)]
pub extern "C" fn amp_in_ptr() -> *mut f32 {
    amp().in_buf.as_mut_ptr()
}

#[unsafe(no_mangle)]
pub extern "C" fn amp_out_ptr() -> *mut f32 {
    amp().out_buf.as_mut_ptr()
}

#[unsafe(no_mangle)]
pub extern "C" fn amp_process(n: u32) {
    amp().process(n as usize)
}

#[unsafe(no_mangle)]
pub extern "C" fn amp_set_param(id: u32, value: f32) {
    amp().set_param(id, value)
}

#[unsafe(no_mangle)]
pub extern "C" fn amp_set_model(id: u32) {
    amp().set_model(id)
}

#[unsafe(no_mangle)]
pub extern "C" fn amp_tuner_freq() -> f32 {
    amp().tuner_freq()
}

#[unsafe(no_mangle)]
pub extern "C" fn amp_tuner_clarity() -> f32 {
    amp().tuner_clarity()
}

#[unsafe(no_mangle)]
pub extern "C" fn fx_init(sample_rate: f32) {
    // SAFETY: called once from the worklet constructor, before any processing.
    unsafe { *addr_of_mut!(FX) = Some(fx::Fx::new(sample_rate)) }
}

#[unsafe(no_mangle)]
pub extern "C" fn fx_in_ptr() -> *mut f32 {
    fx().in_buf.as_mut_ptr()
}

#[unsafe(no_mangle)]
pub extern "C" fn fx_out_l_ptr() -> *mut f32 {
    fx().out_l.as_mut_ptr()
}

#[unsafe(no_mangle)]
pub extern "C" fn fx_out_r_ptr() -> *mut f32 {
    fx().out_r.as_mut_ptr()
}

#[unsafe(no_mangle)]
pub extern "C" fn fx_process(n: u32) {
    fx().process(n as usize)
}

#[unsafe(no_mangle)]
pub extern "C" fn fx_set_param(id: u32, value: f32) {
    fx().set_param(id, value)
}

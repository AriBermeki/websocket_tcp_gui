use anyhow::Result;
use pyo3::prelude::*;

use crate::utils::FrameEventLoopBuilder;
mod api;
mod api_manager;
mod assets;
mod connections;
mod context;
mod core;
mod utils;

#[pyfunction]
fn create_webframe(html: String, host: String, port: u16, mp_event: Py<PyAny>) -> Result<()> {
    let addrs = format!("ws://{}:{}/ws", host, port);

    let json = serde_json::to_string(&addrs).unwrap();

    let websocket_init_add = format!("window.socket_url = {};", json);

    let mut event_loop = FrameEventLoopBuilder::with_user_event().build();

    let app = core::App::new(&mut event_loop, websocket_init_add, html)?;

    app.run(event_loop, mp_event)
}

/// A Python module implemented in Rust.
#[pymodule]
fn pygcc(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(create_webframe, m)?)?;
    Ok(())
}

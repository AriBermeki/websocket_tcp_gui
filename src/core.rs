use anyhow::Result;
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};

use crate::{
    api_manager::{ApiManager, ApiResponse},
    connections::start_server,
    context::AppContext,
    lock,
    utils::{FrameEventLoop, FrameEventLoopProxy, PendingMap, UserEvent},
};

#[allow(dead_code)]
pub struct App {
    api_manager: Arc<std::sync::Mutex<ApiManager>>,
    pub rt: std::sync::Arc<tokio::runtime::Runtime>,
    pub runtime_handel: std::sync::Arc<tokio::runtime::Handle>,
    pub proxy: FrameEventLoopProxy,
    response_map: PendingMap,
    pub ctx: Arc<AppContext>,
}

impl App {
    pub fn new(
        event_loop: &mut FrameEventLoop,
        init_add: String,
        html: String,
    ) -> Result<std::sync::Arc<App>> {
        let proxy = event_loop.create_proxy();

        let rt = std::sync::Arc::new(
            tokio::runtime::Builder::new_multi_thread()
                .enable_all()
                .build()?,
        );

        let window = tao::window::WindowBuilder::new()
            .with_title("PyFrame")
            .build(&event_loop)?;

        let webview = wry::WebViewBuilder::new()
            .with_initialization_script(init_add)
            .with_initialization_script(crate::assets::_CONN_SCRIPT)
            .with_initialization_script(crate::assets::_COMMAND_SCRIPT)
            .with_html(&html)
            .build(&window)?;

        let _ctx = AppContext::new(
            window.id(),
            Arc::new(Mutex::new(HashMap::from([(
                window.id(),
                (Arc::new(window), Arc::new(webview)),
            )]))),
        )?;

        let handle = rt.handle().clone();

        let cloned_proxy = proxy.clone();

        let api_manager = ApiManager::new();
        {
            let mut api_manager = lock!(api_manager)?;
            crate::api::register_api_instances(&mut api_manager);
        }

        let app = Arc::new(Self {
            api_manager: api_manager.clone(),
            rt: rt.clone(),
            runtime_handel: std::sync::Arc::new(handle),
            proxy,
            response_map: Arc::new(std::sync::Mutex::new(std::collections::HashMap::new())),
            ctx: _ctx.clone(),
        });

        // Richtige Bindung: kein neues Arc erzeugen
        {
            let mut m = lock!(api_manager).unwrap();
            m.bind_app_context(&_ctx);
        }
        let map = app.clone().response_map.clone();

        rt.spawn(start_server(cloned_proxy.clone(), map));

        Ok(app)
    }

    #[allow(dead_code)]
    pub fn api_manager(&self) -> Result<std::sync::MutexGuard<'_, ApiManager>> {
        lock!(self.api_manager)
    }

    #[allow(dead_code)]
    pub fn respond(&self, key: u8, response: ApiResponse) {
        if let Some(sender) = self.response_map.lock().unwrap().remove(&key) {
            let _ = sender.send(response);
        } else {
            eprintln!("Kein Sender für Schlüssel {} gefunden", key);
        }
    }

    pub fn run(
        self: Arc<Self>,
        event_loop: FrameEventLoop,
        _mp_event: pyo3::Py<pyo3::PyAny>,
    ) -> Result<()> {
        let api_manager = self.api_manager.clone();

        event_loop.run(move |event, target, control_flow| {
            *control_flow = tao::event_loop::ControlFlow::Wait;
            match event {
                tao::event::Event::WindowEvent { event, .. } => match event {
                    /*                     tao::event::WindowEvent::Destroyed => {
                        pyo3::Python::with_gil(|py| {
                            if let Err(e) = _mp_event.clone_ref(py).call_method0(py, "set") {
                                e.print(py);
                            }
                            py.check_signals().unwrap();
                        });
                        *control_flow = tao::event_loop::ControlFlow::Exit;
                    } */
                    tao::event::WindowEvent::CloseRequested => {
                        pyo3::Python::with_gil(|py| {
                            if let Err(e) = _mp_event.clone_ref(py).call_method0(py, "set") {
                                e.print(py);
                            }
                            py.check_signals().unwrap();
                        });
                        *control_flow = tao::event_loop::ControlFlow::Exit;
                    }
                    _ => {}
                },
                tao::event::Event::UserEvent(event) => match event {
                    UserEvent::Request(req) => {
                        let res = api_manager
                            .lock()
                            .unwrap()
                            .call(req, target, control_flow)
                            .unwrap();
                        self.respond(res.0, res);
                    }
                },
                _ => {}
            }
        });
    }
}

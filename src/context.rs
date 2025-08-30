use anyhow::{anyhow, Result};
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};
use tao::window::{Window, WindowId};

#[derive(Clone)]
pub struct AppContext {
    first_id: WindowId,
    pub window: Arc<Mutex<HashMap<WindowId, (Arc<Window>, Arc<wry::WebView>)>>>,
}

impl AppContext {
    pub fn new(
        first_id: WindowId,
        window: Arc<Mutex<HashMap<WindowId, (Arc<Window>, Arc<wry::WebView>)>>>,
    ) -> Result<Arc<Self>> {
        Ok(Arc::new(Self { first_id, window }))
    }
    #[allow(dead_code)]
    pub fn get_window(&self) -> Result<Arc<Window>> {
        let guard = self
            .window
            .lock()
            .map_err(|e| anyhow!("Mutex poison error: {}", e))?;
        guard
            .get(&self.first_id)
            .map(|(window, _)| Arc::clone(window))
            .ok_or_else(|| anyhow!("Window with id {:?} not found", self.first_id))
    }
    #[allow(dead_code)]
    pub fn get_webview(&self) -> Result<Arc<wry::WebView>> {
        let guard = self
            .window
            .lock()
            .map_err(|e| anyhow!("Mutex poison error: {}", e))?;
        guard
            .get(&self.first_id)
            .map(|(_, webview)| Arc::clone(webview))
            .ok_or_else(|| anyhow!("WebView with id {:?} not found", self.first_id))
    }
}

impl std::fmt::Debug for AppContext {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let window_guard = match self.window.lock() {
            Ok(guard) => guard,
            Err(_) => {
                return f
                    .debug_struct("AppContext")
                    .field("first_id", &self.first_id)
                    .field("error", &"Mutex is poisoned")
                    .finish();
            }
        };

        f.debug_struct("AppContext")
            .field("first_id", &self.first_id)
            .field("window_count", &window_guard.len())
            .field("window_ids", &window_guard.keys().collect::<Vec<_>>())
            .finish()
    }
}

use anyhow::Result;
use pyframe_macros::api;

use crate::api_manager::ApiManager;

#[api]
fn set_title(title: String) -> Result<bool> {
    let window = ctx.get_window()?;
    window.set_title(&title);
    Ok(true)
}

pub fn register_api_instances(api_manager: &mut ApiManager) {
    api_manager.register_api("set_title", set_title);
}

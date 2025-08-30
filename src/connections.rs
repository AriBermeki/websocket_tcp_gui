// use serde_json::Value;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;

use crate::utils::FrameEventLoopProxy;

/// Startet den Tokio TCP-Server
pub async fn start_server(
    proxy: FrameEventLoopProxy,
    pending: super::utils::PendingMap,
) -> tokio::io::Result<()> {
    let port = std::env::var("RUSTADDR").unwrap_or_else(|_| "9000".to_string());
    let addr = format!("127.0.0.1:{}", port);
    let listener = TcpListener::bind(&addr).await?;
    println!("[TCP] Listening on {}", addr);

    loop {
        let (socket, _) = listener.accept().await?;
        let proxy = proxy.clone();
        let pending = pending.clone();
        tokio::spawn(async move {
            if let Err(e) = handle_client(socket, proxy, pending).await {
                eprintln!("[TCP] Fehler: {:?}", e);
            }
        });
    }
}
pub async fn handle_client(
    socket: tokio::net::TcpStream,
    proxy: FrameEventLoopProxy,
    pending: super::utils::PendingMap,
) -> tokio::io::Result<()> {
    let socket = std::sync::Arc::new(tokio::sync::Mutex::new(socket));

    loop {
        // Länge lesen (4 Byte BE)
        let mut len_buf = [0u8; 4];
        if socket.lock().await.read_exact(&mut len_buf).await.is_err() {
            break;
        }
        let len = u32::from_be_bytes(len_buf) as usize;

        // Payload lesen
        let mut buf = vec![0u8; len];
        socket.lock().await.read_exact(&mut buf).await?;
        //let d:Value = serde_json::from_slice(&buf)?;
        let req: crate::api_manager::ApiRequest = match serde_json::from_slice(&buf) {
            Ok(r) => r,
            Err(e) => {
                eprintln!("[TCP] JSON-Fehler: {:?}", e);
                continue;
            }
        };

        // oneshot-Kanal für Antwort
        let (tx, rx) = tokio::sync::oneshot::channel();
        {
            let mut map = pending.lock().unwrap();
            map.insert(req.0.clone(), tx);
        }

        // Request in Eventloop pushen
        let _ = proxy.send_event(crate::utils::UserEvent::Request(req));

        // Antwort synchron abwarten
        match rx.await {
            Ok(resp) => {
                if let Ok(payload) = serde_json::to_vec(&resp) {
                    let mut msg = (payload.len() as u32).to_be_bytes().to_vec();
                    msg.extend_from_slice(&payload);
                    socket.lock().await.write_all(&msg).await?;
                }
            }
            Err(_) => eprintln!("[TCP] Antwort-Kanal abgebrochen"),
        }
    }

    Ok(())
}

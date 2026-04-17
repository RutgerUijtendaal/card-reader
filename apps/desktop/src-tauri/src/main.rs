use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use tauri::{Manager, State};

struct Sidecars {
    api: Mutex<Option<Child>>,
    worker: Mutex<Option<Child>>,
}

#[tauri::command]
fn backend_status() -> &'static str {
    "running"
}

fn spawn_sidecar(executable: &str) -> Option<Child> {
    Command::new(executable)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .ok()
}

fn main() {
    tauri::Builder::default()
        .manage(Sidecars {
            api: Mutex::new(None),
            worker: Mutex::new(None),
        })
        .setup(|app| {
            let state: State<Sidecars> = app.state();
            let mut api_lock = state.api.lock().expect("api lock poisoned");
            let mut worker_lock = state.worker.lock().expect("worker lock poisoned");

            // Placeholder names for bundled sidecar binaries.
            *api_lock = spawn_sidecar("card-reader-api");
            *worker_lock = spawn_sidecar("card-reader-worker");
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![backend_status])
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|_, event| {
            if let tauri::RunEvent::Exit = event {
                // Lifecycle cleanup is handled by OS process teardown in this scaffold.
            }
        });
}

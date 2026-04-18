#![cfg_attr(all(target_os = "windows", not(debug_assertions)), windows_subsystem = "windows")]

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use tauri::{Manager, State};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

struct Sidecars {
    api: Mutex<Option<Child>>,
    parser: Mutex<Option<Child>>,
}

#[tauri::command]
fn backend_status() -> &'static str {
    "running"
}

fn spawn_sidecar(executable: &str, app_data_dir: Option<&str>) -> Option<Child> {
    let mut command = Command::new(executable);
    let runtime_env = if cfg!(debug_assertions) {
        "development"
    } else {
        "production"
    };
    command
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .env("CARD_READER_ENV", runtime_env);

    if !cfg!(debug_assertions) {
        if let Some(path) = app_data_dir {
            command.env("CARD_READER_APP_DATA_DIR", path);
        }
    }

    #[cfg(target_os = "windows")]
    {
        command.creation_flags(CREATE_NO_WINDOW);
    }

    command.spawn().ok()
}

fn main() {
    tauri::Builder::default()
        .manage(Sidecars {
            api: Mutex::new(None),
            parser: Mutex::new(None),
        })
        .setup(|app| {
            let state: State<Sidecars> = app.state();
            let mut api_lock = state.api.lock().expect("api lock poisoned");
            let mut parser_lock = state.parser.lock().expect("parser lock poisoned");
            let app_data_dir = app
                .path()
                .app_data_dir()
                .ok()
                .map(|path| path.to_string_lossy().into_owned());

            // Placeholder names for bundled sidecar binaries.
            *api_lock = spawn_sidecar("card-reader-api", app_data_dir.as_deref());
            *parser_lock = spawn_sidecar("card-reader-parser", app_data_dir.as_deref());
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

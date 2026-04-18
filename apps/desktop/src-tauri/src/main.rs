#![cfg_attr(all(target_os = "windows", not(debug_assertions)), windows_subsystem = "windows")]

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::path::PathBuf;
use std::fs::{self, OpenOptions};
use std::io::Write;

use tauri::{AppHandle, Manager, State};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;
const DESKTOP_API_PORT: &str = "18600";

struct Sidecars {
    api: Mutex<Option<Child>>,
    parser: Mutex<Option<Child>>,
}

#[tauri::command]
fn backend_status() -> &'static str {
    "running"
}

fn resolve_sidecar_path(app: &AppHandle, executable: &str) -> PathBuf {
    if cfg!(debug_assertions) {
        return PathBuf::from(executable);
    }

    let resource_dir = match app.path().resource_dir() {
        Ok(path) => path,
        Err(_) => return PathBuf::from(executable),
    };

    #[cfg(target_os = "windows")]
    let file_name = format!("{executable}.exe");

    #[cfg(not(target_os = "windows"))]
    let file_name = executable.to_string();

    let preferred = resource_dir.join("binaries").join(&file_name);
    if preferred.exists() {
        return preferred;
    }

    let fallback = resource_dir.join(&file_name);
    if fallback.exists() {
        return fallback;
    }

    preferred
}

fn append_desktop_log(app_data_dir: Option<&str>, message: &str) {
    let logs_root = app_data_dir
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."))
        .join("logs");
    if fs::create_dir_all(&logs_root).is_err() {
        return;
    }
    let log_path = logs_root.join("desktop.log");
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_path) {
        let _ = writeln!(file, "{message}");
    }
}

fn sidecar_stdio_file(app_data_dir: Option<&str>, executable: &str) -> Option<std::fs::File> {
    let logs_root = app_data_dir
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."))
        .join("logs");
    if fs::create_dir_all(&logs_root).is_err() {
        return None;
    }
    OpenOptions::new()
        .create(true)
        .append(true)
        .open(logs_root.join(format!("{executable}.log")))
        .ok()
}

fn spawn_sidecar(app: &AppHandle, executable: &str, app_data_dir: Option<&str>) -> Option<Child> {
    let executable_path = resolve_sidecar_path(app, executable);
    append_desktop_log(
        app_data_dir,
        &format!(
            "Launching sidecar executable={} path={} exists={}",
            executable,
            executable_path.display(),
            executable_path.exists()
        ),
    );

    let mut command = Command::new(executable_path);
    let runtime_env = if cfg!(debug_assertions) {
        "development"
    } else {
        "production"
    };
    if let Some(stdout_log) = sidecar_stdio_file(app_data_dir, executable) {
        if let Ok(stderr_log) = stdout_log.try_clone() {
            command.stdout(Stdio::from(stdout_log)).stderr(Stdio::from(stderr_log));
        } else {
            command.stdout(Stdio::from(stdout_log)).stderr(Stdio::null());
        }
    } else {
        command.stdout(Stdio::null()).stderr(Stdio::null());
    }
    command
        .env("CARD_READER_ENV", runtime_env)
        .env("CARD_READER_API_PORT", DESKTOP_API_PORT);

    if !cfg!(debug_assertions) {
        if let Some(path) = app_data_dir {
            command.env("CARD_READER_APP_DATA_DIR", path);
        }
    }

    #[cfg(target_os = "windows")]
    {
        command.creation_flags(CREATE_NO_WINDOW);
    }

    match command.spawn() {
        Ok(child) => {
            append_desktop_log(
                app_data_dir,
                &format!("Sidecar started executable={} pid={}", executable, child.id()),
            );
            Some(child)
        }
        Err(error) => {
            append_desktop_log(
                app_data_dir,
                &format!("Sidecar failed executable={} error={}", executable, error),
            );
            None
        }
    }
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
            let app_handle = app.handle().clone();
            let app_data_dir = app
                .path()
                .app_data_dir()
                .ok()
                .map(|path| path.to_string_lossy().into_owned());
            if let Some(path) = app_data_dir.as_deref() {
                let _ = fs::create_dir_all(path);
                append_desktop_log(Some(path), "Desktop startup: app_data_dir initialized");
            }

            *api_lock = spawn_sidecar(&app_handle, "card-reader-api", app_data_dir.as_deref());
            *parser_lock = spawn_sidecar(&app_handle, "card-reader-parser", app_data_dir.as_deref());
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

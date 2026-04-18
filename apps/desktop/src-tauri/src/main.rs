#![cfg_attr(all(target_os = "windows", not(debug_assertions)), windows_subsystem = "windows")]

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::path::PathBuf;
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::env;
use std::net::TcpStream;
use std::thread;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager, Runtime, State};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;
const DESKTOP_API_PORT: &str = "18600";
const PARSER_GRACEFUL_SHUTDOWN_TIMEOUT_SECS: u64 = 5;

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

fn parser_shutdown_marker_path(app_data_dir: Option<&str>) -> Option<PathBuf> {
    app_data_dir.map(|root| PathBuf::from(root).join("shutdown").join("parser.stop"))
}

fn clear_parser_shutdown_marker(app_data_dir: Option<&str>) {
    let Some(path) = parser_shutdown_marker_path(app_data_dir) else {
        return;
    };
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    if path.exists() {
        let _ = fs::remove_file(path);
    }
}

fn signal_parser_shutdown(app_data_dir: Option<&str>) {
    let Some(path) = parser_shutdown_marker_path(app_data_dir) else {
        return;
    };
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let _ = OpenOptions::new().create(true).truncate(true).write(true).open(&path);
    append_desktop_log(
        app_data_dir,
        &format!("Parser shutdown marker created path={}", path.display()),
    );
}

fn resolve_runtime_app_data_dir<R: Runtime, M: Manager<R>>(app: &M) -> Option<PathBuf> {
    #[cfg(target_os = "windows")]
    {
        if let Ok(local_app_data) = env::var("LOCALAPPDATA") {
            return Some(PathBuf::from(local_app_data).join("Card Reader"));
        }
        if let Ok(app_data) = env::var("APPDATA") {
            return Some(PathBuf::from(app_data).join("Card Reader"));
        }
    }

    app.path().app_data_dir().ok()
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
    if executable == "card-reader-parser" {
        if let Some(path) = parser_shutdown_marker_path(app_data_dir) {
            command.env("CARD_READER_SHUTDOWN_FILE", path.to_string_lossy().to_string());
        }
        command.env("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True");
    }

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

fn api_healthcheck() -> bool {
    let address = format!("127.0.0.1:{DESKTOP_API_PORT}");
    let mut stream = match TcpStream::connect(address) {
        Ok(stream) => stream,
        Err(_) => return false,
    };

    let _ = stream.set_read_timeout(Some(Duration::from_millis(400)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(400)));

    let request = b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
    if stream.write_all(request).is_err() {
        return false;
    }

    let mut response = String::new();
    if stream.read_to_string(&mut response).is_err() {
        return false;
    }

    response.starts_with("HTTP/1.1 200") || response.starts_with("HTTP/1.0 200")
}

fn wait_for_api_ready(app_data_dir: Option<&str>, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    loop {
        if api_healthcheck() {
            append_desktop_log(app_data_dir, "API healthcheck succeeded");
            return true;
        }
        if Instant::now() >= deadline {
            append_desktop_log(app_data_dir, "API healthcheck timed out");
            return false;
        }
        thread::sleep(Duration::from_millis(250));
    }
}

fn stop_sidecar(
    lock: &Mutex<Option<Child>>,
    executable: &str,
    app_data_dir: Option<&str>,
    graceful: bool,
) {
    let mut child_opt = lock.lock().expect("sidecar lock poisoned");
    let Some(mut child) = child_opt.take() else {
        return;
    };

    let pid = child.id();
    if graceful {
        if executable == "card-reader-parser" {
            signal_parser_shutdown(app_data_dir);
        }
        let deadline = Instant::now() + Duration::from_secs(PARSER_GRACEFUL_SHUTDOWN_TIMEOUT_SECS);
        loop {
            match child.try_wait() {
                Ok(Some(status)) => {
                    append_desktop_log(
                        app_data_dir,
                        &format!(
                            "Sidecar exited gracefully executable={} pid={} status={}",
                            executable, pid, status
                        ),
                    );
                    if executable == "card-reader-parser" {
                        clear_parser_shutdown_marker(app_data_dir);
                    }
                    return;
                }
                Ok(None) => {
                    if Instant::now() >= deadline {
                        append_desktop_log(
                            app_data_dir,
                            &format!("Graceful shutdown timeout executable={} pid={}", executable, pid),
                        );
                        break;
                    }
                    thread::sleep(Duration::from_millis(250));
                }
                Err(error) => {
                    append_desktop_log(
                        app_data_dir,
                        &format!("Graceful wait error executable={} pid={} error={}", executable, pid, error),
                    );
                    break;
                }
            }
        }
    }

    #[cfg(target_os = "windows")]
    {
        let taskkill_result = Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
        match taskkill_result {
            Ok(status) if status.success() => {
                append_desktop_log(
                    app_data_dir,
                    &format!("Sidecar tree stopped executable={} pid={} via taskkill", executable, pid),
                );
            }
            Ok(status) => {
                append_desktop_log(
                    app_data_dir,
                    &format!(
                        "taskkill failed executable={} pid={} status={}",
                        executable, pid, status
                    ),
                );
            }
            Err(error) => {
                append_desktop_log(
                    app_data_dir,
                    &format!("taskkill error executable={} pid={} error={}", executable, pid, error),
                );
            }
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        if let Err(error) = child.kill() {
            append_desktop_log(
                app_data_dir,
                &format!("Sidecar stop failed executable={} pid={} error={}", executable, pid, error),
            );
            return;
        }
    }
    let _ = child.wait();
    if executable == "card-reader-parser" {
        clear_parser_shutdown_marker(app_data_dir);
    }
    append_desktop_log(
        app_data_dir,
        &format!("Sidecar stopped executable={} pid={}", executable, pid),
    );
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .manage(Sidecars {
            api: Mutex::new(None),
            parser: Mutex::new(None),
        })
        .setup(|app| {
            let state: State<Sidecars> = app.state();
            let mut api_lock = state.api.lock().expect("api lock poisoned");
            let mut parser_lock = state.parser.lock().expect("parser lock poisoned");
            let app_handle = app.handle().clone();
            let app_data_dir = resolve_runtime_app_data_dir(app)
                .map(|path| path.to_string_lossy().into_owned());
            if let Some(path) = app_data_dir.as_deref() {
                let _ = fs::create_dir_all(path);
                append_desktop_log(Some(path), &format!("Desktop startup: app_data_dir initialized path={path}"));
            }
            clear_parser_shutdown_marker(app_data_dir.as_deref());

            *api_lock = spawn_sidecar(&app_handle, "card-reader-api", app_data_dir.as_deref());
            if api_lock.is_none() {
                return Err("failed to start card-reader-api sidecar".into());
            }
            drop(api_lock);

            if !wait_for_api_ready(app_data_dir.as_deref(), Duration::from_secs(20)) {
                let state: State<Sidecars> = app.state();
                stop_sidecar(&state.parser, "card-reader-parser", app_data_dir.as_deref(), true);
                stop_sidecar(&state.api, "card-reader-api", app_data_dir.as_deref(), false);
                return Err("card-reader-api did not become healthy in time".into());
            }

            *parser_lock = spawn_sidecar(&app_handle, "card-reader-parser", app_data_dir.as_deref());
            if parser_lock.is_none() {
                if let Some(mut api_child) = state.api.lock().expect("api lock poisoned").take() {
                    let _ = api_child.kill();
                    let _ = api_child.wait();
                }
                return Err("failed to start card-reader-parser sidecar".into());
            }
            drop(parser_lock);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![backend_status])
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|app_handle, event| {
            if matches!(
                event,
                tauri::RunEvent::ExitRequested { .. }
                    | tauri::RunEvent::Exit
                    | tauri::RunEvent::WindowEvent {
                        event: tauri::WindowEvent::CloseRequested { .. },
                        ..
                    }
            ) {
                let app_data_dir = resolve_runtime_app_data_dir(app_handle)
                    .map(|path| path.to_string_lossy().into_owned());
                let state: State<Sidecars> = app_handle.state();
                stop_sidecar(&state.parser, "card-reader-parser", app_data_dir.as_deref(), true);
                stop_sidecar(&state.api, "card-reader-api", app_data_dir.as_deref(), false);
            }
        });
}

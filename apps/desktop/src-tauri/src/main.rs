#![cfg_attr(
    all(target_os = "windows", not(debug_assertions)),
    windows_subsystem = "windows"
)]

use std::env;
use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager, Runtime, State};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;
const DESKTOP_API_PORT: &str = "18600";
const PARSER_GRACEFUL_SHUTDOWN_TIMEOUT_SECS: u64 = 5;
const API_MODULE: &str = "card_reader_api.desktop_main";
const PARSER_MODULE: &str = "card_reader_parser.main";

struct ServiceProcesses {
    api: Mutex<Option<Child>>,
    parser: Mutex<Option<Child>>,
}

struct PythonServiceLayout {
    executable: PathBuf,
    python_home: Option<PathBuf>,
    python_path: Option<PathBuf>,
    working_dir: PathBuf,
}

#[tauri::command]
fn backend_status() -> &'static str {
    "running"
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
    let _ = OpenOptions::new()
        .create(true)
        .truncate(true)
        .write(true)
        .open(&path);
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

fn sidecar_stdio_file(app_data_dir: Option<&str>, service_name: &str) -> Option<std::fs::File> {
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
        .open(logs_root.join(format!("{service_name}.log")))
        .ok()
}

fn repo_root() -> PathBuf {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("..");
    root.canonicalize().unwrap_or(root)
}

#[cfg(target_os = "windows")]
fn normalize_process_path(path: &Path) -> PathBuf {
    let raw = path.to_string_lossy();
    if let Some(stripped) = raw.strip_prefix(r"\\?\UNC\") {
        return PathBuf::from(format!(r"\\{stripped}"));
    }
    if let Some(stripped) = raw.strip_prefix(r"\\?\") {
        return PathBuf::from(stripped);
    }
    path.to_path_buf()
}

#[cfg(not(target_os = "windows"))]
fn normalize_process_path(path: &Path) -> PathBuf {
    path.to_path_buf()
}

fn derive_python_home(python_executable: &Path) -> Option<PathBuf> {
    let parent = python_executable.parent()?;
    if parent.file_name().and_then(|name| name.to_str()) == Some("bin") {
        return parent.parent().map(Path::to_path_buf);
    }
    Some(parent.to_path_buf())
}

fn find_python_executable(root: &Path) -> Option<PathBuf> {
    let mut stack = vec![root.to_path_buf()];
    let candidates: &[&str] = if cfg!(target_os = "windows") {
        &["python.exe"]
    } else {
        &["python3.12", "python3", "python"]
    };

    while let Some(current_dir) = stack.pop() {
        let entries = match fs::read_dir(&current_dir) {
            Ok(entries) => entries,
            Err(_) => continue,
        };
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                stack.push(path);
                continue;
            }
            let Some(file_name) = path.file_name().and_then(|name| name.to_str()) else {
                continue;
            };
            if candidates.contains(&file_name) {
                return Some(path);
            }
        }
    }

    None
}

fn resolve_python_layout<R: Runtime, M: Manager<R>>(
    app: &M,
    app_data_dir: Option<&str>,
) -> Result<PythonServiceLayout, String> {
    if cfg!(debug_assertions) {
        let root = repo_root();
        let executable = if cfg!(target_os = "windows") {
            root.join(".venv").join("Scripts").join("python.exe")
        } else {
            root.join(".venv").join("bin").join("python3")
        };
        append_desktop_log(
            app_data_dir,
            &format!(
                "Resolved development Python executable path={} exists={}",
                executable.display(),
                executable.exists()
            ),
        );
        return Ok(PythonServiceLayout {
            executable: normalize_process_path(&executable),
            python_home: None,
            python_path: None,
            working_dir: root,
        });
    }

    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|error| format!("failed to resolve Tauri resource dir: {error}"))?;
    let python_root = resource_dir.join("python");
    let runtime_root = python_root.join("runtime");
    let site_packages = python_root.join("site-packages");
    let executable = find_python_executable(&runtime_root).ok_or_else(|| {
        format!(
            "failed to locate bundled Python executable under {}",
            runtime_root.display()
        )
    })?;

    append_desktop_log(
        app_data_dir,
        &format!(
            "Resolved bundled Python executable path={} site_packages={} exists={}",
            executable.display(),
            site_packages.display(),
            site_packages.exists()
        ),
    );

    let executable = normalize_process_path(&executable);
    let python_home = derive_python_home(&executable).map(|path| normalize_process_path(&path));
    let python_path = Some(normalize_process_path(&site_packages));
    let working_dir = normalize_process_path(
        &app_data_dir
            .map(PathBuf::from)
            .unwrap_or_else(|| resource_dir.clone()),
    );

    Ok(PythonServiceLayout {
        python_home,
        executable,
        python_path,
        working_dir,
    })
}

fn spawn_python_service(
    app: &AppHandle,
    service_name: &str,
    module_name: &str,
    app_data_dir: Option<&str>,
) -> Option<Child> {
    let layout = match resolve_python_layout(app, app_data_dir) {
        Ok(layout) => layout,
        Err(error) => {
            append_desktop_log(
                app_data_dir,
                &format!(
                    "Python runtime resolution failed service={} error={error}",
                    service_name
                ),
            );
            return None;
        }
    };

    append_desktop_log(
        app_data_dir,
        &format!(
            "Launching Python service service={} python={} module={} cwd={}",
            service_name,
            layout.executable.display(),
            module_name,
            layout.working_dir.display()
        ),
    );

    let mut command = Command::new(&layout.executable);
    command.arg("-m").arg(module_name);
    command.current_dir(&layout.working_dir);
    command.env_remove("PYTHONHOME");
    command.env_remove("PYTHONPATH");

    if let Some(python_home) = layout.python_home.as_ref() {
        command.env("PYTHONHOME", python_home);
    }
    if let Some(python_path) = layout.python_path.as_ref() {
        command.env("PYTHONPATH", python_path);
    }

    if let Some(stdout_log) = sidecar_stdio_file(app_data_dir, service_name) {
        if let Ok(stderr_log) = stdout_log.try_clone() {
            command
                .stdout(Stdio::from(stdout_log))
                .stderr(Stdio::from(stderr_log));
        } else {
            command
                .stdout(Stdio::from(stdout_log))
                .stderr(Stdio::null());
        }
    } else {
        command.stdout(Stdio::null()).stderr(Stdio::null());
    }

    let runtime_env = if cfg!(debug_assertions) {
        "development"
    } else {
        "production"
    };
    command
        .env("PYTHONUNBUFFERED", "1")
        .env("CARD_READER_ENV", runtime_env)
        .env("CARD_READER_API_PORT", DESKTOP_API_PORT);

    if service_name == "card-reader-api" {
        command.env("CARD_READER_AUTH_ENABLED", "false");
    }
    if service_name == "card-reader-parser" {
        if let Some(path) = parser_shutdown_marker_path(app_data_dir) {
            command.env(
                "CARD_READER_SHUTDOWN_FILE",
                path.to_string_lossy().to_string(),
            );
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
                &format!(
                    "Python service started service={} pid={}",
                    service_name,
                    child.id()
                ),
            );
            Some(child)
        }
        Err(error) => {
            append_desktop_log(
                app_data_dir,
                &format!(
                    "Python service failed service={} error={}",
                    service_name, error
                ),
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
        thread::sleep(Duration::from_millis(250));
        if Instant::now() >= deadline {
            append_desktop_log(app_data_dir, "API healthcheck timed out");
            return false;
        }
    }
}

fn stop_service(
    lock: &Mutex<Option<Child>>,
    service_name: &str,
    app_data_dir: Option<&str>,
    graceful: bool,
) {
    let mut child_opt = lock.lock().expect("service lock poisoned");
    let Some(mut child) = child_opt.take() else {
        return;
    };

    let pid = child.id();
    if graceful {
        if service_name == "card-reader-parser" {
            signal_parser_shutdown(app_data_dir);
        }
        let deadline = Instant::now() + Duration::from_secs(PARSER_GRACEFUL_SHUTDOWN_TIMEOUT_SECS);
        loop {
            match child.try_wait() {
                Ok(Some(status)) => {
                    append_desktop_log(
                        app_data_dir,
                        &format!(
                            "Service exited gracefully service={} pid={} status={}",
                            service_name, pid, status
                        ),
                    );
                    if service_name == "card-reader-parser" {
                        clear_parser_shutdown_marker(app_data_dir);
                    }
                    return;
                }
                Ok(None) => {
                    if Instant::now() >= deadline {
                        append_desktop_log(
                            app_data_dir,
                            &format!(
                                "Graceful shutdown timeout service={} pid={}",
                                service_name, pid
                            ),
                        );
                        break;
                    }
                    thread::sleep(Duration::from_millis(250));
                }
                Err(error) => {
                    append_desktop_log(
                        app_data_dir,
                        &format!(
                            "Graceful wait error service={} pid={} error={}",
                            service_name, pid, error
                        ),
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
                    &format!(
                        "Service tree stopped service={} pid={} via taskkill",
                        service_name, pid
                    ),
                );
            }
            Ok(status) => {
                append_desktop_log(
                    app_data_dir,
                    &format!(
                        "taskkill failed service={} pid={} status={}",
                        service_name, pid, status
                    ),
                );
            }
            Err(error) => {
                append_desktop_log(
                    app_data_dir,
                    &format!(
                        "taskkill error service={} pid={} error={}",
                        service_name, pid, error
                    ),
                );
            }
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        if let Err(error) = child.kill() {
            append_desktop_log(
                app_data_dir,
                &format!(
                    "Service stop failed service={} pid={} error={}",
                    service_name, pid, error
                ),
            );
            return;
        }
    }
    let _ = child.wait();
    if service_name == "card-reader-parser" {
        clear_parser_shutdown_marker(app_data_dir);
    }
    append_desktop_log(
        app_data_dir,
        &format!("Service stopped service={} pid={}", service_name, pid),
    );
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .manage(ServiceProcesses {
            api: Mutex::new(None),
            parser: Mutex::new(None),
        })
        .setup(|app| {
            let state: State<ServiceProcesses> = app.state();
            let mut api_lock = state.api.lock().expect("api lock poisoned");
            let mut parser_lock = state.parser.lock().expect("parser lock poisoned");
            let app_handle = app.handle().clone();
            let app_data_dir =
                resolve_runtime_app_data_dir(app).map(|path| path.to_string_lossy().into_owned());
            if let Some(path) = app_data_dir.as_deref() {
                let _ = fs::create_dir_all(path);
                append_desktop_log(
                    Some(path),
                    &format!("Desktop startup: app_data_dir initialized path={path}"),
                );
            }
            clear_parser_shutdown_marker(app_data_dir.as_deref());

            *api_lock = spawn_python_service(
                &app_handle,
                "card-reader-api",
                API_MODULE,
                app_data_dir.as_deref(),
            );
            if api_lock.is_none() {
                return Err("failed to start card-reader-api service".into());
            }
            drop(api_lock);

            let api_ready = wait_for_api_ready(app_data_dir.as_deref(), Duration::from_secs(20));
            let api_exited = state
                .api
                .lock()
                .expect("api lock poisoned")
                .as_mut()
                .and_then(|child| child.try_wait().ok().flatten());
            if let Some(status) = api_exited {
                append_desktop_log(
                    app_data_dir.as_deref(),
                    &format!("API service exited before healthcheck status={status}"),
                );
            }

            if !api_ready {
                let state: State<ServiceProcesses> = app.state();
                stop_service(
                    &state.parser,
                    "card-reader-parser",
                    app_data_dir.as_deref(),
                    true,
                );
                stop_service(
                    &state.api,
                    "card-reader-api",
                    app_data_dir.as_deref(),
                    false,
                );
                return Err("card-reader-api did not become healthy in time".into());
            }

            *parser_lock = spawn_python_service(
                &app_handle,
                "card-reader-parser",
                PARSER_MODULE,
                app_data_dir.as_deref(),
            );
            if parser_lock.is_none() {
                if let Some(mut api_child) = state.api.lock().expect("api lock poisoned").take() {
                    let _ = api_child.kill();
                    let _ = api_child.wait();
                }
                return Err("failed to start card-reader-parser service".into());
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
                let state: State<ServiceProcesses> = app_handle.state();
                stop_service(
                    &state.parser,
                    "card-reader-parser",
                    app_data_dir.as_deref(),
                    true,
                );
                stop_service(
                    &state.api,
                    "card-reader-api",
                    app_data_dir.as_deref(),
                    false,
                );
            }
        });
}

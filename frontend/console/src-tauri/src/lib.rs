use std::io::{Read, Write};
use std::net::ToSocketAddrs;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread::sleep;
use std::time::{Duration, Instant};

use serde::Serialize;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, Emitter, Manager, State};
use tauri_plugin_deep_link::DeepLinkExt;

const API_HOST: &str = "127.0.0.1";
const API_PORT: &str = "8787";
const DESKTOP_NAVIGATE_EVENT: &str = "desktop:navigate";
const DESKTOP_NOTIFICATIONS_POLICY_EVENT: &str = "desktop:notifications-policy";
const DESKTOP_OPEN_URL_EVENT: &str = "desktop:open-url";
const DEEP_LINK_SCHEME: &str = "agent-hive:";

type SharedRuntime = Arc<Mutex<DesktopRuntime>>;

#[derive(Default)]
struct ManagedBackend {
    child: Option<Child>,
    managed: bool,
}

#[derive(Default)]
struct DesktopRuntime {
    backend: ManagedBackend,
    notifications_paused: bool,
    pending_urls: Vec<String>,
    quitting: bool,
}

struct BackendCommand {
    label: &'static str,
    program: &'static str,
    args: Vec<&'static str>,
    current_dir: Option<PathBuf>,
}

#[derive(Clone, Serialize)]
struct DesktopBootstrapPayload {
    notifications_paused: bool,
    pending_urls: Vec<String>,
}

#[derive(Clone, Serialize)]
struct DesktopNavigationPayload {
    href: String,
}

#[derive(Clone, Serialize)]
struct DesktopNotificationsPolicyPayload {
    paused: bool,
}

#[derive(Clone, Serialize)]
struct DesktopOpenUrlPayload {
    urls: Vec<String>,
}

fn repo_root() -> Option<PathBuf> {
    let candidate = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..");
    let resolved = candidate.canonicalize().ok()?;
    let has_hive =
        resolved.join("pyproject.toml").exists() && resolved.join("src/hive/console/api.py").exists();
    if has_hive {
        Some(resolved)
    } else {
        None
    }
}

fn backend_commands() -> Vec<BackendCommand> {
    let mut commands = Vec::new();
    if let Some(root) = repo_root() {
        commands.push(BackendCommand {
            label: "repo-local uv run hive console api",
            program: "uv",
            args: vec![
                "run",
                "hive",
                "console",
                "api",
                "--host",
                API_HOST,
                "--port",
                API_PORT,
            ],
            current_dir: Some(root),
        });
    }
    commands.push(BackendCommand {
        label: "system hive console api",
        program: "hive",
        args: vec!["console", "api", "--host", API_HOST, "--port", API_PORT],
        current_dir: None,
    });
    commands
}

fn console_api_healthy() -> bool {
    let Ok(mut addresses) = format!("{API_HOST}:{API_PORT}").to_socket_addrs() else {
        return false;
    };
    let Some(address) = addresses.next() else {
        return false;
    };
    let Ok(mut stream) = std::net::TcpStream::connect_timeout(&address, Duration::from_millis(250))
    else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(250)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(250)));
    let request =
        format!("GET /health HTTP/1.1\r\nHost: {API_HOST}:{API_PORT}\r\nConnection: close\r\n\r\n");
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }
    let mut response = String::new();
    if stream.read_to_string(&mut response).is_err() {
        return false;
    }
    response.starts_with("HTTP/1.1 200") || response.starts_with("HTTP/1.0 200")
}

fn wait_for_backend(child: &mut Child, timeout: Duration) -> Result<(), String> {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if console_api_healthy() {
            return Ok(());
        }
        match child.try_wait() {
            Ok(Some(status)) => return Err(format!("exited early with status {status}")),
            Ok(None) => sleep(Duration::from_millis(125)),
            Err(error) => return Err(format!("could not inspect child status: {error}")),
        }
    }
    if console_api_healthy() {
        return Ok(());
    }
    Err("timed out waiting for /health".to_string())
}

fn spawn_backend() -> Result<ManagedBackend, String> {
    if console_api_healthy() {
        return Ok(ManagedBackend {
            child: None,
            managed: false,
        });
    }

    let mut errors = Vec::new();
    for candidate in backend_commands() {
        let mut command = Command::new(candidate.program);
        command.args(&candidate.args);
        if let Some(current_dir) = candidate.current_dir {
            command.current_dir(current_dir);
        }
        command.stdout(Stdio::null()).stderr(Stdio::null());
        match command.spawn() {
            Ok(mut child) => match wait_for_backend(&mut child, Duration::from_secs(6)) {
                Ok(()) => {
                    return Ok(ManagedBackend {
                        child: Some(child),
                        managed: true,
                    })
                }
                Err(error) => {
                    let _ = child.kill();
                    let _ = child.wait();
                    errors.push(format!("{}: {}", candidate.label, error));
                }
            },
            Err(error) => errors.push(format!("{}: {}", candidate.label, error)),
        }
    }

    Err(errors.join(" | "))
}

fn stop_backend(runtime: &SharedRuntime) {
    let managed_child = {
        let mut runtime = runtime.lock().expect("desktop runtime lock poisoned");
        runtime.quitting = true;
        if !runtime.backend.managed {
            return;
        }
        runtime.backend.child.take()
    };

    if let Some(mut child) = managed_child {
        let _ = child.kill();
        let _ = child.wait();
    }
}

fn remember_urls(runtime: &SharedRuntime, urls: &[String]) {
    let mut desktop_runtime = runtime.lock().expect("desktop runtime lock poisoned");
    for url in urls {
        if !desktop_runtime.pending_urls.contains(url) {
            desktop_runtime.pending_urls.push(url.clone());
        }
    }
}

fn show_main_window(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn emit_navigation(app: &AppHandle, href: &str) {
    show_main_window(app);
    let _ = app.emit(
        DESKTOP_NAVIGATE_EVENT,
        DesktopNavigationPayload {
            href: href.to_string(),
        },
    );
}

fn emit_notifications_policy(app: &AppHandle, paused: bool) {
    let _ = app.emit(
        DESKTOP_NOTIFICATIONS_POLICY_EVENT,
        DesktopNotificationsPolicyPayload { paused },
    );
}

fn emit_open_urls(app: &AppHandle, runtime: &SharedRuntime, urls: Vec<String>) {
    if urls.is_empty() {
        return;
    }
    remember_urls(runtime, &urls);
    show_main_window(app);
    let _ = app.emit(DESKTOP_OPEN_URL_EVENT, DesktopOpenUrlPayload { urls });
}

fn deep_link_args(args: &[String]) -> Vec<String> {
    args.iter()
        .filter(|arg| {
            arg.starts_with(DEEP_LINK_SCHEME)
                || arg.starts_with("http://")
                || arg.starts_with("https://")
        })
        .cloned()
        .collect()
}

fn install_tray(app: &AppHandle, runtime: SharedRuntime) -> tauri::Result<()> {
    let open_i = MenuItem::with_id(app, "open", "Open Command Center", true, None::<&str>)?;
    let open_notifications_i =
        MenuItem::with_id(app, "open-notifications", "Open Notifications", true, None::<&str>)?;
    let pause_notifications_i = MenuItem::with_id(
        app,
        "pause-notifications",
        "Pause desktop notifications",
        true,
        None::<&str>,
    )?;
    let resume_notifications_i = MenuItem::with_id(
        app,
        "resume-notifications",
        "Resume desktop notifications",
        true,
        None::<&str>,
    )?;
    let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
    let menu = Menu::with_items(
        app,
        &[
            &open_i,
            &open_notifications_i,
            &pause_notifications_i,
            &resume_notifications_i,
            &quit_i,
        ],
    )?;

    TrayIconBuilder::new()
        .menu(&menu)
        .show_menu_on_left_click(true)
        .icon(app.default_window_icon().expect("missing default window icon").clone())
        .on_menu_event(move |app, event| match event.id.as_ref() {
            "open" => emit_navigation(app, "/home"),
            "open-notifications" => emit_navigation(app, "/notifications"),
            "pause-notifications" => {
                runtime
                    .lock()
                    .expect("desktop runtime lock poisoned")
                    .notifications_paused = true;
                emit_notifications_policy(app, true);
            }
            "resume-notifications" => {
                runtime
                    .lock()
                    .expect("desktop runtime lock poisoned")
                    .notifications_paused = false;
                emit_notifications_policy(app, false);
            }
            "quit" => {
                runtime.lock().expect("desktop runtime lock poisoned").quitting = true;
                app.exit(0);
            }
            _ => {}
        })
        .build(app)?;

    Ok(())
}

fn configure_deep_links(app: &AppHandle, runtime: SharedRuntime) -> tauri::Result<()> {
    let current_urls = app
        .deep_link()
        .get_current()
        .ok()
        .into_iter()
        .flatten()
        .flatten()
        .map(|url| url.to_string())
        .collect::<Vec<_>>();
    remember_urls(&runtime, &current_urls);

    let app_handle = app.clone();
    let runtime_for_events = Arc::clone(&runtime);
    app.deep_link().on_open_url(move |event| {
        let urls = event
            .urls()
            .iter()
            .map(|url| url.to_string())
            .collect::<Vec<_>>();
        emit_open_urls(&app_handle, &runtime_for_events, urls);
    });

    Ok(())
}

#[tauri::command]
fn desktop_bootstrap(state: State<'_, SharedRuntime>) -> DesktopBootstrapPayload {
    let mut runtime = state.lock().expect("desktop runtime lock poisoned");
    DesktopBootstrapPayload {
        notifications_paused: runtime.notifications_paused,
        pending_urls: runtime.pending_urls.drain(..).collect(),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let runtime = Arc::new(Mutex::new(DesktopRuntime::default()));
    let runtime_for_single_instance = Arc::clone(&runtime);
    let runtime_for_setup = Arc::clone(&runtime);
    let runtime_for_exit = Arc::clone(&runtime);

    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(move |app, args, _cwd| {
            let urls = deep_link_args(&args);
            if urls.is_empty() {
                show_main_window(app);
            } else {
                emit_open_urls(app, &runtime_for_single_instance, urls);
            }
        }))
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_notification::init())
        .manage(Arc::clone(&runtime))
        .invoke_handler(tauri::generate_handler![desktop_bootstrap])
        .setup(move |app| {
            let backend = match spawn_backend() {
                Ok(backend) => backend,
                Err(error) => {
                    eprintln!(
                        "Agent Hive desktop beta could not auto-start the console API on http://{}:{} ({})",
                        API_HOST, API_PORT, error
                    );
                    ManagedBackend::default()
                }
            };
            runtime_for_setup
                .lock()
                .expect("desktop runtime lock poisoned")
                .backend = backend;

            configure_deep_links(app.handle(), Arc::clone(&runtime_for_setup))?;
            install_tray(app.handle(), Arc::clone(&runtime_for_setup))?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(move |app_handle, event| match event {
            tauri::RunEvent::WindowEvent {
                label,
                event: tauri::WindowEvent::CloseRequested { api, .. },
                ..
            } if label == "main" => {
                let quitting = runtime_for_exit
                    .lock()
                    .expect("desktop runtime lock poisoned")
                    .quitting;
                if !quitting {
                    api.prevent_close();
                    if let Some(window) = app_handle.get_webview_window("main") {
                        let _ = window.hide();
                    }
                }
            }
            tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit => {
                stop_backend(&runtime_for_exit);
            }
            _ => {}
        });
}

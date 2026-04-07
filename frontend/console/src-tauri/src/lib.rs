use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};

const API_HOST: &str = "127.0.0.1";
const API_PORT: &str = "8787";

type SharedBackend = Arc<Mutex<Option<Child>>>;

struct BackendCommand {
    label: &'static str,
    program: &'static str,
    args: Vec<&'static str>,
    current_dir: Option<PathBuf>,
}

fn repo_root() -> Option<PathBuf> {
    let candidate = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..");
    let resolved = candidate.canonicalize().ok()?;
    let has_hive = resolved.join("pyproject.toml").exists()
        && resolved.join("src/hive/console/api.py").exists();
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

fn spawn_backend() -> Result<Child, String> {
    let mut errors = Vec::new();
    for candidate in backend_commands() {
        let mut command = Command::new(candidate.program);
        command.args(&candidate.args);
        if let Some(current_dir) = candidate.current_dir {
            command.current_dir(current_dir);
        }
        command.stdout(Stdio::null()).stderr(Stdio::null());
        match command.spawn() {
            Ok(child) => return Ok(child),
            Err(error) => errors.push(format!("{}: {}", candidate.label, error)),
        }
    }
    Err(errors.join(" | "))
}

fn stop_backend(backend: &SharedBackend) {
    if let Some(mut child) = backend.lock().expect("backend lock poisoned").take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend = Arc::new(Mutex::new(match spawn_backend() {
        Ok(child) => Some(child),
        Err(error) => {
            eprintln!(
                "Agent Hive desktop beta could not auto-start the console API on http://{}:{} ({})",
                API_HOST, API_PORT, error
            );
            None
        }
    }));
    let backend_for_exit = Arc::clone(&backend);

    tauri::Builder::default()
        // The desktop beta intentionally wraps the same browser-first console
        // instead of introducing a second frontend surface.
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(move |_app_handle, event| {
            if matches!(
                event,
                tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit
            ) {
                stop_backend(&backend_for_exit);
            }
        });
}

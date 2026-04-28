from __future__ import annotations

import http.client
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from threading import Event
from typing import TextIO

logger = logging.getLogger(__name__)

DESKTOP_API_PORT = os.getenv("CARD_READER_API_PORT", "18600")
PARSER_GRACEFUL_SHUTDOWN_TIMEOUT_SECS = 5.0
API_MODULE = "card_reader_api.desktop_main"
PARSER_MODULE = "card_reader_parser.main"
WINDOWS_CREATE_NO_WINDOW = 0x0800_0000


class ShutdownController:
    def __init__(self) -> None:
        self._event = Event()
        marker = os.getenv("CARD_READER_DESKTOP_SHUTDOWN_FILE")
        self._marker_file = Path(marker) if marker else None

    def request_stop(self, signum: int | None = None) -> None:
        if signum is not None:
            logger.info("Received shutdown signal signum=%s", signum)
        self._event.set()

    def should_stop(self) -> bool:
        if self._event.is_set():
            return True
        if self._marker_file is not None and self._marker_file.exists():
            logger.info("Shutdown marker detected. file=%s", self._marker_file)
            self._event.set()
            return True
        return False

    def interruptible_sleep(self, total_seconds: float, step_seconds: float = 0.2) -> None:
        elapsed = 0.0
        while elapsed < total_seconds and not self.should_stop():
            wait_for = min(step_seconds, total_seconds - elapsed)
            time.sleep(wait_for)
            elapsed += wait_for


class ServiceProcess:
    def __init__(
        self,
        *,
        name: str,
        module_name: str,
        env_overrides: dict[str, str],
        stdout_path: Path | None,
        cwd: Path,
    ) -> None:
        self.name = name
        self.module_name = module_name
        self._stdout_handle: TextIO | None = None

        env = os.environ.copy()
        env.update(env_overrides)

        if stdout_path is not None:
            stdout_path.parent.mkdir(parents=True, exist_ok=True)
            self._stdout_handle = stdout_path.open("a", encoding="utf-8")
            stdout: TextIO | int | None = self._stdout_handle
            stderr: TextIO | int | None = subprocess.STDOUT
        else:
            stdout = None
            stderr = None

        if os.name == "nt":
            self.process: subprocess.Popen[str] = subprocess.Popen(
                [sys.executable, "-m", module_name],
                cwd=str(cwd),
                env=env,
                stdout=stdout,
                stderr=stderr,
                creationflags=WINDOWS_CREATE_NO_WINDOW,
                text=True,
            )
        else:
            self.process = subprocess.Popen(
                [sys.executable, "-m", module_name],
                cwd=str(cwd),
                env=env,
                stdout=stdout,
                stderr=stderr,
                text=True,
            )

    @property
    def pid(self) -> int:
        return self.process.pid

    def poll(self) -> int | None:
        return self.process.poll()

    def wait(self, timeout: float | None = None) -> int:
        return self.process.wait(timeout=timeout)

    def terminate(self) -> None:
        self.process.terminate()

    def kill(self) -> None:
        self.process.kill()

    def close(self) -> None:
        if self._stdout_handle is not None:
            self._stdout_handle.close()
            self._stdout_handle = None


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )


def app_data_dir() -> Path | None:
    raw = os.getenv("CARD_READER_APP_DATA_DIR")
    if not raw:
        return None
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def parser_shutdown_marker_path(base_dir: Path | None) -> Path | None:
    if base_dir is None:
        return None
    return base_dir / "shutdown" / "parser.stop"


def clear_parser_shutdown_marker(base_dir: Path | None) -> None:
    path = parser_shutdown_marker_path(base_dir)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()


def signal_parser_shutdown(base_dir: Path | None) -> None:
    path = parser_shutdown_marker_path(base_dir)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    logger.info("Parser shutdown marker created. path=%s", path)


def service_log_path(base_dir: Path | None, name: str) -> Path | None:
    if base_dir is None:
        return None
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / f"{name}.log"


def api_healthcheck() -> bool:
    connection: http.client.HTTPConnection | None = None
    try:
        connection = http.client.HTTPConnection("127.0.0.1", int(DESKTOP_API_PORT), timeout=0.4)
        connection.request("GET", "/health")
        response = connection.getresponse()
        response.read()
        return response.status == 200
    except OSError:
        return False
    finally:
        try:
            if connection is not None:
                connection.close()
        except Exception:
            pass


def wait_for_api_ready(shutdown: ShutdownController, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline and not shutdown.should_stop():
        if api_healthcheck():
            logger.info("API healthcheck succeeded")
            return True
        shutdown.interruptible_sleep(0.25)
    logger.error("API healthcheck timed out")
    return False


def stop_service(
    service: ServiceProcess | None,
    *,
    graceful: bool,
    shutdown: ShutdownController,
    parser_base_dir: Path | None = None,
) -> None:
    if service is None:
        return

    exit_code = service.poll()
    if exit_code is not None:
        logger.info("Service already exited. service=%s exit_code=%s", service.name, exit_code)
        service.close()
        return

    if graceful and service.name == "card-reader-parser":
        signal_parser_shutdown(parser_base_dir)
        deadline = time.monotonic() + PARSER_GRACEFUL_SHUTDOWN_TIMEOUT_SECS
        while time.monotonic() < deadline:
            exit_code = service.poll()
            if exit_code is not None:
                clear_parser_shutdown_marker(parser_base_dir)
                logger.info(
                    "Service exited gracefully. service=%s pid=%s exit_code=%s",
                    service.name,
                    service.pid,
                    exit_code,
                )
                service.close()
                return
            if shutdown.should_stop():
                time.sleep(0.2)
            else:
                time.sleep(0.2)

    service.terminate()
    try:
        exit_code = service.wait(timeout=3)
        logger.info(
            "Service terminated. service=%s pid=%s exit_code=%s",
            service.name,
            service.pid,
            exit_code,
        )
    except subprocess.TimeoutExpired:
        service.kill()
        exit_code = service.wait(timeout=3)
        logger.warning(
            "Service killed after timeout. service=%s pid=%s exit_code=%s",
            service.name,
            service.pid,
            exit_code,
        )
    finally:
        if service.name == "card-reader-parser":
            clear_parser_shutdown_marker(parser_base_dir)
        service.close()


def working_dir() -> Path:
    return Path.cwd()


def spawn_api(base_dir: Path | None) -> ServiceProcess:
    env_overrides = {
        "CARD_READER_AUTH_ENABLED": "false",
        "CARD_READER_API_PORT": DESKTOP_API_PORT,
    }
    if base_dir is not None:
        env_overrides["CARD_READER_APP_DATA_DIR"] = str(base_dir)
    service = ServiceProcess(
        name="card-reader-api",
        module_name=API_MODULE,
        env_overrides=env_overrides,
        stdout_path=service_log_path(base_dir, "card-reader-api"),
        cwd=working_dir(),
    )
    logger.info("API service started. pid=%s", service.pid)
    return service


def spawn_parser(base_dir: Path | None) -> ServiceProcess:
    env_overrides = {
        "CARD_READER_API_PORT": DESKTOP_API_PORT,
        "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK": "True",
    }
    marker_path = parser_shutdown_marker_path(base_dir)
    if marker_path is not None:
        env_overrides["CARD_READER_SHUTDOWN_FILE"] = str(marker_path)
    if base_dir is not None:
        env_overrides["CARD_READER_APP_DATA_DIR"] = str(base_dir)

    service = ServiceProcess(
        name="card-reader-parser",
        module_name=PARSER_MODULE,
        env_overrides=env_overrides,
        stdout_path=service_log_path(base_dir, "card-reader-parser"),
        cwd=working_dir(),
    )
    logger.info("Parser service started. pid=%s", service.pid)
    return service


def main() -> None:
    configure_logging()
    shutdown = ShutdownController()
    signal.signal(signal.SIGTERM, lambda signum, _frame: shutdown.request_stop(signum))
    signal.signal(signal.SIGINT, lambda signum, _frame: shutdown.request_stop(signum))

    base_dir = app_data_dir()
    clear_parser_shutdown_marker(base_dir)

    api_service: ServiceProcess | None = None
    parser_service: ServiceProcess | None = None

    try:
        api_service = spawn_api(base_dir)
        if not wait_for_api_ready(shutdown, timeout_seconds=20.0):
            raise RuntimeError("card-reader-api did not become healthy in time")

        parser_service = spawn_parser(base_dir)

        while not shutdown.should_stop():
            api_exit = api_service.poll()
            if api_exit is not None:
                raise RuntimeError(f"card-reader-api exited unexpectedly with code {api_exit}")

            parser_exit = parser_service.poll()
            if parser_exit is not None:
                raise RuntimeError(f"card-reader-parser exited unexpectedly with code {parser_exit}")

            shutdown.interruptible_sleep(0.5)
    except Exception:
        logger.exception("Desktop backend supervisor failed")
        raise
    finally:
        stop_service(parser_service, graceful=True, shutdown=shutdown, parser_base_dir=base_dir)
        stop_service(api_service, graceful=False, shutdown=shutdown, parser_base_dir=base_dir)


if __name__ == "__main__":
    main()

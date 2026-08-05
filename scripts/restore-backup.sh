#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "${CARD_READER_RESTORE_RUNNER:-}" == "docker_compose" ]]; then
  archive_path=""
  backup_root=""
  include_logs=false

  while (($#)); do
    case "$1" in
      --backup-root)
        if (($# < 2)); then
          echo "Missing value for --backup-root" >&2
          exit 2
        fi
        backup_root="$2"
        shift 2
        ;;
      --backup-root=*)
        backup_root="${1#--backup-root=}"
        shift
        ;;
      --include-logs)
        include_logs=true
        shift
        ;;
      --*)
        echo "Unsupported Docker restore argument: $1" >&2
        exit 2
        ;;
      *)
        if [[ -n "$archive_path" ]]; then
          echo "Unexpected argument: $1" >&2
          exit 2
        fi
        archive_path="$1"
        shift
        ;;
    esac
  done

  if [[ -z "$archive_path" ]]; then
    echo "A backup archive path is required" >&2
    exit 2
  fi
  if [[ ! -f "$archive_path" ]]; then
    echo "Backup archive does not exist: $archive_path" >&2
    exit 2
  fi

  archive_dir="$(cd "$(dirname "$archive_path")" && pwd -P)"
  archive_name="$(basename "$archive_path")"
  if [[ -z "$backup_root" ]]; then
    backup_root="$archive_dir"
  fi
  mkdir -p "$backup_root"
  backup_root="$(cd "$backup_root" && pwd -P)"

  compose_file="${CARD_READER_RESTORE_COMPOSE_FILE:-$ROOT_DIR/docker-compose.yml}"
  compose_override_file="${CARD_READER_RESTORE_COMPOSE_OVERRIDE_FILE:-}"
  compose_service="${CARD_READER_RESTORE_COMPOSE_SERVICE:-api}"
  compose_cmd="${CARD_READER_RESTORE_COMPOSE_CMD:-docker compose}"
  read -r -a compose_args <<< "$compose_cmd"
  compose_file_args=(-f "$compose_file")
  if [[ -n "$compose_override_file" ]]; then
    compose_file_args+=(-f "$compose_override_file")
  fi

  "${compose_args[@]}" "${compose_file_args[@]}" down

  restore_args=(
    "${compose_args[@]}"
    "${compose_file_args[@]}"
    run
    --rm
    --no-deps
    -v "$archive_dir:/restore-input:ro"
    -v "$backup_root:/backup-output"
    -e "CARD_READER_APP_DATA_DIR=${CARD_READER_RESTORE_CONTAINER_APP_DATA_DIR:-/var/lib/card-reader}"
    -e "CARD_READER_PUBLIC_APP_DATA_DIR=${CARD_READER_RESTORE_CONTAINER_PUBLIC_APP_DATA_DIR:-/var/lib/card-reader}"
    -e "CARD_READER_DATABASE_PATH=${CARD_READER_RESTORE_CONTAINER_DATABASE_PATH:-card_reader.db}"
    "$compose_service"
    python
    -m
    card_reader_core.operations.restore_cli
    "/restore-input/$archive_name"
    --backup-root
    /backup-output
    --skip-compose
    --skip-healthcheck
  )
  if [[ "$include_logs" == true ]]; then
    restore_args+=(--include-logs)
  fi

  set +e
  "${restore_args[@]}"
  restore_status=$?
  set -e
  if ((restore_status != 0)); then
    "${compose_args[@]}" "${compose_file_args[@]}" up -d
    exit "$restore_status"
  fi

  exec "${compose_args[@]}" "${compose_file_args[@]}" up -d --wait
fi

exec uv run --project . python scripts/restore-backup.py "$@"

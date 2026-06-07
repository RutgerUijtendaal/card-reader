#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "${CARD_READER_BACKUP_RUNNER:-}" == "docker_compose" ]]; then
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
      *)
        echo "Unknown argument: $1" >&2
        exit 2
        ;;
    esac
  done

  if [[ -z "$backup_root" ]]; then
    echo "--backup-root is required" >&2
    exit 2
  fi
  mkdir -p "$backup_root"
  backup_root="$(cd "$backup_root" && pwd -P)"

  container_backup_root="${CARD_READER_BACKUP_CONTAINER_ROOT:-/backup}"
  compose_file="${CARD_READER_BACKUP_COMPOSE_FILE:-$ROOT_DIR/docker-compose.yml}"
  compose_service="${CARD_READER_BACKUP_COMPOSE_SERVICE:-api}"
  compose_cmd="${CARD_READER_BACKUP_COMPOSE_CMD:-docker compose}"

  read -r -a compose_args <<< "$compose_cmd"
  docker_args=(
    "${compose_args[@]}"
    -f "$compose_file"
    run
    --rm
    --no-deps
    -v "$backup_root:$container_backup_root"
    -e "CARD_READER_PUBLIC_APP_DATA_DIR=${CARD_READER_BACKUP_CONTAINER_PUBLIC_APP_DATA_DIR:-/var/lib/card-reader}"
    "$compose_service"
    python
    -m
    card_reader_core.operations.backup_cli
    --backup-root
    "$container_backup_root"
  )
  if [[ "$include_logs" == true ]]; then
    docker_args+=(--include-logs)
  fi

  exec "${docker_args[@]}"
fi

exec uv run --project . python scripts/create-backup.py "$@"

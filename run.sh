#!/bin/bash

# ========== CONFIG ==========
VENV_PATH="/home/furicada/virtualenv/admin.furi-cadaster.com/3.11/bin/activate"
APP_DIR="/home/furicada/admin.furi-cadaster.com"
UVICORN_CMD="uvicorn main:app --host 0.0.0.0 --port 8000"

# ========== FUNCTIONS ==========

activate_env() {
    echo "[Activating virtualenv and changing dir]"
    source "$VENV_PATH" && cd "$APP_DIR"
}

kill_uvicorn() {
    echo "[Killing uvicorn process]"
    pkill -f "$UVICORN_CMD"
}

nohup_start() {
    echo "[Starting uvicorn with nohup in background]"
    activate_env
    nohup $UVICORN_CMD &
    echo "[Started with nohup]"
}

restart_uvicorn() {
    echo "[Restarting uvicorn with nohup]"
    activate_env
    kill_uvicorn
    nohup $UVICORN_CMD &
    echo "[Restarted]"
}

run_foreground() {
    echo "[Running uvicorn in foreground]"
    activate_env
    $UVICORN_CMD
}

# ========== PARSE ARGS ==========
if [ $# -eq 0 ]; then
    echo "Please provide an argument."
    echo "Valid arguments: $0 [-a] [-s] [-r] [-f] [-k]"
    echo "  -a  Activate virtualenv and cd"
    echo "  -s  Start uvicorn with nohup"
    echo "  -r  Restart uvicorn with nohup"
    echo "  -f  Run uvicorn in foreground"
    echo "  -k  Kill uvicorn"
    exit 1
fi

while getopts "asrfk" opt; do
  case $opt in
    a)
      activate_env
      ;;
    k)
      kill_uvicorn
      ;;
    s)
      nohup_start
      ;;
    r)
      restart_uvicorn
      ;;
    f)
      run_foreground
      ;;
    *)
      echo "Argument is invalid"
      echo "Valid arguments: $0 [-a] [-s] [-r] [-f] [-k]"
      exit 1
      ;;
  esac
done
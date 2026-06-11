#!/bin/bash

# Color styles for logs
log_info() {
  echo -e "\033[1;34m[INFO]\033[0m $1"
}
log_success() {
  echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}
log_warn() {
  echo -e "\033[1;33m[WARNING]\033[0m $1"
}
log_error() {
  echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# 1. Check FFmpeg dependency
if ! command -v ffmpeg &> /dev/null; then
  log_error "FFmpeg is not installed or not in PATH. Please install FFmpeg before running."
  exit 1
fi
log_success "FFmpeg check passed."

# 2. Check for port conflicts (8000 for backend, 3000 for frontend)
check_port() {
  local port=$1
  if lsof -i :$port &>/dev/null; then
    return 1
  fi
  return 0
}

backend_ok=true
frontend_ok=true
check_port 8000 || backend_ok=false
check_port 3000 || frontend_ok=false

if [ "$backend_ok" = false ] || [ "$frontend_ok" = false ]; then
  log_warn "One or more required ports (8000 or 3000) are already in use."
  read -p "Would you like to kill these processes and free the ports? (y/N): " confirm
  if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
    log_info "Freeing ports 8000 and 3000..."
    lsof -t -i :8000 | xargs kill -9 2>/dev/null
    lsof -t -i :3000 | xargs kill -9 2>/dev/null
    log_success "Ports freed."
  else
    log_error "Ports are busy. Please resolve conflicts or exit other applications."
    exit 1
  fi
fi

# Cleanup on exit (Ctrl+C)
cleanup() {
  echo ""
  log_info "Stopping all servers..."
  # Kill all child processes of this shell script
  kill $(jobs -p) 2>/dev/null
  log_success "Stopped."
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 3. Start Backend Server
log_info "Starting Backend (FastAPI) on http://localhost:8000..."
if [ -d ".venv" ]; then
  PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --port 8000 --reload &
  BACKEND_PID=$!
else
  log_error "Virtual environment '.venv' not found. Run python3 -m venv .venv and install requirements."
  exit 1
fi

# Allow backend a second to bind
sleep 1

# 4. Start Frontend Server
log_info "Starting Frontend (Next.js) on http://localhost:3000..."
if [ -d "frontend/node_modules" ]; then
  npm run dev --prefix frontend &
  FRONTEND_PID=$!
else
  log_error "Frontend dependencies ('node_modules') not found. Run 'npm install' inside 'frontend/'."
  exit 1
fi

log_success "Both servers started successfully!"
log_info "Press Ctrl+C to terminate both servers."

# Wait for background processes to keep script alive
wait

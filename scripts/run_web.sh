#!/usr/bin/env bash
# Cross-platform (macOS/Linux) equivalent of scripts/run_web.ps1.
# Creates .venv, installs requirements, runs the pipeline + checks,
# exports dashboard JSON, then starts the Vite dev server.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"
WEB_ROOT="${REPO_ROOT}/web"
cd "${REPO_ROOT}"

if [ ! -x "${VENV_PYTHON}" ]; then
  echo "[setup] Creating .venv"
  python3 -m venv "${REPO_ROOT}/.venv"
fi

echo "[setup] Installing Python requirements in .venv"
"${VENV_PYTHON}" -m pip install --quiet --disable-pip-version-check --upgrade -r "${REPO_ROOT}/requirements.txt"

echo "[setup] Node $(node --version), npm $(npm --version)"

echo "[1/4] Running Python pipeline"
"${VENV_PYTHON}" "${REPO_ROOT}/run_pipeline.py"

echo "[2/4] Running scenario robustness evaluation"
"${VENV_PYTHON}" -m src.scenario_robustness

echo "[3/4] Checking generated outputs"
"${VENV_PYTHON}" "${REPO_ROOT}/tests/smoke_check_outputs.py"

echo "[4/4] Exporting web dashboard data"
"${VENV_PYTHON}" "${REPO_ROOT}/scripts/export_web_data.py"

cd "${WEB_ROOT}"
if [ ! -d "${WEB_ROOT}/node_modules" ]; then
  echo "[setup] Installing web dependencies"
  npm install
fi

echo ""
echo "Web dashboard is starting on http://127.0.0.1:5173 (or next free port)."
echo "Press Ctrl+C to stop the development server."
npm run dev -- --host 127.0.0.1 --port 5173

#!/usr/bin/env bash
# ==========================================================
# Mini-Rag MySQL Database Initialization (Linux / macOS)
# ==========================================================
# Usage:
#   chmod +x init_mysql.sh
#   ./init_mysql.sh
# ==========================================================

set -e

MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="${SCRIPT_DIR}/init_mysql.sql"

echo "=========================================================="
echo "  Mini-Rag MySQL Database Initialization"
echo "=========================================================="
echo "  Host:     ${MYSQL_HOST}"
echo "  Port:     ${MYSQL_PORT}"
echo "  User:     ${MYSQL_USER}"
echo "=========================================================="
echo

if ! command -v mysql >/dev/null 2>&1; then
    echo "[ERROR] mysql client not found. Please install MySQL first."
    exit 1
fi

if [ ! -f "${SQL_FILE}" ]; then
    echo "[ERROR] SQL file not found: ${SQL_FILE}"
    exit 1
fi

if [ -z "${MYSQL_PASSWORD}" ]; then
    MYSQL_CMD="mysql -h ${MYSQL_HOST} -P ${MYSQL_PORT} -u ${MYSQL_USER}"
else
    export MYSQL_PWD="${MYSQL_PASSWORD}"
    MYSQL_CMD="mysql -h ${MYSQL_HOST} -P ${MYSQL_PORT} -u ${MYSQL_USER}"
fi

echo "Running init_mysql.sql ..."
echo

${MYSQL_CMD} < "${SQL_FILE}"

echo
echo "[OK] MySQL database initialized successfully."
echo
echo "Next step: edit .env and set:"
echo "  DB_TYPE=mysql"
echo "  MYSQL_HOST=${MYSQL_HOST}"
echo "  MYSQL_PORT=${MYSQL_PORT}"
echo "  MYSQL_USER=${MYSQL_USER}"
echo "  MYSQL_PASSWORD=your_password"
echo "  MYSQL_DATABASE=mini_rag"

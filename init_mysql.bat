@echo off
REM ==========================================================
REM Mini-Rag MySQL 数据库初始化脚本 (Windows)
REM ==========================================================
REM 使用方法：
REM   1. 修改下面的 MYSQL_USER / MYSQL_PASSWORD / MYSQL_PORT
REM   2. 双击运行 init_mysql.bat
REM ==========================================================

setlocal

set MYSQL_USER=root
set MYSQL_PASSWORD=
set MYSQL_PORT=3306
set MYSQL_HOST=localhost

echo.
echo ==========================================================
echo   Mini-Rag MySQL Database Initialization
echo ==========================================================
echo   Host:     %MYSQL_HOST%
echo   Port:     %MYSQL_PORT%
echo   User:     %MYSQL_USER%
echo ==========================================================
echo.

where mysql >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] mysql client not found in PATH.
    echo Please install MySQL or add its bin directory to PATH.
    pause
    exit /b 1
)

if "%MYSQL_PASSWORD%"=="" (
    set MYSQL_CMD=mysql -h %MYSQL_HOST% -P %MYSQL_PORT% -u %MYSQL_USER%
) else (
    set MYSQL_CMD=mysql -h %MYSQL_HOST% -P %MYSQL_PORT% -u %MYSQL_USER% -p%MYSQL_PASSWORD%
)

echo Running init_mysql.sql ...
echo.

%MYSQL_CMD% < "%~dp0init_mysql.sql"

if %errorlevel% equ 0 (
    echo.
    echo [OK] MySQL database initialized successfully.
    echo.
    echo Next step: edit .env and set:
    echo   DB_TYPE=mysql
    echo   MYSQL_HOST=%MYSQL_HOST%
    echo   MYSQL_PORT=%MYSQL_PORT%
    echo   MYSQL_USER=%MYSQL_USER%
    echo   MYSQL_PASSWORD=your_password
    echo   MYSQL_DATABASE=mini_rag
) else (
    echo.
    echo [ERROR] Failed to initialize MySQL database.
)

echo.
pause

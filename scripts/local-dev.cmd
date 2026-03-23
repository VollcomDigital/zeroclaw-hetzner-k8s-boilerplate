@echo off
setlocal
cd /d "%~dp0.."
where pwsh >nul 2>&1 && (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0local-dev.ps1" %*
  exit /b %ERRORLEVEL%
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0local-dev.ps1" %*
exit /b %ERRORLEVEL%

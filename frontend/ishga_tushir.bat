@echo off
rem Libosa frontend dev serverini ishga tushiradi (http://localhost:5173)
cd /d "%~dp0"
if not exist node_modules (call npm install)
call npm run dev
pause

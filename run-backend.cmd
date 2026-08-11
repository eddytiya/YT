@echo off
cd /d "D:\PROJECTS\YT\backend"
call .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8010

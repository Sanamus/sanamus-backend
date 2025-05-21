@echo off
cd /d C:\Users\Kasutaja\OneDrive\Desktop\python\Sanamus
call ..\venv\Scripts\activate.bat
uvicorn app.main:app --reload
pause
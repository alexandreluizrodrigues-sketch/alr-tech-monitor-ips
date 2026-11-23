@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente virtual...
  py -3 -m venv .venv
  if errorlevel 1 (echo Falha ao criar ambiente virtual. Instale o Python 3.11+ e habilite o launcher py. & pause & exit /b 1)
)
echo Instalando/validando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (echo Falha na instalacao das dependencias. & pause & exit /b 1)
start "ALR TECH Coletor de IPs" cmd /k ""%~dp0.venv\Scripts\python.exe" "%~dp0collector.py""
start "ALR TECH Dashboard de IPs" cmd /k ""%~dp0.venv\Scripts\python.exe" -m streamlit run "%~dp0dashboard.py" --server.address 127.0.0.1 --server.port 8501"
echo Dashboard: http://localhost:8501
timeout /t 3 > nul
start "" "http://localhost:8501"

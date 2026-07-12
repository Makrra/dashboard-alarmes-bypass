@echo off
REM Gera o executavel unico (dist\AnaliseAlarmesBypass.exe) a partir de src\main.py.
REM Rodar este arquivo com duplo clique (ou "build.bat" no terminal) dentro da
REM pasta do projeto, com o Python e as dependencias do requirements.txt instalados.

cd /d "%~dp0"

python -m pip install -r requirements.txt
if errorlevel 1 goto erro

python -m PyInstaller --onefile --console --clean ^
    --name AnaliseAlarmesBypass ^
    --distpath dist ^
    --workpath build ^
    --specpath build ^
    src\main.py
if errorlevel 1 goto erro

echo.
echo Build concluido! O executavel esta em: dist\AnaliseAlarmesBypass.exe
pause
exit /b 0

:erro
echo.
echo Ocorreu um erro durante o build. Veja as mensagens acima.
pause
exit /b 1

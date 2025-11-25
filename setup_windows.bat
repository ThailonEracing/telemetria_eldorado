@echo off
REM Script de instalação e verificação para Windows
REM Para Monitor CAN - Driver Kvaser

echo ================================
echo Monitor CAN - Setup Windows
echo ================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python não encontrado!
    echo.
    echo 1. Baixe Python 3.8+ de https://python.org
    echo 2. Marque "Add Python to PATH" durante instalação
    echo 3. Reinicie este script
    pause
    exit /b 1
) else (
    echo [OK] Python encontrado
    python --version
)

echo.

REM Instalar dependências Python
echo Instalando dependências Python...
pip install python-can matplotlib numpy pandas

if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependências
    echo.
    echo Tente manualmente:
    echo pip install python-can matplotlib numpy pandas
    pause
    exit /b 1
) else (
    echo [OK] Dependências instaladas
)

echo.

REM Verificar driver Kvaser
echo Verificando driver Kvaser...
python -c "import can.interface.kvaser; print('[OK] Driver Kvaser disponível')" 2>nul
if errorlevel 1 (
    echo [AVISO] Driver Kvaser não encontrado
    echo.
    echo 1. Baixe driver Kvaser de: https://www.kvaser.com/downloads/
    echo 2. Instale "Kvaser Windows Driver Package"
    echo 3. Reinicie o computador
    echo 4. Execute novamente este script
    echo.
) else (
    echo [OK] Driver Kvaser encontrado
)

echo.

REM Verificar interfaces disponíveis
echo Interfaces CAN disponíveis:
python -c "import can; print('\n'.join(can.interface.Bus.available_interfaces()))"

echo.

REM Testar canais Kvaser
echo Testando canais Kvaser...
for /l %%i in (0,1,3) do (
    python -c "import can; can.interface.Bus(channel='%%i', interface='kvaser').shutdown()" 2>nul
    if errorlevel 1 (
        echo Canal %%i: Não disponível
    ) else (
        echo Canal %%i: Disponível ✓
    )
)

echo.
echo ================================
echo Setup completo!
echo ================================
echo.
echo Comandos para testar:
echo.
echo 1. Modo simulação (sem hardware):
echo    python monitor_windows_kvaser.py --simulate
echo.
echo 2. Com hardware Kvaser:
echo    python monitor_windows_kvaser.py --channel 0
echo    python monitor_windows_kvaser.py --channel 1
echo.
echo 3. Replay de arquivo de log:
echo    python replay_windows_kvaser.py exemplo_log_can.log
echo.
echo 4. Verificar drivers apenas:
echo    python replay_windows_kvaser.py --check-drivers
echo.
pause
@echo off
rem Primeira vez em um Windows: instala o Docker Desktop se nao houver (pergunta antes), prepara o .env e liga tudo.
rem Para so ver o que ele faria, sem instalar: ligar-tudo-e-instalar-docker.bat -Teste
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\instalar-e-ligar.ps1" %*
echo.
pause

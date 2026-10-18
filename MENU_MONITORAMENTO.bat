@echo off
setlocal
title Clealco - Monitoramento de Mosca
cd /d "%~dp0"

:MENU
cls
color 0A
echo ================================================================================
echo             CLEALCO - MONITORAMENTO DE MOSCA (SISTEMA WEB)
echo ================================================================================
echo.
echo   [1] Abrir Mapa de Coleta no Navegador (index.html)
echo   [2] Baixar Relatorio de Coletas em Excel (Coletas_Monitoramento_Mosca.xlsx)
echo   [3] Atualizar Base do Mapa (Processar novos shapefiles para o mapa web)
echo   [4] Publicar Alteracoes no GitHub (Atualizar App do Celular)
echo   [0] Sair
echo.
echo ================================================================================
echo.
choice /C 12340 /N /M "Pressione 1, 2, 3, 4 ou 0: "

if errorlevel 5 goto OP_SAIR
if errorlevel 4 goto OP_GITHUB
if errorlevel 3 goto OP_UPDATE
if errorlevel 2 goto OP_EXCEL
if errorlevel 1 goto OP_OPEN_WEB
goto MENU

:OP_OPEN_WEB
cls
echo Abrindo o Mapa de Coleta no navegador...
start "" "index.html"
echo Pronto!
timeout /t 2 > nul
goto MENU

:OP_EXCEL
cls
color 0A
echo ================================================================================
echo   [2] BAIXANDO COLETAS DA NUVEM PARA PLANILHA EXCEL...
echo ================================================================================
echo.
python baixar_planilha_coletas.py
echo.
echo ================================================================================
pause
goto MENU

:OP_UPDATE
cls
color 0B
echo ================================================================================
echo   [3] ATUALIZANDO BASE DO MAPA WEB...
echo ================================================================================
echo.
python atualizar_base_web.py
echo.
echo ================================================================================
pause
goto MENU

:OP_GITHUB
cls
color 0B
echo ================================================================================
echo   [4] PUBLICANDO ATUALIZACOES NO GITHUB (APP DO CELULAR)...
echo ================================================================================
echo.
echo -> Verificando arquivos alterados...
git add -A
git status -s
echo.
echo -> Enviando atualizacoes para o GitHub...
git commit -m "Atualizacao do sistema e base geografica" > nul 2>&1
git push origin main
echo.
echo ================================================================================
echo   [CONCLUIDO] Projeto sincronizado com o GitHub com sucesso!
echo   Basta tocar em 'Atualizar' no celular para carregar as mudancas.
echo ================================================================================
pause
goto MENU

:OP_SAIR
cls
endlocal
exit

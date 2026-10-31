@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

:: ==========================================
:: CONFIGURAÇÃO DOS CAMINHOS DIRETOS (SEM RECURSÃO)
:: ==========================================
set "PROJECT_DIR=C:\Users\User\Documents\PÓS GESTÃO ESTRATÉGICA DE DADOS\05 - AWS PARA GESTÃO DE DADOS"
set "LOG_DIR=%PROJECT_DIR%\log"

:: ==========================================
:: TIMESTAMP SEGURO
:: ==========================================
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set DATETIME=%%I
set DAT_ESTATE=%DATETIME:~0,8%
set HR_TORUN=%DATETIME:~8,6%

set "LOG_FILE=%LOG_DIR%\pipeline_%DAT_ESTATE%_%HR_TORUN%.log"

echo ------------------------------------------
echo PIPELINE LAKEHOUSE POS-GRADUACAO
echo ------------------------------------------

:: ==========================================
:: CRIA DIRETORIO DE LOG
:: ==========================================
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
)

:: ==========================================
:: EXECUCAO DAS ETAPAS
:: ==========================================
echo ETAPA 1 - LEGADO UPLOAD
echo ETAPA 1 - LEGADO UPLOAD >> "%LOG_FILE%"
python "%PROJECT_DIR%\scripts\upload_legado.py" >> "%LOG_FILE%" 2>&1
if !errorlevel! gtr 0 goto erro

echo ETAPA 2 - RAW TO TRUSTED
echo ETAPA 2 - RAW TO TRUSTED >> "%LOG_FILE%"
python "%PROJECT_DIR%\scripts\legado_to_raw.py" >> "%LOG_FILE%" 2>&1
if !errorlevel! gtr 0 goto erro

echo ETAPA 3 - RAW TO TRUSTED
echo ETAPA 3 - RAW TO TRUSTED >> "%LOG_FILE%"
python "%PROJECT_DIR%\scripts\raw_to_trusted.py" >> "%LOG_FILE%" 2>&1
if !errorlevel! gtr 0 goto erro

echo ETAPA 4 - CTAS ATHENA (CURATED)
echo ETAPA 4 - CTAS ATHENA (CURATED) >> "%LOG_FILE%"
python "%PROJECT_DIR%\scripts\run_ctas_athena.py" >> "%LOG_FILE%" 2>&1
if !errorlevel! gtr 0 goto erro

goto fim

:erro
echo ERRO NA EXECUCAO DO PIPELINE >> "%LOG_FILE%"
echo FIM COM ERRO >> "%LOG_FILE%"
exit /b 1

:fim
echo FIM COM SUCESSO >> "%LOG_FILE%"
exit /b 0


@echo off
title LSVI Survey123 Publicatie Pipeline (Via Anaconda Prompt)
cls

echo =======================================================
echo  START LSVI AUTOMATISCHE PUBLICATIE PIPELINE
echo =======================================================
echo.

REM --- PADEN CONFIGURATIE ---
REM Omdat je in Anaconda Prompt zit, is het simpele commando 'python' voldoende!
SET SCRIPT_PATH="Q:\Projects\PRJ_GIS\lsvi-app-testing\src\publish_survey.py"
SET EXCEL_OUTPUT_DIR=Q:\Projects\PRJ_GIS\lsvi-app-testing\output

@REM echo [STAP 1/3] Verwerken van Habitat 1-4...
@REM python %SCRIPT_PATH% --xlsform-path "%EXCEL_OUTPUT_DIR%\xlsform_hab1-4.xlsx" --target-folder "Survey-LSVI App Test Auto"
@REM echo.

@REM echo [STAP 2/3] Verwerken van Habitat 5-7...
@REM python %SCRIPT_PATH% --xlsform-path "%EXCEL_OUTPUT_DIR%\xlsform_hab5-7.xlsx" --target-folder "Survey-LSVI App Test Auto"
echo.

echo [STAP 3/3] Verwerken van Habitat 9...
python %SCRIPT_PATH% --xlsform-path "%EXCEL_OUTPUT_DIR%\xlsform_hab9.xlsx" --target-folder "Survey-LSVI App Test Auto"

@REM add parameter --manual_old_survey_id to force the script to use the old survey ID for Habitat 9, in case you manually deleted a form from AGOL.
@REM python %SCRIPT_PATH% --xlsform-path "%EXCEL_OUTPUT_DIR%\xlsform_hab9.xlsx" --target-folder "Survey-LSVI App Test Auto" --manual_old_survey_id "a637a3e62fec4a6b80d19c5d642607b0"

echo.

echo =======================================================
echo  PIPELINE VOLTOOID! Alle geselecteerde surveys verwerkt.
echo =======================================================
echo.
pause

@echo off
title LSVI Survey123 Update Pipeline (Via Anaconda Prompt)
cls

echo =======================================================
echo  START LSVI AUTOMATISCHE UPDATE PIPELINE
echo =======================================================
echo.

REM --- PADEN CONFIGURATIE ---
REM Omdat je in Anaconda Prompt zit, is het simpele commando 'python' voldoende!
SET SCRIPT_PATH="Q:\Projects\PRJ_GIS\lsvi-app-testing\src\update_survey.py"
set XLSFORM_PATH1="Q:\Projects\PRJ_GIS\lsvi-app-testing\output\xlsform_hab1-4.xlsx"
set XLSFORM_PATH2="Q:\Projects\PRJ_GIS\lsvi-app-testing\output\xlsform_hab5-7.xlsx"
set XLSFORM_PATH3="Q:\Projects\PRJ_GIS\lsvi-app-testing\output\xlsform_hab9.xlsx"


echo [STAP 1/3] Updaten survey voor Habitat 1-4...
python %SCRIPT_PATH% --xlsform "%XLSFORM_PATH1%" --webmap-id "64c1f0bd02344d5ebf41c3dd320615bc"
echo.

echo [STAP 2/3] Updaten survey voor Habitat 5-7...
python %SCRIPT_PATH% --xlsform "%XLSFORM_PATH2%" --webmap-id "64c1f0bd02344d5ebf41c3dd320615bc"
echo.
echo [STAP 3/3] Updaten survey voor Habitat 9...
python %SCRIPT_PATH% --xlsform "%XLSFORM_PATH3%" --webmap-id "64c1f0bd02344d5ebf41c3dd320615bc"
echo.

echo ===================
echo  PIPELINE VOLTOOID! 
echo ===================
echo.
pause
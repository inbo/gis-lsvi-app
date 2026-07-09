call conda activate python-gis

REM Generate survey for habitat type 1-4
python src/xlsform_generation.py --habitat-filter 1 2 3 4 --output-file output/xlsform_hab1-4.xlsx --form-title "LSVI Habitat 1-4"

REM Generate survey for habitat type 6
python src/xlsform_generation.py --habitat-filter 5 6 7 --output-file output/xlsform_hab5-7.xlsx --form-title "LSVI Habitat 5-7"

REM Generate survey for habitat types 3 and 4
python src/xlsform_generation.py --habitat-filter 9 --output-file output/xlsform_hab9.xlsx --form-title "LSVI Habitat 9"

pause
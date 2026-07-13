"Script to grab dedicated list of xls forms and publis has survey123 objects in AGOL."

import argparse
from pathlib import Path
import sys
import time
from arcgis.gis import GIS
import os

# Get the absolute path of the folder above the notebook
parent_dir = os.path.abspath(os.path.join(os.getcwd(), "."))

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src import utils

# Load secrets into environment
LOCAL_DB = "G:\Mijn Drive\keepass_db.kdbx"
ENTRY_TITLE = "AGOL"
AGOL_URL = "https://gisservices.inbo.be/portal"

def main():
    # 1. Bouw de Argument Parser voor command line input
    parser = argparse.ArgumentParser(
        description="Verwijder en publiceer een specifieke Survey123 survey in AGOL."
    )
    parser.add_argument(
        "--xlsform-path", required=True, help="Het bestandspad naar het XLSX/XLSForm"
    )
    parser.add_argument(
        "--target-folder",
        default="Survey-LSVI App Test Auto",
        help="De doelmap in ArcGIS Online (default: Survey-LSVI App Test Auto)",
    )

    args = parser.parse_args()
    xlsform_path = Path(args.xlsform_path)

    if not xlsform_path.exists():
        print(f" [!] Fout: Bestand niet gevonden op pad: '{xlsform_path}'")
        sys.exit(1)

    # Automatisch de surveynaam afleiden van de bestandsnaam (zonder .xlsx)
    survey_name = xlsform_path.stem

    # 2. Laden van KeePass inloggegevens en connectie maken met AGOL
    print("Inloggegevens ophalen uit KeePass...")
    AGOL_USER, AGOL_PASS = utils.load_keepass_credentials(
        db_path=LOCAL_DB, entry_name=ENTRY_TITLE
    )
    gis = GIS(AGOL_URL, AGOL_USER, AGOL_PASS)

    # DELETE
    utils.delete_specific_survey(gis, survey_name=survey_name)

    # PUBLISH
    item_id = utils.upload_survey(
            gis=gis,
            xlsform_path=xlsform_path,
            target_folder=args.target_folder,
            thumbnail_path = r"./inbo_logo.jpg",
        )
        
if __name__ == "__main__":
    main()
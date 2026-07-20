"Script to grab dedicated list of xls forms and publis has survey123 objects in AGOL."

import argparse
from pathlib import Path
import sys
import time
from arcgis.gis import GIS
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    old_survey_id = utils.delete_specific_survey(gis, survey_name=survey_name)

    # PUBLISH
    new_survey_id = utils.upload_survey(
            gis=gis,
            xlsform_path=xlsform_path,
            target_folder=args.target_folder,
            thumbnail_path = r"./inbo_logo.jpg",
        )
    
    # Update BWK field map web app item with new form id
    FIELD_MAP_ID = "ad1a1d268ddf4f02b1bb48f6f1b85f1c"

    # Get the web map's internal data configuration
    map_item = gis.content.get(FIELD_MAP_ID)
    map_data = map_item.get_data()

    # Convert configuration to a string to easily replace the old ID globally
    map_data_str = json.dumps(map_data)

    # Scenario A: The survey ID did not change (e.g., standard overwrite publish)
    if old_survey_id == new_survey_id:
        print("ℹ️ The survey ID did not change. No web map update is required.")

    # Scenario B: The survey ID changed (e.g., wipe and recreate workflow)
    elif old_survey_id in map_data_str:
        # Safely swap out ONLY the old target ID with the new one
        updated_map_data_str = map_data_str.replace(old_survey_id, new_survey_id)
        updated_map_data = json.loads(updated_map_data_str)
        
        # Push the updated data config back to the Web Map item in AGOL
        map_item.update(data=updated_map_data)
        print(f"Success! Updated the pop-up link in the Web Map from {old_survey_id} to {new_survey_id}.")

    # Scenario C: Safety net in case the survey ID isn't found in the popup at all
    else:
        print(
            f"⚠️ Warning: The old survey ID ({old_survey_id}) for '{survey_name}' "
            "was not found in the Web Map pop-up configuration. No update was made."
        )
            
if __name__ == "__main__":
    main()
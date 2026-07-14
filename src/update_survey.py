"""Script to update a specific survey123 survey in AGOL with a new XLSForm and update the corresponding field map link to the survey."""

import argparse
import json
import sys
from pathlib import Path
from arcgis.gis import GIS
import arcgis
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Zorg dat de lokale utils.py geïmporteerd kan worden
try:
    import utils
except ImportError:
    print("Fout: Kan 'utils.py' niet vinden in de huidige map. Zorg dat deze in dezelfde directory staat.")
    sys.exit(1)

# Load secrets into environment
LOCAL_DB = r"G:\Mijn Drive\keepass_db.kdbx"
ENTRY_TITLE = "AGOL"
AGOL_URL = "https://gisservices.inbo.be/portal"

def main():

    parser = argparse.ArgumentParser(
        description="Update een specifieke Survey123 survey en pas de bijbehorende Field Map link aan."
    )
    
    parser.add_argument(
        "-x", "--xlsform", 
        required=True, 
        help="Volledig pad naar het nieuwe XLSForm Excel-bestand (.xlsx)"
    )

    parser.add_argument(
        "-w", "--webmap-id", 
        default="64c1f0bd02344d5ebf41c3dd320615bc", 
        help="ID van de Field Map Web Map waarin de popup link staat"
    )

    args = parser.parse_args()

    # Laden van KeePass inloggegevens en connectie maken met AGOL
    print("Inloggegevens ophalen uit KeePass...")
    AGOL_USER, AGOL_PASS = utils.load_keepass_credentials(
        db_path=LOCAL_DB, entry_name=ENTRY_TITLE
    )
    
    # Verbinding maken met ArcGIS Online
    print("Verbinding maken met ArcGIS...")
    try:
        gis = GIS(AGOL_URL, AGOL_USER, AGOL_PASS, verify_cert=True)
        survey_manager = arcgis.apps.survey123.SurveyManager(gis)
    except Exception as e:
        print(f"Fout bij het inloggen op ArcGIS: {e}")
        sys.exit(1)

    # Pad naar xlsform
    xlsform_path = Path(args.xlsform)
    if not xlsform_path.exists():
        print(f"Fout: Het bestand '{xlsform_path}' bestaat niet.")
        sys.exit(1)
    survey_name = xlsform_path.stem
    print(f"Survey naam afgeleid van XLSForm: '{survey_name}'")
    print(f" [*] Pad naar XLSForm: '{xlsform_path}'")

    # Find old survey object
    try:
        old_survey_id = utils.get_survey_id_by_name(survey_manager, survey_name)
        print(f"Bestaande survey ({old_survey_id}) voor '{survey_name}' gevonden. Updaten gestart...")
    except ValueError as e:
        print(f"Fout: {e}")
        sys.exit(1)

    # Update old survey
    try:
        mijn_survey = survey_manager.get(old_survey_id)
        mijn_survey.publish(
            xlsform=str(xlsform_path),
            schema_changes=True
        )
        print("✅ Survey succesvol overschreven!")
    except Exception as e:
        print(f"Fout tijdens het publiceren van de survey: {e}")
        sys.exit(1)

    # Fetch new ID of survey (form object)
    new_survey_id = utils.get_survey_id_by_name(survey_manager, survey_name)
    print(f"Nieuw survey object actief: {new_survey_id}")

    # Update survey link in Field Map Web Map
    print("Field Map pop-up links controleren...")
    try:
        map_item = gis.content.get(args.webmap_id)
        if not map_item:
            print(f"Waarschuwing: Web Map met ID {args.webmap_id} niet gevonden.")
            sys.exit(0)

        map_data = map_item.get_data()
        map_data_str = json.dumps(map_data)

        # Scenario A: ID is gelijk gebleven
        if old_survey_id == new_survey_id:
            print("ℹ️ De survey ID is ongewijzigd gebleven. Web Map update is niet nodig.")

        # Scenario B: ID is gewijzigd (bijv. na een harde wipe-and-replace)
        elif old_survey_id in map_data_str:
            updated_map_data_str = map_data_str.replace(old_survey_id, new_survey_id)
            updated_map_data = json.loads(updated_map_data_str)
            
            map_item.update(data=updated_map_data)
            print(f"Succes! De pop-up link in de Web Map is bijgewerkt van {old_survey_id} naar {new_survey_id}.")

        # Scenario C: Oude ID niet gevonden in popup string
        else:
            print(
                f"⚠️ Waarschuwing: De oude survey ID ({old_survey_id}) voor '{survey_name}' "
                "is niet aangetroffen in de Web Map pop-up configuratie. Geen update uitgevoerd."
            )
            
    except Exception as e:
        print(f"Fout bij het bijwerken van de Web Map: {e}")

if __name__ == "__main__":
    main()
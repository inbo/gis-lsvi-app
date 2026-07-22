import argparse
from pathlib import Path
import sys
import os
import urllib3
from arcgis.gis import GIS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get the absolute path of the folder above the script
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src import utils


def give_access_to_group(group_name, target_folder):
    """
    Share all items in a target folder with a specific group on AGOL.
    
    Args:
        group_name (str): The name of the group to share with
        target_folder (str): The name of the folder containing items to share
    """
    # Connect to AGOL
    # Define your local specific paths 
    LOCAL_DB = "G:\\Mijn Drive\\keepass_db.kdbx"
    ENTRY_TITLE = "AGOL"

    # Get credentials from key vault
    AGOL_USER, AGOL_PASS = utils.load_keepass_credentials(db_path=LOCAL_DB, entry_name=ENTRY_TITLE)

    agol_url = "https://gisservices.inbo.be/portal"
    gis = GIS(agol_url, AGOL_USER, AGOL_PASS)

    # Get group
    lsvi_group = gis.groups.search(query=f"title: {group_name}", max_groups=15)
    if not lsvi_group:
        raise ValueError(f"Groep '{group_name}' niet gevonden op AGOL")
    
    lsvi_group = lsvi_group[0]
    lsvi_group_id = lsvi_group.id

    # Get all items in target folder
    user = gis.users.me
    folder_items = list(user.items(folder=target_folder))
    
    print(f"Deel {len(folder_items)} items uit map '{target_folder}' met groep '{lsvi_group.title}'...")

    for item in folder_items:
        try:
            # item.share() deelt het item direct met de opgegeven groep(en)
            item.share(groups=[lsvi_group])
            print(f" [✓] Gedeeld: {item.title} ({item.type})")
        except Exception as e:
            print(f" [!] Fout bij delen van {item.title}: {e}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Share items from an AGOL folder with a specific group",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python give_access.py "LSVI Group" "MyTargetFolder"
  python give_access.py --group_name "LSVI Group" --target_folder "MyTargetFolder"
        """
    )
    
    parser.add_argument(
        "group_name",
        metavar="GROUP_NAME",
        help="The name of the group to share items with"
    )
    
    parser.add_argument(
        "target_folder",
        metavar="TARGET_FOLDER",
        help="The name of the folder containing items to share"
    )
    
    args = parser.parse_args()
    
    try:
        give_access_to_group(args.group_name, args.target_folder)
        print("\n✓ Proces voltooid!")
    except Exception as e:
        print(f"\n✗ Fout: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
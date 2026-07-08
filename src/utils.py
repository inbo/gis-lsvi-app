import re
import pandas as pd
import getpass
import shutil
from sys import platform
import subprocess
import os

def load_keepass_credentials(db_path, entry_name, key_file=None, cli_path=None):
    """
    Securely prompts for a KeePassXC master password, fetches a username 
    and password from a local database entry, and loads them into os.environ.
    
    :param db_path: Absolute path to your local .kdbx file.
    :param entry_name: The exact title of the entry inside KeePassXC.
    :param key_file: Optional path to a KeePassXC key file if your database uses one.
    :param cli_path: Optional explicit path to the keepassxc-cli executable.
    """
    # 1. Automatically detect keepassxc-cli path based on Operating System
    if not cli_path:
        cli_path = shutil.which("keepassxc-cli")
        if not cli_path:
            os_type = platform.system()
            if os_type == "Windows":
                cli_path = r"C:\Program Files\KeePassXC\keepassxc-cli.exe"
            elif os_type == "Darwin":  # macOS
                cli_path = "/Applications/KeePassXC.app/Contents/MacOS/keepassxc-cli"
            else:
                cli_path = "keepassxc-cli"
                
    if not os.path.exists(cli_path) and not shutil.which(cli_path):
        raise FileNotFoundError(
            f"Could not find 'keepassxc-cli' executable at '{cli_path}'.\n"
            "Please ensure KeePassXC is installed locally or provide an explicit cli_path."
        )

    # 2. Securely prompt for the master password inside the Jupyter UI
    master_password = getpass.getpass("Enter your local KeePassXC Master Password: ")

    # 3. Construct the CLI command
    # -s: Show protected attributes (like passwords) in clear text
    # -a: Query multiple attributes sequentially (UserName first, then Password)
    cmd = [cli_path, "show", "-s", "-a", "UserName", "-a", "Password"]
    
    if key_file:
        cmd.extend(["-k", key_file])
        
    cmd.extend([db_path, entry_name])

    # 4. Execute command and safely pipe the master password
    try:
        # Appending '\n' mimics pressing 'Enter' on a standard terminal prompt
        result = subprocess.run(
            cmd,
            input=f"{master_password}\n",
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        print(f"❌ Failed to retrieve credentials. Error details:\n{error_msg}")
        return False
    finally:
        # Clean up the password variable reference from local memory context
        del master_password

    # 5. Parse the sequential output and assign to environment variables
    output_lines = result.stdout.strip().splitlines()
    if len(output_lines) >= 2:
        os.environ["NOTEBOOK_USER"] = output_lines[0].strip()
        os.environ["NOTEBOOK_PASSWORD"] = output_lines[1].strip()
        print(f"✅ Success: Credentials for '{entry_name}' loaded into environment variables!")
        return output_lines[0].strip(), output_lines[1].strip()
    else:
        print("❌ Error: KeePassXC did not return both a username and password line.")
        return False

def clean_name(hab_text):
    """Maakt een string veilig voor Survey123 (maximaal 2 delen gescheiden door 1 underscore)"""
    if pd.isna(hab_text): return "onbekend"
    
    # Alles naar kleine letters
    hab_text = str(hab_text).lower().strip()
    
    # Hak de tekst in stukken op elke bestaande underscore
    parts = hab_text.split('_')
    
    # Saneer elk stukje: verwijder alles wat GEEN letter of cijfer is
    # (Lege stukjes filteren we er meteen uit met 'if part')
    cleaned_parts = [re.sub(r'[^a-z0-9]', '', part) for part in parts if part]
    
    # Pak maximaal de eerste twee onderdelen
    limited_parts = cleaned_parts[:2]
    
    # Plak ze weer aan elkaar met exact één underscore (of geen, als er maar 1 deel is)
    return "_".join(limited_parts)

def get_habitat_hint(habitattype_code):
    """
    Genereert een dynamische hint voor een habitattype, met vermelding
    van de parent-habitat indien deze bestaat.
    """
    # hardcode lookup habitattypes for now joost
    df_habitattypes = pd.read_sql_table('Habitattype', 'sqlite:///../input/LSVIHabitatTypes.sqlite')

    # 1. Zoek het habitattype op basis van de Code
    match = df_habitattypes[df_habitattypes['Code'] == habitattype_code]
    
    # Fallback als de code niet in de tabel zit
    if match.empty:
        return f"{habitattype_code}: Geen omschrijving gevonden"
        
    row = match.iloc[0]
    code = row['Code']
    naam = row['Naam']
    parent_id = row['ParentId']
    
    # 2. Check of er een geldige ParentId is (Niet NaN, null of leeg)
    if pd.notna(parent_id) and str(parent_id).strip() != "":
        
        # 3. Zoek de parent op basis van de Id
        parent_match = df_habitattypes[df_habitattypes['Id'] == parent_id]
        
        if not parent_match.empty:
            parent_row = parent_match.iloc[0]
            parent_code = parent_row['Code']
            parent_naam = parent_row['Naam']
            # parent_naamkort = parent_row.get('NaamKort', '') # Indien je deze in de toekomst nodig hebt
            
            # 4. Return the gelaagde string
            # Tip: In Survey123 kan je ook HTML gebruiken zoals <br> in plaats van \n als \n niet goed rendert.
            hint = (
                f"{code}: {naam}\n"
                f"Deze habitat is een subtype van habitat {parent_code}:\n"
                f"{parent_naam}"
            )
            return hint
            
    # 5. Als er geen ParentId is, return de simpele string
    return f"{code}: {naam}"

def get_question_label(vereiste):
    """Genereer HTML-geformatteerde label voor een vraag op basis van de vereiste data"""
    # 1. Haal de basiswaarden op (zorg dat het strings zijn)
    indicator = str(vereiste['Indicator'])
    voorwaarde = str(vereiste['Voorwaarde'])
    beoordeling = str(vereiste['Beoordeling'])
    referentie_waarde = str(vereiste['Referentiewaarde'])

    # 2. Check of er een Eenheid is ingevuld (niet NaN en niet leeg)
    eenheid = ""
    if pd.notna(vereiste['Eenheid']) and str(vereiste['Eenheid']).strip() != "":
        eenheid = f" ({vereiste['Eenheid']})" # Plaats het tussen haakjes, of pas aan naar wens

    # 3. Bouw de HTML-geformatteerde string op
    # Let op: <br> zorgt voor een nieuwe regel in Survey123
    # We force non-bold text for the values in case the question label is the group label
    html_label = (
        f"<b>Indicator:</b> <span style='font-weight: normal;'>{indicator}</span><br>"
        f"<b>Voorwaarde:</b> <span style='font-weight: normal;'>{voorwaarde}{eenheid}</span><br>"
        f"<b>Beoordeling:</b> <span style='font-weight: normal;'><i>{beoordeling}</i></span><br>"
        f"<b>Referentiewaarde:</b> <span style='font-weight: normal;'>{referentie_waarde}</span>"
    )
    return html_label

def get_species_hint(taxongroep_id, df_soorten):
    """
    Genereert een Survey123-veilige HTML hint met alle soorten voor een specifieke TaxongroepId.
    """
    # 1. Als er geen TaxongroepId is (NaN), return een lege hint
    if pd.isna(taxongroep_id) or str(taxongroep_id).strip() == "":
        return ""
    
    # Zorg ervoor dat we met integers vergelijken indien mogelijk
    try:
        tax_id = float(taxongroep_id)
    except ValueError:
        return ""

    # 2. Filter de soortenlijst
    soorten = df_soorten[df_soorten['TaxongroepId'] == tax_id]
    
    # Als er geen soorten gevonden zijn, return leeg
    if soorten.empty:
        return ""
        
    # 3. Bouw de veilige HTML op (een lijst met <br> en opsommingstekens)
    species_lines = []
    
    for idx, soort in soorten.iterrows():
        wet_naam = str(soort['WetNaam']).strip()
        ned_naam = str(soort['NedNaam']).strip()
        
        # Check of de Nederlandse naam geldig is (niet leeg of 'nan')
        if pd.isna(soort['NedNaam']) or ned_naam.lower() == "nan" or ned_naam == "":
            # Enkel wetenschappelijke naam
            lijn = f"• <i>{wet_naam}</i>"
        else:
            # Nederlandse naam met wetenschappelijke naam tussen haakjes
            lijn = f"• {ned_naam} (<i>{wet_naam}</i>)"
            
        species_lines.append(lijn)
        
    # Verbind alle lijnen met een HTML line-break
    return "<br>".join(species_lines)

def get_question_settings(row):
    type_var = str(row['schaal_type']).strip().lower()

    if type_var == 'lsvi':
        answer_type = "select_one LSVI"  # Verwijst naar de 'LSVI' lijst in survey123_schalen.csv
        vraag_appearance = ""  # Verticaal met radio buttons
    elif 'bedekking' in type_var:
        answer_type = "select_one Standaard"  # Verwijst naar de 'Standaard' lijst in survey123_schalen.csv
        vraag_appearance = "minimal autocomplete"  # Optioneel: maakt de opties naast elkaar in plaats van onder elkaar
    elif type_var == 'aantal' and pd.notna(row['TaxongroepId']): # als type vraag 'Aantal' is en Taxongroep is bekend kunnen we soortenlijst koppen aan multiple choice vraag
        tax_id = int(row['TaxongroepId'])
        answer_type = f"select_multiple taxa_{tax_id}"
        vraag_appearance = "horizontal compact"
    elif type_var == 'meting_perc':
        answer_type = "select_one Percentage" #to find example and implement joost
        vraag_appearance = "minimal"  
    else:
        answer_type = "text" # Fallback
        vraag_appearance = "minimal" 
        print(f"Waarschuwing: Onbekend AnalyseVariabele type '{type_var}' voor VoorwaardeID {row['VoorwaardeID']}. Fallback naar 'text' vraag.") 
    return answer_type, vraag_appearance    
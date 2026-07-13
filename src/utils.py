import re
import pandas as pd
import getpass
import shutil
from sys import platform
import subprocess
import os

import arcgis
import sqlite3
from pathlib import Path

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

def get_habitat_hint(habitattype_code, db_path: str):
    """
    Genereert een dynamische hint voor een habitattype, met vermelding
    van de parent-habitat indien deze bestaat.
    """
    # hardcode lookup habitattypes for now joost
    with sqlite3.connect(db_path) as conn:
        # We lezen alleen de specifieke rij die we nodig hebben, dat is veel sneller!
        query = "SELECT * FROM Habitattype WHERE Code = ?"
        df_habitattypes = pd.read_sql_query(
            query, conn, params=(str(habitattype_code),)
        )

    # Zoek het habitattype op basis van de Code
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
            lijn = f"• {ned_naam}" # (<i>{wet_naam}</i>)" removed scientific name from hint to reduce clutter
            
        species_lines.append(lijn)
        
    # Verbind alle lijnen met een HTML line-break
    return "<br>".join(species_lines)

def get_question_settings(row):
    type_var = str(row['schaal_type']).strip().lower()

    if type_var == 'lsvi':
        answer_type = "select_one LSVI"  # Verwijst naar de 'LSVI' lijst in survey123_schalen.csv
        vraag_appearance = "compact horizontal"  # Verticaal met radio buttons
    elif 'bedekking' in type_var:
        answer_type = "select_one Standaard"  # Verwijst naar de 'Standaard' lijst in survey123_schalen.csv
        vraag_appearance = "compact horizontal"  # Optioneel: maakt de opties naast elkaar in plaats van onder elkaar
    elif type_var == 'aantal' and pd.notna(row['TaxongroepId']): # als type vraag 'Aantal' is en Taxongroep is bekend kunnen we soortenlijst koppen aan multiple choice vraag
        tax_id = int(row['TaxongroepId'])
        answer_type = f"select_multiple taxa_{tax_id}"
        vraag_appearance = "horizontal compact"
    elif type_var == 'meting_perc':
        answer_type = "select_one Percentage" #to find example and implement joost
        vraag_appearance = "minimal" 
    elif 'meting' in type_var and type_var != 'meting_perc':
        answer_type = "decimal" #to find example and implement joost
        vraag_appearance = "minimal" 
    elif 'scoresom' in type_var and type_var != 'meting_perc':
        answer_type = "integer" #to find example and implement joost
        vraag_appearance = "minimal" 
    else:
        answer_type = "text" # Fallback
        vraag_appearance = "minimal" 
        print(f"Waarschuwing: Onbekend AnalyseVariabele type '{type_var}' voor VoorwaardeID {row['VoorwaardeID']}. Fallback naar 'text' vraag.") 
    return answer_type, vraag_appearance    

def get_survey_id_by_name(gis, survey_name: str) -> str:
    """Fetches the ID of a Survey123 survey by its title.

    Args:
        gis: The authenticated GIS connection object.
        survey_name: The exact title of the survey to find.

    Returns:
        str: The survey ID string.

    Raises:
        ValueError: If no survey matches the provided title.
    """
    # Initialize the Survey Manager
    survey_manager = arcgis.apps.survey123.SurveyManager(gis)
    surveys = survey_manager.surveys
    
    # Safely find matches using the .get() method
    matched_surveys = [s for s in surveys if s.properties.get('title') == survey_name]
    
    if matched_surveys:
        # Return the ID of the first matching survey found
        return matched_surveys[0].properties.get('id')
    
    # If nothing matches, gather available titles to provide a helpful error message
    available_titles = [s.properties.get('title') for s in surveys if s.properties.get('title')]
    print(f"Survey '{survey_name}' not found in the connected portal.\n")
    print(f"Available surveys: {available_titles}")
    return None

def browse_folders_for_survey(gis, old_survey_id: str) -> str:
    """Finds the name of the folder containing a specific survey by browsing item lists.

    Args:
        gis: The authenticated GIS connection object.
        old_survey_id: The unique ID of the survey form item.

    Returns:
        tuple: The name and ID of the folder where the survey resides, or ('Root', None) if not found in subfolders.
    """
    form_item = gis.content.get(old_survey_id)
    if not form_item:
        raise ValueError(f"Survey item with ID {old_survey_id} could not be found.")
        
    user = gis.users.get(form_item.owner)
    
    for f in user.folders:
        list = user.items(folder=f)
        for i in list:
            if i.id == old_survey_id:
                return f.name, f._folder_id
    return None, None

def voeg_lsvi_beschrijving_toe(
    df_vereisten: pd.DataFrame,
    sqlite_path: str,
    col_habitattype: str = "Habitattype",
    col_beoordeling_id: str = "BeoordelingID",
    col_taxongroep_id: str = "TaxongroepId",
) -> pd.DataFrame:
    """Voegt de LSVI-beschrijving toe aan de invoervereisten datatabel.

    Deze functie haalt de relevante beschrijvingen op uit de opgegeven
    SQLite-databank op basis van de combinatie van Habitattype (code),
    BeoordelingID en TaxongroepId. De beschrijving wordt toegevoegd als een
    nieuwe kolom 'Beschrijving'.

    Er wordt rekening gehouden met de volgende fallback-logica voor elke rij:
    - Als 'Beschrijving' ingevuld is, wordt deze gebruikt.
    - Als 'Beschrijving' leeg is, wordt 'Beschrijving_naSoorten' gebruikt.
    - Als 'Beschrijving_naSoorten' leeg is, wordt 'Beschrijving' gebruikt.
    - Als beide leeg zijn, blijft de waarde voor die rij leeg (None).

    Args:
        df_vereisten (pd.DataFrame): Het DataFrame met de invoervereisten (de
          vragenlijst).
        sqlite_path (str): Het bestandspad naar de LSVI SQLite-databank.
        col_habitattype (str, optional): De kolomnaam voor het habitattype in
          df_invoer. Defaults to 'Habitattype'.
        col_beoordeling_id (str, optional): De kolomnaam voor het BeoordelingID
          in df_invoer. Defaults to 'BeoordelingID'.
        col_taxongroep_id (str, optional): De kolomnaam voor het TaxongroepId in
          df_invoer. Defaults to 'TaxongroepId'.

    Returns:
        pd.DataFrame: Een nieuw DataFrame (kopie) inclusief de kolom
        'Beschrijving'.

    Raises:
        KeyError: Als een van de opgegeven kolomnamen niet bestaat in df_invoer.
    """
    # 1. Maak een kopie om het originele DataFrame niet ongewenst te wijzigen
    df = df_vereisten.copy()

    # Valideer of de gevraagde kolommen daadwerkelijk bestaan
    for col in [col_habitattype, col_beoordeling_id, col_taxongroep_id]:
        if col not in df.columns:
            raise KeyError(
                f"Kolom '{col}' werd niet gevonden in het invoer DataFrame."
            )

    # 3. Maak verbinding met de SQLite database en haal de volledige tabel op
    conn = sqlite3.connect(sqlite_path)

    query = """
    SELECT 
        ht.Code AS Habitatsubtype,
        b.Id AS BeoordelingID,
        IFNULL(ih.TaxongroepId, -1) AS TaxongroepId,
        ih.Beschrijving AS Beschrijving, 
        ih.Beschrijving_naSoorten AS Beschrijving_naSoorten
    FROM Indicator_habitat ih
    INNER JOIN Habitattype ht ON ih.HabitattypeId = ht.Id
    INNER JOIN Indicator_beoordeling ib ON ih.IndicatorId = ib.IndicatorID
    INNER JOIN Beoordeling b ON ib.Id = b.Indicator_beoordelingID
    WHERE 
        (LENGTH(ih.Beschrijving) > 0 OR LENGTH(ih.Beschrijving_naSoorten) > 0)
        AND
        ih.VersieId = 3
    """

    df_db = pd.read_sql_query(query, conn)
    conn.close()

    # 4. Schoon de database strings op en converteer types
    df_db["Habitatsubtype"] = (
        df_db["Habitatsubtype"].astype(str).str.strip()
    )
    df_db["BeoordelingID"] = df_db["BeoordelingID"].astype(int)
    df_db["TaxongroepId"] = df_db["TaxongroepId"].astype(int)

    for col_name in ["Beschrijving", "Beschrijving_naSoorten"]:
        # Strip whitespaces en zet echte lege strings ("") om naar None/NaN
        df_db[col_name] = df_db[col_name].astype(str).str.strip()
        df_db[col_name] = df_db[col_name].replace(
            r"^\s*$", None, regex=True
        )  # Vangt ook verborgen spaties op

    # 5. Pas de exacte fallback-logica toe via .fillna()
    # - Als DB_Beschrijving gevuld is -> kies DB_Beschrijving
    # - Als DB_Beschrijving leeg is -> kies DB_Beschrijving_naSoorten
    # - Als beide leeg zijn -> resultaat is None/NaN
    df_db["Beschrijving"] = df_db["Beschrijving"].fillna(
        df_db["Beschrijving_naSoorten"]
    )

    # 6. Breng de data samen middels een Left Join (merge)
    df_merged = pd.merge(
        df,
        df_db[
            [
                "Habitatsubtype",
                "BeoordelingID",
                "TaxongroepId",
                "Beschrijving",
            ]
        ],
        on=["Habitatsubtype", "BeoordelingID", "TaxongroepId"],
        how="left",
    )

    return df_merged

def delete_specific_survey(gis, survey_name: str):
    """
    Verwijdert een specifieke Survey123 survey en alle daaraan gekoppelde
    elementen uit ArcGIS Online middels een onafhankelijke 'Multi-Pass' strategie.
    
    Deze functie is 100% onafhankelijk van naam-suffixes (_form, _fieldworker).
    Het probeert herhaaldelijk items te wissen; zodra afhankelijke views in 
    ronde 1 verdwijnen, worden de hoofdlagen in ronde 2 automatisch vrijgegeven.
    """
    print(f"=== Start gerichte verwijdering voor survey: '{survey_name}' ===")

    # 1. Haal de unieke ID van het hoofdformulier op via de naam
    old_survey_id = get_survey_id_by_name(gis, survey_name)

    if not old_survey_id:
        print(f" [!] Geen survey gevonden met de naam '{survey_name}'. Annuleren.")
        return

    form_item = gis.content.get(old_survey_id)
    if not form_item:
        print(f" [!] Kon het item met ID {old_survey_id} niet ophalen.")
        return

    form_id = form_item.id
    user = gis.users.get(form_item.owner)

    # 2. Zoek de map waarin deze specifieke survey leeft
    folder_name, folder_id = browse_folders_for_survey(gis, old_survey_id)
    print(f"Survey bevindt zich in map: '{folder_name}'")

    # Haal ALLE items op uit deze map
    all_folder_items = user.items(folder=folder_name)

    # 3. Verzamel ALLE items die bij deze survey horen in één platte lijst
    items_to_delete = []
    
    for item in all_folder_items:
        is_target_item = (
            item.id == form_id or 
            item.title.lower().startswith(survey_name.lower()) or 
            form_id in item.title or
            (item.name and form_id in item.name)
        )
        if is_target_item:
            items_to_delete.append(item)

    if not items_to_delete:
        print(" -> Geen gekoppelde elementen gevonden om te verwijderen.")
        return

    print(f"Totaal aantal geïdentificeerde survey-items voor verwijdering: {len(items_to_delete)}")

    # 4. CRUCIAL: Hef EERST bij alle doelen de beveiliging op
    # Als we dit pas tijdens het verwijderen doen, kan een lock elders een valse dependency-fout triggeren
    print("Verwijder-beveiliging opheffen voor alle geselecteerde items...")
    for item in items_to_delete:
        try:
            item.protect(enable=False)
        except Exception:
            pass

    # 5. DE MULTI-PASS RETRY LOOP (De slimme motor)
    pass_number = 1
    max_passes = 4  # Meestal is alles in 2 passes al volledig weg
    
    while items_to_delete and pass_number <= max_passes:
        print(f"\n--- Start Verwijderronde {pass_number} ---")
        leftover_items = []
        deleted_any_this_pass = False

        for item in items_to_delete:
            try:
                # Poging tot verwijderen
                item.delete()
                print(f" [✓] Succesvol verwijderd: {item.title} ({item.type})")
                deleted_any_this_pass = True
            except Exception as e:
                # Als het faalt (bijv. Error 400 wegens gerelateerd item), bewaren we hem voor de volgende ronde
                leftover_items.append(item)

        # Update de hoofdlijst met de items die we moesten skippen
        items_to_delete = leftover_items

        # Veiligheidsklep: als een hele ronde niks heeft kunnen verwijderen,
        # zitten we vast op een échte harde fout (bijv. rechten) en moeten we stoppen om infinite loops te voorkomen.
        if not deleted_any_this_pass and items_to_delete:
            print("\n [!] Systeem zit vast: resterende items hebben permanente blokkades.")
            break

        pass_number += 1

    # 6. Eindrapportage
    print("\n=== Eindrapportage ===")
    if items_to_delete:
        print(f" [!] De volgende {len(items_to_delete)} items konden NIET worden verwijderd:")
        for item in items_to_delete:
            print(f"   - {item.title} ({item.type})")
    else:
        print(f" [✓] Voltooid: Alle elementen voor '{survey_name}' zijn succesvol opgeruimd. Map '{folder_name}' is behouden.")

def upload_survey(
    gis: arcgis.gis.GIS,
    xlsform_path: str | Path,
    target_folder: str = "Survey-LSVI App Test Auto",
    thumbnail_path: str = r"./inbo_logo.jpg",
) -> str | None:
    """Publiceert een enkel XLSForm als een Survey123-object naar ArcGIS Online.

    De functie controleert eerst of de doelmap al bestaat voor de ingelogde
    gebruiker en maakt deze aan indien nodig. De titel van de survey wordt
    automatisch afgeleid van de bestandsnaam (zonder de extensie).

    Args:
        gis (arcgis.gis.GIS): De actieve GIS-connectiepool.
        xlsform_path (str | Path): Het bestandspad naar het XLSX/XLSForm.
        target_folder (str, optional): De naam van de doelmap in ArcGIS Online.
          Defaults to "Survey-LSVI App Test Auto".
        thumbnail_path (str, optional): Het pad naar het inbo logo voor de
          miniatuurweergave. Defaults to r"../inbo_logo.jpg".

    Returns:
        str | None: De nieuwe ArcGIS Item ID van de gepubliceerde survey, of
        None als de publicatie is mislukt.
    """
    xlsform_path = Path(xlsform_path)

    # 1. Valideer of het bestand daadwerkelijk bestaat op schijf
    if not xlsform_path.exists():
        print(f" [!] Bestand niet gevonden: '{xlsform_path}'")
        return None

    # Automatisch de surveynaam afleiden van de bestandsnaam (zonder .xlsx)
    survey_title = xlsform_path.stem
    print(f"\n=== Start upload voor survey: '{survey_title}' ===")

    # 2. Initialiseer de Survey123 Manager
    survey_manager = arcgis.apps.survey123.SurveyManager(gis)

    # 3. Map-controle logic: Maak aan als deze nog niet bestaat
    user = gis.users.me
    bestaande_mappen = [folder.name for folder in user.folders]

    if target_folder not in bestaande_mappen:
        print(f"Map '{target_folder}' bestaat nog niet. Aanmaken...")
        try:
            gis.content.create_folder(folder=target_folder)
            print(f" [✓] Map '{target_folder}' succesvol aangemaakt.")
        except Exception as e:
            print(
                f" [!] Waarschuwing bij het aanmaken van map '{target_folder}': {e}"
            )
    else:
        # We houden de log stil als de map al bestaat (fijn voor in een loop)
        pass

    # Valideer de thumbnail locatie
    valid_thumbnail = (
        thumbnail_path if Path(thumbnail_path).exists() else None
    )

    # 4. Het daadwerkelijke creatie- en publicatieproces
    try:
        # A. Maak het Survey Draft object aan in de cloud map
        print(f" -> Concept aanmaken in map '{target_folder}'...")
        new_survey = survey_manager.create(
            title=survey_title,
            folder=target_folder,
            tags="LSVI, Survey123, Python",
            summary=f"Automatisch gegenereerde LSVI survey op basis van {xlsform_path.name}.",
            description=f"Deze survey is automatisch gepubliceerd via Python vanuit het bestand: {xlsform_path.name}.",
            thumbnail=valid_thumbnail,
        )

        # B. Publiceer het formulier (aanmaken van tabellen, views en feature services)
        print(
            f" -> Publiceren naar ArcGIS Online begonnen (dit kan even duren)..."
        )
        new_survey.publish(
            xlsform=str(xlsform_path),
            enable_delete_protection=False,  # Zorgt dat je delete-script de tabel kan overschrijven
            enable_sync=True,  # Cruciaal voor offline gebruik in de Survey123 veld-app
            thumbnail=valid_thumbnail,
            schema_changes=True,
        )

        # C. Haal de nieuwe unieke Item ID op ter verificatie
        new_survey_id = get_survey_id_by_name(gis, survey_title)
        print(f" [✓] Succesvol gepubliceerd! Item ID: {new_survey_id}")

        return new_survey_id

    except Exception as e:
        print(
            f" [!] Fout opgetreden bij het publiceren van '{survey_title}': {e}"
        )
        return None
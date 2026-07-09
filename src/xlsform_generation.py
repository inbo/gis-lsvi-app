import pandas as pd
import re
from typing import List
import numpy as np
import sqlite3
from datetime import datetime
import os
import sys
import argparse

# Get the absolute path of the folder above the notebook
parent_dir = os.path.abspath(os.path.join(os.getcwd(), "."))

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src import utils


def generate_xlsform(
        habitat_filter: List[str] = None, 
        output_file: str = './output/Survey123_Volledige_Generatie.xlsx',
        form_title: str = 'LSVI App Test'):
    """
    Generate XLSForm survey based on parameters
    """
    ### Load input data
    df_vereisten = pd.read_excel('./input/LSVI_packageInvoervereisten_uitdb_2026-06-08_aanvullingenLSVI_app.xlsx', sheet_name='LSVI_packageInvoervereisten_uit')
    # We should only use vereiesten v3
    df_vereisten = df_vereisten[df_vereisten['Versie'] == 'Versie 3']
    print(df_vereisten.shape)
    # Maak unieke ID aan voor vragen adhv voorwaarde id + habitattype
    df_vereisten['vraag_id'] = "vrg_" + df_vereisten['VoorwaardeID'].astype(str) + "_" + (df_vereisten['Habitatsubtype'].astype(str).apply(utils.clean_name))
    # Make sure vereisten ID (VoorwaardeID) is uniek
    df_vereisten.drop_duplicates(subset=['vraag_id'], inplace=True)

    # Type vraag/antwoord is combinatie van kolom Schaal en AnalyseVariabele
    # Coalesce kolom Schaal (prioritair) en AnalyseVariabele (fallback)
    df_vereisten['schaal_type'] = df_vereisten.apply(lambda row: row['Schaal'] if pd.notnull(row['Schaal']) else row['AnalyseVariabele'], axis=1)

    if len(df_vereisten[df_vereisten['schaal_type'].isnull()]) > 0:
        print("Er zijn vereisten zonder type vraag/antwoord. Controleer de invoervereisten!")
        print(df_vereisten[df_vereisten['schaal_type'].isnull()])

    # We filter on specific habitat types (start with 3,4 or 5) to keep survey sizeable
    # df_vereisten = df_vereisten[df_vereisten['Habitatsubtype'].astype(str).str.startswith(('1', '2','3', '4', '5'))]
    if habitat_filter is not None:
        df_vereisten = df_vereisten[df_vereisten['Habitatsubtype'].astype(str).str.startswith(tuple(habitat_filter))]

    print(df_vereisten.shape)

    print("Aantal unieke schaal in de vereisten:", df_vereisten['schaal_type'].unique())

    df_soorten = pd.read_csv('./input/invoervereistenUitTeWerkenSoortenlijst-UTF8.csv', sep=';')
    df_schalen = pd.read_csv('./input/survey123_schalen.csv', sep=';') # Het bestand van de vorige stap!

    # Groepen voor matrixvragen
    df_groepen = pd.read_excel('./input/LSVI_packageInvoervereisten_uitdb_2026-06-08_aanvullingenLSVI_app.xlsx', sheet_name='Groepen')
    # 2. Opschonen: Verwijder eventuele onzichtbare spaties aan de randen van de tekst
    df_groepen['Name'] = df_groepen['Name'].astype(str).str.strip()
    df_groepen['Value'] = df_groepen['Value'].astype(str).str.strip()
    groepen_mapping = df_groepen.groupby('Name')['Value'].apply(list).to_dict()

    # Habitattypes
    # df_habitattypes = pd.read_sql_table('Habitattype', 'sqlite:///./input/LSVIHabitatTypes.sqlite')

    ### Build choices
    print("Choices tabblad opbouwen...")
    choices_list = []

    # A. Schalen toevoegen
    for _, row in df_schalen.iterrows():
        choices_list.append(row.to_dict())

    # B. Dynamische Habitattype lijst genereren (Voor de eerste vraag)
    unieke_habitats = df_vereisten['Habitattype'].dropna().unique()
    for hab in unieke_habitats:
        choices_list.append({
            "list_name": "lijst_habitats",
            "name": utils.clean_name(hab),
            "label": str(hab).upper()
        })

    # C. Dynamische Soortenlijsten genereren (Groepeer per TaxongroepId)
    for _, soort in df_soorten.iterrows():
        if pd.notna(soort['TaxongroepId']):
            tax_id = int(soort['TaxongroepId'])
            choices_list.append({
                "list_name": f"taxa_{tax_id}",
                "name": utils.clean_name(soort['WetNaamKort']),
                "label": f"{soort['NedNaam']} ({soort['WetNaamKort']})" if pd.notna(soort['NedNaam']) else soort['WetNaamKort']
            })

    # Dynamische subhapitattypes toevoegen (Voor de BWK-vragen)
    unieke_subhabitats = df_vereisten['Habitatsubtype'].dropna().unique()
    for hab in unieke_subhabitats:
        choices_list.append({
            "list_name": "lijst_subhabitats",
            "name": utils.clean_name(hab),
            "label": str(hab).upper()
        })
        
    df_choices_final = pd.DataFrame(choices_list)

    # Zorg dat de talen overeenkomen in survey en choices!
    if 'label' in df_choices_final.columns:
        df_choices_final.rename(columns={'label': 'label::nl'}, inplace=True)


    ### Settings
    # Add settings dataframe
    last_part = '_'.join(habitat_filter)
    if not form_title:
        last_part2 = '-'.join(habitat_filter)
        form_title = f"LSVI App {last_part2}"
    df_settings = pd.DataFrame([{
        "form_id": f"lsvi_app_{last_part}",
        "form_title": form_title,
        "style": "pages",
        "default_language": "nl" 
    }])

    ###########################
    ### SURVEY CONSTRUCTION ###
    ###########################

    ### General info
    print("Survey tabblad opbouwen...")
    survey_list = []

    # Unieke ID: Wordt op de achtergrond gegenereerd (gebruiker ziet dit niet)
    survey_list.append({
        "type": "calculate", "name": "collectie_id", "label": "", 
        "calculation": "uuid()", "relevant": "", "appearance": "", "default": ""
    })

    # Datum & Uur: Automatisch ingevuld
    survey_list.append({
        "type": "date", "name": "datum", "label": "Datum", 
        "default": "today()", "relevant": "", "appearance": "", "calculation": ""
    })

    survey_list.append({
        "type": "time", "name": "uur", "label": "Uur", 
        "default": "now()", "relevant": "", "appearance": "", "calculation": ""
    })

    # Locatie: Onzichtbare GPS-bepaling
    survey_list.append({
        "type": "geopoint", "name": "locatie", "label": "Locatie", 
        "appearance": "hidden", "default": "", "relevant": "", "calculation": ""
    })

    # BWK questions
    # Toon BWK ID over hele breedte
    survey_list.append({
        "type": "integer", 
        "name": "bwk_id", 
        "label": "BWK ID", 
        "default": "", 
        "relevant": "", 
        "appearance": "",  # Neemt 5/5 kolommen in, dus over hele rij
        "calculation": "", 
        "readonly": "yes"
    })

    # Maak grid aan voor hab and phab velden weer te geven
    survey_list.append({
        "type": "begin group", 
        "name": "grp_fieldmaps_data", 
        "label": "Gegevens uit Field Maps (Controle)", 
        "relevant": "", 
        "appearance": "w2 fixed-grid"  # <-- Dit activeert het grid-systeem!
    })

    survey_list.append({
        "type": "note", 
        "name": "hdr_hab", 
        "label": "<b>Habitat Code</b>", 
        "relevant": "", 
        "appearance": "w1", 
        "calculation": ""
    })
    survey_list.append({
        "type": "note", 
        "name": "hdr_phab", 
        "label": "<b>Percentage (%)</b>", 
        "relevant": "", 
        "appearance": "w1", 
        "calculation": ""
    })


    # Toon HAB en PHAB in grid
    for i in range(1, 6):
        # Top row: Habitat Code (Breedte = w1)
        survey_list.append({
            "type": "text", 
            "name": f"hab{i}", 
            "label": "&nbsp;", #f"Hab. {i}", 
            "default": "", 
            "relevant": "", 
            "appearance": "w1",  # <-- Neem 1/2 kolommen in
            "calculation": "", 
            "readonly": "no" # Joost set to yes later on
        })

        # Bottom row: Percentage (Breedte = w1)
        survey_list.append({
            "type": "integer", 
            "name": f"phab{i}", 
            "label": "&nbsp;", #f"% Hab. {i}", 
            "default": "", 
            "relevant": "", 
            "appearance": "w1",  # <-- Neemt de andere helft van de ruimte in
            "calculation": "", 
            "readonly": "yes"
        })

    # 4. Sluit de grid groep netjes af
    survey_list.append({
        "type": "end group", "name": "", "label": "", "relevant": "", "appearance": ""
    })

    ### Questions per habitat
    # Trigger vraag
    survey_list.append({
        "type": "select_one Ja_Nee", "name": "lsvi_opstellen", "label": "LSVI Opstellen?", 
        "relevant": "", "appearance": "horizontal", "default": "", "calculation": ""
    })

    # Groepeer alle LSVI vragen zodat we de 'relevant' logica maar 1 keer hoeven te typen
    survey_list.append({
        "type": "begin group", "name": "grp_lsvi", "label": "LSVI Gegevens", 
        "relevant": "${lsvi_opstellen} = 'ja'", # Zichtbaar als vorige vraag 'ja' is
        "appearance": "field-list", "default": "", "calculation": ""
    })

    # Eerste hoofdvraag: Welk habitattype?
    survey_list.append({
        "type": "select_multiple lijst_subhabitats",
        "name": "habitat_keuze",
        "label": "Welk habitat(sub)type wil je inventariseren?",
        "relevant": "",  # Altijd zichtbaar
        "hint": "Eenvoudige tekst om feature te testen.",
        "guidance_hint": "Eenvoudige tekst om feature te testen.",
        "appearance": "horizontal", #blank defaults to radio buttons instead of "minimal autocomplete",
        "choice_filter": "string(name) = string(${hab1}) or string(name) = string(${hab2}) or string(name) = string(${hab3}) or string(name) = string(${hab4}) or string(name) = string(${hab5})" # This makes sure we only get to choose habitats that were mapped in BWK field app for this polygon.
    })



    # 4.2. Loop door de unieke habitattypes (Creëer "Pages" / Groups)
    for hab in unieke_subhabitats:
        hab_clean = utils.clean_name(hab)

        # Vragen per habitattype
        # Begin de groep voor dit specifieke habitattype. 
        # De "relevant" zorgt ervoor dat enkel de habitattypes uit BWK-kaart worden weergegeven in app.
        survey_list.append({
            "type": "begin group",
            "name": f"grp_habitat_{hab_clean}",
            "label": f"Habitat {hab_clean.upper()}",
            "hint": utils.get_habitat_hint(hab),
            # "guidance_hint": get_habitat_hint(hab),   # Dynamische hint genereren op basis van de habitattype code
            "relevant": f"selected(string(${{habitat_keuze}}), '{hab_clean}')",   # De groep erft de relevantie van het repeat blok. Dit mag leeg zijn als we repeats gebruiken.
            "appearance": "w1 compact field-list" # Zorgt dat het als 1 pagina toont in de app
        })

        # Filter de vereisten voor dít specifieke habitattype
        df_hab_vereisten = df_vereisten[df_vereisten['Habitatsubtype'] == hab]
        
        # 4.3. Genereer de vragen binnen dit habitattype
        for idx, row in df_hab_vereisten.iterrows():
            vraag_naam = f"{row['vraag_id']}"

            # Type_vraag heeft 3 mogelijkheden: Orig (normaal), Matrixvraag of 'niet nodig in app':
            if row['Type_vraag'].lower() == 'orig':
                # Do usual processing
                answer_type, vraag_appearance = utils.get_question_settings(row)

                # Vraag toevoegen
                # Label van de vraag is combinatie van Voorwaarde + Indicator + Beoordeling(en eventueel Eenheid)
                # Add soortenlijst als hint 
                survey_list.append({
                    "type": answer_type,
                    "name": vraag_naam,
                    "label": utils.get_question_label(row), # De vraag die de gebruiker ziet
                    "relevant": "",
                    "appearance": vraag_appearance
                })

            # Block below
            elif row['Type_vraag'].lower() == 'matrixvraag':
        
                # 1. Start subgroep voor matrix met de table-list layout
                survey_list.append({
                    "type": "begin group",
                    "name": f"{vraag_naam}_matrix",
                    "label": utils.get_question_label(row), # Genereert jouw mooie HTML label
                    "hint": "Scoor elk van de onderstaande onderdelen volgens de LSVI-schaal.",
                    "relevant": "",
                    "appearance": "table-list" # <-- GEWIJZIGD: Verander 'w2 grid-layout' naar 'table-list'
                })

                # Welke groep moeten we bevragen in matrix?
                groep_naam = str(row['Groepen']).strip().lower()
                items_te_scoren = []
                
                if 'sleutelsoorten' in groep_naam:
                    tax_id = row['TaxongroepId']
                    if pd.notna(tax_id):
                        df_sub_soorten = df_soorten[df_soorten['TaxongroepId'] == int(tax_id)]
                        items_te_scoren = df_sub_soorten['NedNaam'].fillna(df_sub_soorten['WetNaam']).tolist()
                else:
                    raw_groep = str(row['Groepen']).strip()
                    items_te_scoren = groepen_mapping.get(raw_groep, [])

                if not items_te_scoren:
                    print(f"Waarschuwing: Geen matrix items gevonden voor groep '{row['Groepen']}' bij vraag {vraag_naam}")

                # 2. Genereer de matrix rijen
                # Binnen een 'table-list' groep hoef je GEEN 'notes' toe te voegen voor de labels!
                for index, item in enumerate(items_te_scoren):
                    uniek_veld_name = f"{vraag_naam}_matrix_{index}"
                    uniek_veld_name = uniek_veld_name[0:27] # Beperkt tot 32 tekens max voor GIS/Excel kolommen

                    # GEWIJZIGD: Geen aparte 'note' meer toevoegen. 
                    # We voegen direct de 'select_one' vraag toe. Het label van deze vraag 
                    # wordt door Survey123 automatisch als de linker rijkop geplaatst.
                    survey_list.append({
                        "type": "select_one LSVI", # Zorg dat al deze vragen exact dezelfde keuzelijst delen!
                        "name": uniek_veld_name,
                        "label": f"{item.capitalize()}", # <-- GEWIJZIGD: De itemnaam is nu direct het label van de keuzevraag
                        "relevant": "",
                        "appearance": "" # <-- GEWIJZIGD: Verwijder 'minimal' en 'w1'. table-list regelt de styling.
                    })

                # 3. Sluit de matrix sub-groep netjes af
                survey_list.append({
                    "type": "end group", "name": "", "label": "", "relevant": "", "appearance": ""
                })
            
            # elif row['Type_vraag'].lower() == 'matrixvraag':
            #     # Moet iets doen voor alle groepen? Zie groep kolom? 
                
            #     # Start subgroep voor matrix met grid layout
            #     survey_list.append({
            #         "type": "begin group",
            #         "name": f"{vraag_naam}_matrix",
            #         "label": utils.get_question_label(row), # Genereert jouw mooie HTML label
            #         "hint": "Scoor elk van de onderstaande onderdelen volgens de LSVI-schaal.",
            #         "relevant": "",
            #         "appearance": "w2 grid-layout" # Activeert het 2-koloms rastersysteem
            #     })

            #     # Welke groep moeten we bevragen in matrix? Sleutelsoorten of andere categorie? 
            #     groep_naam = str(row['Groepen']).strip().lower()
            #     items_te_scoren = []
                
            #     if 'sleutelsoorten' in groep_naam:
            #         # CASE A: Haal de specifieke soorten op uit df_soorten op basis van TaxongroepId
            #         tax_id = row['TaxongroepId']
            #         if pd.notna(tax_id):
            #             df_sub_soorten = df_soorten[df_soorten['TaxongroepId'] == int(tax_id)]
            #             # Pak 'NedNaam', tenzij NaN, dan pak 'WetNaam'
            #             items_te_scoren = df_sub_soorten['NedNaam'].fillna(df_sub_soorten['WetNaam']).tolist()

            #     else:
            #         # CASE B: Haal de vaste categorieën op uit het tabblad 'Groepen' (de dictionary)
            #         raw_groep = str(row['Groepen']).strip()
            #         items_te_scoren = groepen_mapping.get(raw_groep, [])

            #     # Veiligheidscheck voor als er niets gevonden is
            #     if not items_te_scoren:
            #         print(f"Waarschuwing: Geen matrix items gevonden voor groep '{row['Groepen']}' bij vraag {vraag_naam}")

            #     # Genereer de rijen (Text + Dropdown paren) binnen het grid
            #     for index, item in enumerate(items_te_scoren):
            #         # We saneren de tekst handmatig naar kleine letters zonder vreemde tekens
            #         item_clean = re.sub(r'[^a-z0-9]', '', str(item).lower().strip())
            #         voorwaarde_clean = re.sub(r'[^a-z0-9]', '', str(row['VoorwaardeID']).lower().strip())
                    
            #         # SLIMME TRUC: Omdat jouw utils.clean_name strikt maximaal 2 delen (Deel1_Deel2) 
            #         # toestaat, bouwen we de veldnaam op als "v{VoorwaardeID}_{item}". 
            #         # Dit levert exact 2 delen op (bijv: v317_pionierstadium) wat perfect uniek is!
            #         uniek_veld_name = f"{vraag_naam}_matrix_{index}"
            #         uniek_veld_name = uniek_veld_name[0:27] # Beperkt tot 32 tekens

            #         # KOLOM 1 (Links): De naam van de soort of het stadium (w6 = 50% breedte)
            #         survey_list.append({
            #             "type": "note",
            #             "name": f"{uniek_veld_name}_note", # Beperkt tot 32 tekens
            #             "label": f"{item.capitalize()}",
            #             "relevant": "",
            #             "appearance": "w1" 
            #         })
                    
            #         # KOLOM 2 (Rechts): De LSVI Keuzelijst Dropdown (w6 = 50% breedte)
            #         survey_list.append({
            #             "type": "select_one LSVI",
            #             "name": uniek_veld_name,
            #             "label": "Score:", # Spatie verbergt het label visueel, maar voorkomt Connect fouten
            #             "relevant": "",
            #             "appearance": "minimal w1" # 'minimal' maakt er een dropdown van
            #         })

            #     # 4. Sluit de matrix sub-groep netjes af
            #     survey_list.append({
            #         "type": "end group", "name": "", "label": "", "relevant": "", "appearance": ""
            #     })


            else:
                # Skip question
                continue
            
        
            # Onder vraag wil je soms de soortenlijst weergeven.
            # Doen dit niet als hint of guidance_hint in de vraag, want niet inklapbaar of te weinig ruimte.
            # We maken een aparte groep aan (conditioneel) met soorten indien nodig.
            # Genereer de soortenlijst HTML
            if row["Soortenlijst weergeven in vraag"] == 1:
                html_soorten = utils.get_species_hint(row['TaxongroepId'], df_soorten)

                # Check of er een soortenlijst is om te tonen
                if pd.notna(html_soorten) and str(html_soorten).strip() != "":
                    # Start de in- en uitklapbare groep
                    survey_list.append({
                        "type": "begin group",
                        "name": f"grp_lijst_{vraag_naam}",
                        "label": "🔽 Bekijk soortenlijst", # Dit is de tekst op de klikbare balk
                        "hint": np.nan,
                        "guidance_hint": np.nan,
                        "relevant": "",
                        "appearance": "compact" # <--- Dit commando maakt hem standaard ingeklapt!
                    })

                    # Voeg de 'note' toe met jouw HTML-geformatteerde soortenlijst
                    survey_list.append({
                        "type": "note",
                        "name": f"note_{vraag_naam}",
                        "label": html_soorten, # We stoppen jouw HTML nu in de 'label' van de note
                        "hint": np.nan,
                        "guidance_hint": np.nan,
                        "relevant": "",
                        "appearance": "",
                        "bind::esri:fieldType": "null"
                    })

                    # Sluit de uitklapbare groep netjes af
                    survey_list.append({
                        "type": "end group",
                        "name": "", 
                        "label": np.nan, 
                        "hint": np.nan, 
                        "guidance_hint": np.nan,
                        "relevant": "", 
                        "appearance": ""
                    })

        # Sluit de groep (Pagina) af
        survey_list.append({
            "type": "end group",
            "name": "", "label": "", "relevant": "", "appearance": ""
        })

    # Sluit de LSVI Groep af
    survey_list.append({
        "type": "end group", "name": "", "label": "", 
        "relevant": "", "appearance": "", "default": "", "calculation": ""
    })

    df_survey_final = pd.DataFrame(survey_list)


    ### Export XLSForm
    # Vervang alle lege strings in de hint (en eventueel andere) kolommen door echte NaN waarden
    df_survey_final['hint'] = df_survey_final['hint'].replace("", np.nan)
    # df_survey_final['guidance_hint'] = df_survey_final['guidance_hint'].replace("", np.nan)

    # rename columns to add default language
    df_survey_final = df_survey_final.rename(columns={'label': 'label::nl', 'hint': 'hint::nl', 'guidance_hint': 'guidance_hint::nl'})

    print("Excel bestand genereren...")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_survey_final.to_excel(writer, sheet_name='survey', index=False)
        df_choices_final.to_excel(writer, sheet_name='choices', index=False)
        df_settings.to_excel(writer, sheet_name='settings', index=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate XLSForm survey')
    parser.add_argument('--habitat-filter', nargs='+', type=str, default=['1','2','3'], help='Habitat type to filter as a list of strings (default: [\'1\',\'2\',\'3\'])')
    parser.add_argument('--output-file', default='./output/Survey123_Volledige_Generatie.xlsx', help='Output file path')
    parser.add_argument('--form-title', default='LSVI App Test', help='Form title')
    
    args = parser.parse_args()
    
    generate_xlsform(
        habitat_filter=args.habitat_filter,
        output_file=args.output_file,
        form_title=args.form_title
    )
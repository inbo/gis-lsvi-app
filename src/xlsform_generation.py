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

SQLITE_PATH = "./input/LSVIHabitatTypes.sqlite"


def generate_xlsform(
        habitat_filter: List[str] = None, 
        output_file: str = './output/Survey123_Volledige_Generatie.xlsx',
        form_title: str = 'LSVI App Test'):
    """
    Generate XLSForm survey based on parameters
    """
    ### Load input data
    df_vereisten = pd.read_excel('./input/LSVI_packageInvoervereisten_uitdb_2026-06-08_aanvullingenLSVI_app.xlsx', sheet_name='LSVI_packageInvoervereisten_uit')
    df_vereisten["Habitattype"] = df_vereisten["Habitattype"].astype(str).str.strip()
    df_vereisten["BeoordelingID"] = df_vereisten["BeoordelingID"].astype(int)
    df_vereisten["TaxongroepId"] = df_vereisten["TaxongroepId"].fillna(-1).astype(int)
    # We should only use vereisten v3
    df_vereisten = df_vereisten[(df_vereisten['Versie'] == 'Versie 3') & df_vereisten['Type_vraag'].isin(['Orig', 'Matrixvraag'])]
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

    # Haal beschrijving op uit LSVI databank (mimic functie geefInfoHabitatfiche)
    df_vereisten = utils.voeg_lsvi_beschrijving_toe(df_vereisten, sqlite_path=SQLITE_PATH)

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
        df_choices_final.rename(columns={'label': 'label'}, inplace=True)


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
        "default_language": "Dutch (nl)"
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
        "type": "text", 
        "name": "bwk_plot_id", 
        "label": "Plot ID", 
        "default": "", 
        "relevant": "", 
        "appearance": "",  # Neemt 5/5 kolommen in, dus over hele rij
        "calculation": "", 
        "readonly": "yes"
    })

    survey_list.append({
        "type": "text", 
        "name": "bwk_globalid", 
        "label": "Global ID", 
        "default": "", 
        "relevant": "", 
        "appearance": "",  # Neemt 5/5 kolommen in, dus over hele rij
        "calculation": "", 
        "readonly": "yes"
    })

    survey_list.append({
        "type": "integer", 
        "name": "bwk_centroid_x", 
        "label": "BWK Centroid X", 
        "default": "", 
        "relevant": "", 
        "appearance": "hidden",  # Neemt 5/5 kolommen in, dus over hele rij
        "calculation": "", 
        "readonly": "yes"
    })

    survey_list.append({
        "type": "integer", 
        "name": "bwk_centroid_y", 
        "label": "BWK Centroid Y", 
        "default": "", 
        "relevant": "", 
        "appearance": "hidden",  # Neemt 5/5 kolommen in, dus over hele rij
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
        "calculation": "",
        "bind::esri:fieldType": "null"
    })
    survey_list.append({
        "type": "note", 
        "name": "hdr_phab", 
        "label": "<b>Percentage (%)</b>", 
        "relevant": "", 
        "appearance": "w1", 
        "calculation": "",
        "bind::esri:fieldType": "null"
    })

    # Toon HAB en PHAB in grid
    for i in range(1, 4):
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

    # ########################################
    # ### SAMPLE OF TABLE LIST MATRIX QUESTION JOOST TO REMOVE LATER
    # ########################################
    # # Add sample hardcoded table list matrixquestion so Toon en Johannes can test if width is enough
    # survey_list.append({
    #                 "type": "begin group",
    #                 "name": f"test_matrix",
    #                 "label": "Deze vraag dient enkel als voorbeeld van matrixgrid. Is er genoeg ruimte om het juiste antwoord aan te duiden?", # Genereert jouw mooie HTML label
    #                 "hint": np.nan,
    #                 "relevant": "",
    #                 "appearance": "table-list" # <-- GEWIJZIGD: Verander 'w2 grid-layout' naar 'table-list'
    #             })

    # # Welke groep moeten we bevragen in matrix?
    # groep_naam = 'lsvi'
    # items_te_scoren = []
    # tax_id = 1
    # if pd.notna(tax_id):
    #     df_sub_soorten = df_soorten[df_soorten['TaxongroepId'] == int(tax_id)]
    #     items_te_scoren = df_sub_soorten['NedNaam'].fillna(df_sub_soorten['WetNaam']).tolist()
                
    # # 2. Genereer de matrix rijen
    # # Binnen een 'table-list' groep hoef je GEEN 'notes' toe te voegen voor de labels!
    # for index, item in enumerate(items_te_scoren):
    #     uniek_veld_name = f"test_matrix_{index}"

    #     survey_list.append({
    #         "type": "select_one LSVI", # Zorg dat al deze vragen exact dezelfde keuzelijst delen!
    #         "name": uniek_veld_name,
    #         "label": f"{item.capitalize()}", 
    #         "relevant": "",
    #         "appearance": "" 
    #     })

    # # 3. Sluit de matrix sub-groep netjes af
    # survey_list.append({
    #     "type": "end group", "name": "", "label": "", "relevant": "", "appearance": ""
    # })

    # #########################################
    # ### END OF BLOCK TO DELETE LATER
    # ########################################

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
            # "hint": utils.get_habitat_hint(hab),
            "relevant": f"selected(string(${{habitat_keuze}}), '{hab_clean}')",   # De groep erft de relevantie van het repeat blok. Dit mag leeg zijn als we repeats gebruiken.
            "appearance": "field-list" # Zorgt dat het als 1 pagina toont in de app
        })

        # Filter de vereisten voor dít specifieke habitattype
        df_hab_vereisten = df_vereisten[df_vereisten['Habitatsubtype'] == hab]
        
        # 4.3. Genereer de vragen binnen dit habitattype
        for idx, row in df_hab_vereisten.iterrows():
            vraag_naam = f"{row['vraag_id']}"

            # # Add spacing after question
            # if idx > 0:
            #     survey_list.append({
            #         "type": "note",
            #         "name": f"div_{vraag_naam}",
            #         # 1. Outer DIV forces exactly 40px of padding above and below
            #         # 2. Inner DIV draws the 2px line right in the dead-center of that space
            #         # "label": "<div style='height: 1px; background-color: #31872e; margin: 20px 0; line-height: 0;'></div>",                # "label": "<div style='margin: 25px 0; padding-top: 15px; border-top: 2px solid #31872e; padding-bottom: 15px;'></div>",
            #         "label": "<div style='background-color: #31872e; height: 1px; font-size: 2px; padding: 0; margin: 3px 0; line-height: 1px;'>&nbsp;</div>",
            #         "relevant": "",
            #         "appearance": "",
            #         "bind::esri:fieldType": "null"
            #     })
            #     survey_list.append({
            #         "type": "note",
            #         "name": f"div_{vraag_naam}2",
            #         # 1. Outer DIV forces exactly 40px of padding above and below
            #         # 2. Inner DIV draws the 2px line right in the dead-center of that space
            #         "label": "<br>",                # "label": "<div style='margin: 25px 0; padding-top: 15px; border-top: 2px solid #31872e; padding-bottom: 15px;'></div>",
            #         "relevant": "",
            #         "appearance": "",
            #         "bind::esri:fieldType": "null"
            #     })

            # Type_vraag heeft 3 mogelijkheden: Orig (normaal), Matrixvraag of 'niet nodig in app':
            if row['Type_vraag'].lower() == 'orig':
                # Do usual processing
                answer_type, vraag_appearance = utils.get_question_settings(row)

                # Controleer of er een beschrijving is
                # heeft_beschrijving = pd.notna(row['Beschrijving']) and str(row['Beschrijving']).strip() != ""

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

                # Toevoegen beschrijving indicator
                if pd.notna(row['Beschrijving']) and str(row['Beschrijving']).strip() != "":
                
                    # Start de inklapbare groep
                    survey_list.append({
                        "type": "begin group",
                        "name": f"besch_{vraag_naam}",
                        "label": "ℹ️ Bekijk indicator beschrijving", # De tekst op de klikbare balk
                        "relevant": "",
                        "appearance": "compact"  # <--- Dit zorgt ervoor dat hij standaard ingeklapt is!
                    })

                    # Voeg de note toe met de VOLLEDIGE beschrijving
                    survey_list.append({
                        "type": "note",
                        "name": f"note_besch_{vraag_naam}",
                        "label": str(row['Beschrijving']).strip(), # De volledige, onafgekapte tekst
                        "relevant": "",
                        "appearance": "",
                        "bind::esri:fieldType": "null" # Zorgt ervoor dat dit geen lege GIS-kolom wordt
                    })

                    # Sluit de groep netjes af
                    survey_list.append({
                        "type": "end group", "name": "", "label": np.nan, "relevant": "", "appearance": ""
                    })

            elif row['Type_vraag'].lower() == 'matrixvraag':
                vraag_naam = f"{row['vraag_id']}"
                
                # 1. Start de matrix hoofdgroep met 'field-list' (verticale stapeling over 100% breedte)
                survey_list.append({
                    "type": "begin group",
                    "name": f"{vraag_naam}_matrix",
                    "label": utils.get_question_label(row), # Jouw mooie HTML hoofdlabel
                    "hint": "Scoor elk van de onderstaande onderdelen volgens de LSVI-schaal.",
                    "relevant": "",
                    "appearance": "field-list" # <-- GEWIJZIGD: field-list stapt af van het krappe grid
                })

                # 2. VOEG DE INKLAPBARE INDICATOR-BESCHRIJVING TOE (Bovenin de groep)
                if pd.notna(row['Beschrijving']) and str(row['Beschrijving']).strip() != "":
                    # Start de inklapbare subgroep
                    survey_list.append({
                        "type": "begin group",
                        "name": f"grp_besch_{vraag_naam}",
                        "label": "ℹ️ Bekijk indicator beschrijving", 
                        "relevant": "",
                        "appearance": "compact"  # Standaard netjes ingeklapt
                    })

                    # De note met de volledige tekst
                    survey_list.append({
                        "type": "note",
                        "name": f"note_besch_{vraag_naam}",
                        "label": str(row['Beschrijving']).strip(),
                        "relevant": "",
                        "appearance": "",
                        "bind::esri:fieldType": "null"
                    })

                    # Sluit de inklapbare subgroep
                    survey_list.append({
                        "type": "end group", "name": "", "label": "", "relevant": "", "appearance": ""
                    })

                # 3. Welke groep moeten we bevragen? (Sleutelsoorten of vaste mapping)
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

                # 4. Genereer de rijen over de VOLLEDIGE breedte van het scherm
                for index, item in enumerate(items_te_scoren):
                    uniek_veld_name = f"{vraag_naam}_matrix_{index}"
                    uniek_veld_name = uniek_veld_name[0:27] # Beperkt tot 32 tekens max

                    # OPLOSSING VOOR SMALLE SCHERMEN:
                    # - We verwijderen de aparte 'note' rij volledig.
                    # - De soortnaam/stadium-naam wordt DIRECT het 'label' van de select_one vraag.
                    # - We halen 'w1' weg. 'appearance: minimal' zorgt nu voor een dropdown
                    #   die de volle 100% breedte van het scherm gebruikt.
                    survey_list.append({
                        "type": "select_one LSVI",
                        "name": uniek_veld_name,
                        "label": f"{item.capitalize()}", # De soortnaam staat nu groot en leesbaar BOVEN de dropdown
                        "relevant": "",
                        "appearance": "minimal" # Volledige breedte dropdown, perfect voor mobiel
                    })

                # 5. Sluit de matrix hoofdgroep netjes af
                survey_list.append({
                    "type": "end group", "name": "", "label": "", "relevant": "", "appearance": ""
                })


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
                        "relevant": "",
                        "appearance": "compact" # <--- Dit commando maakt hem standaard ingeklapt!
                    })

                    # Voeg de 'note' toe met jouw HTML-geformatteerde soortenlijst
                    survey_list.append({
                        "type": "note",
                        "name": f"note_{vraag_naam}",
                        "label": html_soorten, # We stoppen jouw HTML nu in de 'label' van de note
                        "hint": np.nan,
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

    # Reduce choice list to values needed in the survey
    choice_list = df_survey_final['type'].str.extract(r'select_(?:one|multiple)\s+(.+)', expand=False)
    df_choices_final = df_choices_final[df_choices_final.list_name.isin(choice_list.unique())]

    # rename columns to add default language
    # df_survey_final = df_survey_final.rename(columns={'label': 'label::nl', 'hint': 'hint::nl', 'guidance_hint': 'guidance_hint::nl'})

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
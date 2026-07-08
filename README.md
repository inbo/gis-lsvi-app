## Requirements

### Create environment
Several python dependencies need to be installed to create the survey and export the data. 

1. Create the virtual python environment from arcgis pro python installation on citrix
```
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" -m venv .venv
```

2. Activate the environment
```
./.venv/Scripts/activate
```

3. Install dependencies using requirements.txt
```
pip install -r requirements.txt
```

## Workflow
### Survey aanpassen
1. Survey aanmaken/aanpassen: run notebook create_survey. Dit maakt een XLS form (als .xls) en overschrijft het bestaande bestand in de folder
```C:\Users\<<gebruiker>>\ArcGIS\My Survey Designs\LSVI App Test
```
2. Dit triggert automatisch een synchronisatie (zie knop 'actualiseren') in ArcGIS Survey123 Connect. Bijhorende bestanden worden aangepast (geopackage, xml bestanden, etc.). 
3. Indien geen fouten gevonden worden, kan de survey gepuliceerd worden (zie knop 'Publiceren'). Dit zal de bijhorende feature layers en form op ESRI portal overschrijven. Indien aanpassingen beperkt blijven kan bestaande data behouden worden. Bij grotere aanpassingen is het mogelijk dat alle data ook verwijderd zal worden uit de feature layer. Hiervoor krijgt de gebruiker eerst een waarschuwing.
4. Open de ArcGIS Survey123 app (laptop of smartphone), haal de nieuwste update van de survey op
5. Open field maps, kaart 'BWK Test'. Dit is een mock-up om interactie met BWK te testen. De nodige pop-up is geconfigureerd in de web map (zie portal).
6. Teken een polygoon of selecteer een bestaande polygoon. Onderaan de pop-up staat een link naar Survey123.
7. De vernieuwde survey zou automatisch moeten openen en neemt de habitats en bwk ID mee in de achtergrond.


Indien er iets misgaat bij het updaten/aanpassen van de survey zijn dit nuttige links:
- https://doc.arcgis.com/en/survey123/desktop/create-surveys/updatesurvey.htm
- https://doc.arcgis.com/en/survey123/desktop/create-surveys/troubleshootcreatesurveys.htm
- https://support.esri.com/en-us/knowledge-base/problem-unable-to-update-and-publish-surveys-from-arcgi-000025001

### Backups van resultaten (ETL)

Zie notebook etl_export_result_to_sqlite.
Connectie met AGOL Feature Layer wordt gemaakt op basis van:
- url
- username
- password
- feature layer item id

De feature layer wordt volledig uitgelezen en op meer genormaliseerde wijze opgeslagen als sqlite databank in de output folder. 
Dit toont enkel het concept, verdere verfijning nodig.
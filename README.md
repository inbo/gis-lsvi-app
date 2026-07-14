# LSVI App Testing - Survey123 Pipeline

Automated pipeline to convert LSVI (Lokale Staat Van Instanthouding) habitat assessment data into ArcGIS Survey123 surveys and publish them to AGOL.

## Overview

This project implements a data transformation pipeline:

```
LSVI Requirements Data (Excel/CSV)
         ↓
    XLSForm Generation
         ↓
    XLS Files (Survey123 format)
         ↓
    Publish/Update to AGOL
         ↓
    Survey123 App & Field Maps
```

## Project Structure

```
src/
  ├── xlsform_generation.py    # Converts LSVI requirements to XLSForm
  ├── publish_survey.py         # Publishes new surveys to AGOL
  ├── update_survey.py          # Updates existing surveys in AGOL
  └── utils.py                  # Shared utilities (KeePass auth, data cleaning)

input/                           # Data sources
  ├── LSVI_packageInvoervereisten_uitdb_*.xlsx  # Main LSVI requirements (invoervereisten)
  ├── LSVIHabitatTypes.sqlite   # Copy of sqlite database from LSVI R package for lookups
  ├── survey123_schalen.csv     # Answer scales/options
  ├── invoervereistenUitTeWerkenSoortenlijst-UTF8.csv  # Species list
  └── bwk_karteringseenheden.csv # BWK mapping units, but not relevant anymore

output/                          # Generated artifacts
  ├── xlsform_hab1-4.xlsx       # Survey for habitat types 1-4
  ├── xlsform_hab5-7.xlsx       # Survey for habitat types 5-7
  └── xlsform_hab9.xlsx         # Survey for habitat type 9
```

## Requirements

- **Anaconda Python Environment**: `python-gis` (shared across projects)
- **Python Libraries**: See `requirements.txt`
  - `arcgis` (ArcGIS Python API)
  - `pandas` (data manipulation)
  - `openpyxl` (Excel handling)
  - `sqlalchemy` (database access)
- **KeePass**: Local KeePassXC installation with stored AGOL credentials

## Setup

### 1. Anaconda Environment

Recreate the environment from the included environment.yml file:
```
conda env create -f environment.yml
conda activate python-gis
```

Ensure you have the `python-gis` environment activated:

```bash
conda activate python-gis
```

### 2. AGOL Credentials

Credentials are securely retrieved from KeePassXC:
- **Database**: `G:\Mijn Drive\keepass_db.kdbx`
- **Entry Title**: `AGOL`
- **Portal**: `https://gisservices.inbo.be/portal`

The pipeline will prompt for your KeePass master password when executing publish/update operations.

## Workflow

Make sure to run from anaconda prompt.
Navigate: cd /d Q:\Projects\PRJ_GIS\lsvi-app-testing

### Step 1: Generate XLSForm from LSVI Data

```bash
run_xlsform_generation.bat
```

**What it does:**
- Reads LSVI requirements from Excel (`input/LSVI_packageInvoervereisten_*.xlsx`)
- Adds habitat descriptions from SQLite database
- Automatically groups questions and organizes layout
- Generates 3 separate surveys by habitat type filter
- Outputs: `output/xlsform_hab*.xlsx`

The process handles:
- Question grouping and hierarchical organization
- Dynamic choice lists (species, habitat types, scales)
- Descriptions under questions (from LSVI database)
- Survey123-compatible ODK/XLSForm structure

### Step 2: Publish Surveys to AGOL (New Surveys)

```bash
run_upload_survey.bat
```

**What it does:**
- Deletes existing surveys with matching names from AGOL
- Publishes new XLSForm files as Survey123 surveys
- Uploads to AGOL folder: `Survey-LSVI App Test Auto`
- Creates Feature Layer for data collection
- Requires KeePass authentication

**Use this for:** First-time publication or complete regeneration

### Step 3: Update Surveys in AGOL (Existing Surveys)

```bash
run_update_survey.bat
```

**What it does:**
- Updates existing Survey123 surveys with new XLSForm definitions
- Preserves existing survey configuration and data
- Updates Field Map web map links (popups) to point to updated surveys
- Target webmap: `64c1f0bd02344d5ebf41c3dd320615bc`
- Requires KeePass authentication

**Use this for:** Frequent updates without losing collected data

## Pipeline Scripts

### `xlsform_generation.py`

Converts LSVI requirements into XLSForm:

```bash
python src/xlsform_generation.py \
  --habitat-filter 1 2 3 4 \
  --output-file output/xlsform_hab1-4.xlsx \
  --form-title "LSVI Habitat 1-4"
```

**Inputs:**
- LSVI requirements Excel file
- Habitat filters (numeric codes)
- Survey title

**Outputs:**
- XLSForm Excel file compatible with Survey123

### `publish_survey.py`

Publishes XLSForm as new Survey123:

```bash
python src/publish_survey.py \
  --xlsform-path output/xlsform_hab1-4.xlsx \
  --target-folder "Survey-LSVI App Test Auto"
```

### `update_survey.py`

Updates existing Survey123 with new XLSForm:

```bash
python src/update_survey.py \
  --xlsform output/xlsform_hab1-4.xlsx \
  --webmap-id 64c1f0bd02344d5ebf41c3dd320615bc
```

## Data Flow

1. **Input**: LSVI requirements from external R package export (Excel/CSV)
2. **Transform**: Python pipeline groups, cleans, and structures for Survey123
3. **Generate**: Creates ODK-compliant XLSForm files
4. **Publish**: Uploads to AGOL Survey123 and creates Feature Layers
5. **Deploy**: Survey123 app and Field Maps integrate with data
6. **Export** (optional): Results can be exported to SQLite (see notebooks)

## Key Features

- **Automated**: Full pipeline from data source to live surveys
- **Modular Surveys**: Three habitat-type-specific surveys generated separately, to reduce loading time in app.
- **Dynamic Content**: Species lists and choice options auto-populated from databases
- **Multi-step Publishing**: Supports both new publication and update workflows
- **Security**: Credentials stored in KeePass, never in code

## Troubleshooting

- **KeePass Prompt**: If credentials fail, ensure KeePassXC is installed and the entry exists
- **File Not Found**: Verify input data files exist in `input/` folder

## References

- ArcGIS Survey123: https://doc.arcgis.com/en/survey123/
- XLSForm Standard: https://xlsform.org/
- LSVI Documentation: https://github.com/inbo/LSVI/tree/main

## Next steps

- ETL survey results to DB
- Decouple results in AGOL feature layer to normalized DB model
- 
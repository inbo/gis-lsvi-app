WITH RECURSIVE ResolvedVoorwaarden AS (
    -- 1. ANCHOR: Start vanaf de hoofdvoorwaarden die gekoppeld zijn aan een BeoordelingId
    SELECT 
        BeoordelingId,
        Id AS CV_Id,
        VoorwaardeID1,
        VoorwaardeID2,
        ChildID1,
        ChildID2
    FROM CombinerenVoorwaarden
    WHERE BeoordelingId IS NOT NULL
    
    UNION ALL
    
    -- 2. RECURSIVE: Daal af in de boom via ChildID1 of ChildID2
    SELECT 
        r.BeoordelingId,
        cv.Id AS CV_Id,
        cv.VoorwaardeID1,
        cv.VoorwaardeID2,
        cv.ChildID1,
        cv.ChildID2
    FROM ResolvedVoorwaarden r
    INNER JOIN CombinerenVoorwaarden cv 
        ON cv.Id = r.ChildID1 OR cv.Id = r.ChildID2
),

FlatVoorwaarden AS (
    -- 3. Breng alle BeoordelingId's en unieke VoorwaardeId's samen
    SELECT BeoordelingId, VoorwaardeID1 AS VoorwaardeID FROM ResolvedVoorwaarden WHERE VoorwaardeID1 IS NOT NULL
    UNION
    SELECT BeoordelingId, VoorwaardeID2 AS VoorwaardeID FROM ResolvedVoorwaarden WHERE VoorwaardeID2 IS NOT NULL
),

GroupedLijstItems AS (
    -- 4. Groepeer keuzelijst-opties (Invoerwaarden) tot één string (Weergave = 'basis')
    SELECT 
        LijstId,
        GROUP_CONCAT(Waarde, ', ') AS Invoerwaarden
    FROM LijstItem
    GROUP BY LijstId
)

-- 5. Hoofdselectie met de self-join voor Habitattype hiërarchie
SELECT 
    ver.VersieLSVI AS Versie,
    COALESCE(parent.Code, ht.Code) AS Habitattype,  -- Als het een subtype is, pak de code van de parent
    ht.Code AS Habitatsubtype,                     -- De specifieke subtype code (bijv. 1310_pol)
    c.Naam AS Criterium,
    i.Naam AS Indicator,
    b.Beoordeling_letterlijk AS Beoordeling,
    b.Kwaliteitsniveau,
    ib.Belang,
    b.Id AS BeoordelingID,
    v.Id AS VoorwaardeID,
    v.VoorwaardeNaam AS Voorwaarde,
    v.Referentiewaarde,
    v.Operator,
    v.Maximumwaarde,
    av.VariabeleNaam AS AnalyseVariabele,
    av.Eenheid,
    tv.Naam AS TypeVariabele,
    gli.Invoerwaarden AS Invoerwaarde,
    v.TaxongroepId,
    tg.Omschrijving AS TaxongroepNaam

FROM FlatVoorwaarden fv
INNER JOIN Beoordeling b ON fv.BeoordelingId = b.Id
INNER JOIN Indicator_beoordeling ib ON b.Indicator_beoordelingId = ib.Id
INNER JOIN Indicator i ON ib.IndicatorId = i.Id
INNER JOIN Criterium c ON i.CriteriumId = c.Id

-- De hiërarchische self-join koppeling voor Habitattype
INNER JOIN Habitattype ht ON ib.HabitattypeId = ht.Id
LEFT JOIN Habitattype parent ON ht.ParentId = parent.Id
INNER JOIN Versie ver ON ib.VersieId = ver.Id

-- Koppeling naar meetcondities (Voorwaarden)
INNER JOIN Voorwaarde v ON fv.VoorwaardeID = v.Id
LEFT JOIN AnalyseVariabele av ON v.AnalyseVariabeleID = av.Id
LEFT JOIN TypeVariabele tv ON av.TypeVariabeleId = tv.Id
LEFT JOIN GroupedLijstItems gli ON v.InvoermaskerId = gli.LijstId
LEFT JOIN Taxongroep tg ON v.TaxongroepId = tg.Id

-- Filter op basis van de hoofd-habitattype code (haalt automatisch subtypes mee!)
WHERE COALESCE(parent.Code, ht.Code) = '1310'
  AND ver.VersieLSVI = 'Versie 3'
ORDER BY Habitatsubtype, Criterium, Indicator, BeoordelingID, VoorwaardeID;
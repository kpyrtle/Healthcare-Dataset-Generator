-- =============================================================================
-- setup_constraints.sql
	-- Run once in SSMS after loading the tables via make load-sql.
	-- Adds primary keys, foreign keys, and indexes to the healthcare database.

-- Why this matters:
	--   pandas to_sql() loads data but creates no keys or indexes. Without them,
	--   every JOIN does a full table scan and the schema has no defined relationships.
-- =============================================================================

USE healthcare;
GO

-- =============================================================================
-- STEP 1: Fix column types
-- pandas loads all string columns as varchar(max), which cannot be used as
-- primary keys, foreign keys, or index key columns in SQL Server.
-- =============================================================================

ALTER TABLE dbo.patients
    ALTER COLUMN research_id VARCHAR(12) NOT NULL;
GO

ALTER TABLE dbo.encounters
    ALTER COLUMN research_id VARCHAR(12) NOT NULL;
GO

ALTER TABLE dbo.ed_utilization
    ALTER COLUMN research_id VARCHAR(12) NOT NULL;
GO

-- encounter_id is a nullable bigint after pandas load; PKs must be NOT NULL
ALTER TABLE dbo.encounters
    ALTER COLUMN encounter_id BIGINT NOT NULL;
GO

-- department and insurance_type are short categoricals loaded as varchar(max)
ALTER TABLE dbo.encounters
    ALTER COLUMN department VARCHAR(50) NOT NULL;
GO

ALTER TABLE dbo.encounters
    ALTER COLUMN insurance_type VARCHAR(50) NOT NULL;
GO
-- =============================================================================
-- STEP 2: Primary Keys
-- =============================================================================

-- One row per patient
ALTER TABLE dbo.patients
    ADD CONSTRAINT PK_patients PRIMARY KEY (research_id);
GO

ALTER TABLE dbo.encounters
    ADD CONSTRAINT PK_encounters PRIMARY KEY (encounter_id);
GO

-- One row per encounter
ALTER TABLE dbo.encounters
    ALTER COLUMN encounter_id BIGINT NOT NULL;
GO

-- =============================================================================
-- STEP 3: Foreign Keys
-- All clinical tables hang off encounters via encounter_id.
-- encounters links to patients via research_id.
-- =============================================================================

ALTER TABLE dbo.encounters
    ADD CONSTRAINT FK_encounters_patients
    FOREIGN KEY (research_id) REFERENCES dbo.patients (research_id);
GO

ALTER TABLE dbo.vitals
    ADD CONSTRAINT FK_vitals_encounters
    FOREIGN KEY (encounter_id) REFERENCES dbo.encounters (encounter_id);
GO

ALTER TABLE dbo.lab_results
    ADD CONSTRAINT FK_lab_results_encounters
    FOREIGN KEY (encounter_id) REFERENCES dbo.encounters (encounter_id);
GO

ALTER TABLE dbo.encounter_outcomes
    ADD CONSTRAINT FK_encounter_outcomes_encounters
    FOREIGN KEY (encounter_id) REFERENCES dbo.encounters (encounter_id);
GO

ALTER TABLE dbo.ed_utilization
    ADD CONSTRAINT FK_ed_utilization_encounters
    FOREIGN KEY (encounter_id) REFERENCES dbo.encounters (encounter_id);
GO

ALTER TABLE dbo.ed_utilization
    ADD CONSTRAINT FK_ed_utilization_patients
    FOREIGN KEY (research_id) REFERENCES dbo.patients (research_id);
GO

-- =============================================================================
-- STEP 4: Indexes
-- The PK columns get indexes automatically. These cover the most common
-- join and filter patterns in readmission analysis.
-- =============================================================================

-- Patient-level lookups and joins from encounters ? patients
CREATE NONCLUSTERED INDEX IX_encounters_research_id
    ON dbo.encounters (research_id);
GO

-- Filtering encounters by date range (very common in time-series analysis)
CREATE NONCLUSTERED INDEX IX_encounters_admit_date
    ON dbo.encounters (admit_date);
GO

-- Filtering and grouping by department and insurance (readmission rate by X)
CREATE NONCLUSTERED INDEX IX_encounters_department
    ON dbo.encounters (department);
GO

CREATE NONCLUSTERED INDEX IX_encounters_insurance_type
    ON dbo.encounters (insurance_type);
GO

-- Filtering outcomes table by readmission flag (most common outcome query)
CREATE NONCLUSTERED INDEX IX_encounter_outcomes_readmitted
    ON dbo.encounter_outcomes (readmitted_30day);
GO

-- =============================================================================
-- STEP 5: Verify
-- Run these after the script completes to confirm everything was created.
-- =============================================================================

-- Check primary and foreign keys
SELECT
    tc.TABLE_NAME,
    tc.CONSTRAINT_TYPE,
    tc.CONSTRAINT_NAME,
    kcu.COLUMN_NAME
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
    ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
WHERE tc.CONSTRAINT_TYPE IN ('PRIMARY KEY', 'FOREIGN KEY')
ORDER BY tc.TABLE_NAME, tc.CONSTRAINT_TYPE;
GO

-- Check indexes
SELECT
    t.name AS table_name,
    i.name AS index_name,
    i.type_desc,
    STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns
FROM sys.indexes i
JOIN sys.tables t ON i.object_id = t.object_id
JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE t.schema_id = SCHEMA_ID('dbo')
  AND i.name IS NOT NULL
GROUP BY t.name, i.name, i.type_desc
ORDER BY t.name, i.name;
GO

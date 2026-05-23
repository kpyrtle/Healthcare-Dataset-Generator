-- 1. Overall Readmisson Rate by Dept and Insurance
SELECT
    e.department,
    e.insurance_type,
    COUNT(*) AS total_encounters,
    SUM(eo.readmitted_30day) AS total_readmissions,
    ROUND(CAST(100.0 * SUM(eo.readmitted_30day) AS FLOAT) / COUNT(*), 2) AS readmission_rate_pct
FROM dbo.encounters e
JOIN dbo.encounter_outcomes eo
    ON e.encounter_id = eo.encounter_id
GROUP BY
    e.department,
    e.insurance_type
HAVING COUNT(*) >= 500
ORDER BY
    readmission_rate_pct DESC;
-- FINDINGS:
	-- Uninsured patients have the highest readmission rates (22-26%), appearing in 12 of the top 15 results across multiple departments.
	-- Medicaid patients follow closely (19-23%), while Medicare and Private insurance show lower rates (15-19%).
	-- Overall gap between highest and lowest rate is roughly 7-8 percentage points.
	-- Pediatrics consistently shows the lowest rates across all insurance types.
	-- HAVING filter set to 500+ encounters to exclude unreliable small sample groups.


-- 2. Demographics and Clinical Comparison
SELECT
    eo.readmitted_30day,
    COUNT(*) AS patient_count,

    -- Demographics
   ROUND(AVG(e.age), 1) AS avg_age,
   ROUND(CAST(100.0 * SUM(CASE WHEN p.gender = 'Male' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*), 1) AS pct_male,

    -- Encounter characteristics
    ROUND(AVG(e.length_of_stay_days), 1) AS avg_los_days,
    ROUND(AVG(e.total_charges_usd), 0) AS avg_charges_usd,
    ROUND(AVG(e.patient_satisfaction_score), 2) AS avg_satisfaction,

    -- Key labs at time of encounter
    ROUND(AVG(lr.creatinine_mg_dl), 2) AS avg_creatinine,
    ROUND(AVG(lr.hba1c_pct), 2) AS avg_hba1c,
    ROUND(AVG(lr.glucose_mg_dl), 1) AS avg_glucose,

    -- Vitals
    ROUND(AVG(v.bmi), 1) AS avg_bmi,
    ROUND(AVG(v.o2_saturation_pct), 1) AS avg_o2_sat

FROM dbo.encounter_outcomes eo
JOIN dbo.encounters e
    ON eo.encounter_id = e.encounter_id
JOIN dbo.patients p
    ON e.research_id = p.research_id
LEFT JOIN dbo.lab_results lr
    ON e.encounter_id = lr.encounter_id
LEFT JOIN dbo.vitals v
    ON e.encounter_id = v.encounter_id
GROUP BY
    eo.readmitted_30day
ORDER BY
    eo.readmitted_30day;
-- FINDINGS:
	-- Overall readmission rate is approximately 18% (98,024 of 554,235 encounters).
	-- Readmitted patients are slightly older (63 vs 61) and have longer stays (6 vs 5 days).
	-- Creatinine is the most notable lab difference (1.34 vs 1.23), with readmitted patients showing worse kidney function on average.
	-- Average charges are ~$3,300 higher for readmitted patients ($83,429 vs $80,117).
	-- Gender, satisfaction, glucose, BMI, and O2 sat show little to no difference between groups.


-- 3. Prior ED use as a predictor
SELECT
    eu.ed_visits_past_6mo,
    COUNT(*) AS total_encounters,
    SUM(eo.readmitted_30day) AS readmissions,
    ROUND(CAST(100.0 * SUM(eo.readmitted_30day) AS FLOAT) / COUNT(*), 2) AS readmission_rate_pct
FROM dbo.ed_utilization eu
JOIN dbo.encounters e
    ON eu.encounter_id = e.encounter_id
JOIN dbo.encounter_outcomes eo
    ON e.encounter_id = eo.encounter_id
GROUP BY
    eu.ed_visits_past_6mo
ORDER BY
    eu.ed_visits_past_6mo;
-- FINDINGS:
-- Readmission rate increases steadily with each additional prior ED visit.
	-- 0 visits: 16.94% | 6 visits: 23.74% | 7 visits: 24.00%
	-- Roughly a 7 percentage point gap between lowest and highest reliable groups.
	-- Pattern holds consistently across rows 1-8 with large enough sample sizes.
-- Rows 9-10 (8-9 prior visits) have very small samples (21 and 1 encounter) and show irregular rates, which is not reliable for interpretation.
-- Prior ED utilization appears to be a meaningful predictor of readmission risk.


-- High-Risk Patient Profile
WITH risk_flags AS (
    SELECT
        e.encounter_id,
        e.department,
        e.age,
        e.length_of_stay_days,
        e.discharge_disposition,
        eo.readmitted_30day,

        CASE WHEN e.length_of_stay_days >= 7   THEN 1 ELSE 0 END AS flag_long_stay,
        CASE WHEN eu.ed_visits_past_6mo >= 3   THEN 1 ELSE 0 END AS flag_high_ed_use,
        CASE WHEN lr.creatinine_mg_dl >= 2.0   THEN 1 ELSE 0 END AS flag_high_creatinine,
        CASE WHEN lr.hba1c_pct >= 8.0          THEN 1 ELSE 0 END AS flag_poor_diabetes_control,
        CASE WHEN v.o2_saturation_pct < 92     THEN 1 ELSE 0 END AS flag_low_o2,
        CASE WHEN e.age >= 65                  THEN 1 ELSE 0 END AS flag_elderly

    FROM dbo.encounters e
    JOIN dbo.encounter_outcomes eo
        ON e.encounter_id = eo.encounter_id
    LEFT JOIN dbo.ed_utilization eu
        ON e.encounter_id = eu.encounter_id
    LEFT JOIN dbo.lab_results lr
        ON e.encounter_id = lr.encounter_id
    LEFT JOIN dbo.vitals v
        ON e.encounter_id = v.encounter_id
),

	scored AS (
		SELECT
			*,
			(flag_long_stay + flag_high_ed_use + flag_high_creatinine
			 + flag_poor_diabetes_control + flag_low_o2 + flag_elderly) AS risk_score
		FROM risk_flags
)

SELECT
    risk_score,
    COUNT(*) AS total_encounters,
    SUM(readmitted_30day) AS readmissions,
    ROUND(CAST(100.0 * SUM(readmitted_30day) AS FLOAT) / COUNT(*), 2) AS readmission_rate_pct
FROM scored
GROUP BY
    risk_score
ORDER BY
    risk_score;
-- FINDINGS:
	-- Readmission rate increases with every additional risk factor present.
	-- Score 0: 14.34% | Score 4: 28.41% | Score 5: 42.11%
		-- Patients with 4+ risk factors are readmitted at roughly twice the rate of patients with none.
		-- The jump from score 4 to score 5 is the largest single increase (~14 points).
		-- Score 5 only has 19 encounters, which is directionally correct but I'm treating it with caution.
	-- No patients triggered all 6 flags simultaneously (no score of 6 in results).
		-- This risk score could realistically be used at admission to flag high-risk patients for additional discharge planning or care coordination.
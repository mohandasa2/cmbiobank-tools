SELECT DISTINCT
    specimen_transmittal.Subject AS 'participant ID',
    specimen_transmittal.SPECID AS 'Specimen ID',
    specimen_transmittal.Site,
    enrollment.CTEP_SDC_MED_V10_CD AS 'Disease type',

    CASE
        WHEN specimen_transmittal.ASMTTPT_DRV = 'Baseline (Fresh)' THEN 'Baseline'
        WHEN specimen_transmittal.ASMTTPT_DRV = 'Progression (Fresh)' THEN 'Progression'
        ELSE specimen_transmittal.ASMTTPT_DRV
    END AS 'Assessment timepoint',

    specimen_transmittal.SPECCAT AS 'Specimen category',

    specimen_transmittal.BEDAT_RAW AS 'Specimen Collection Date',

    enrollment.DSSTDAT_ENROLLMENT_RAW AS 'Enrollment Date',

    DATEDIFF(
        STR_TO_DATE(
            TRIM(specimen_transmittal.BEDAT_RAW),
            '%d %b %Y'
        ),
        STR_TO_DATE(
            TRIM(enrollment.DSSTDAT_ENROLLMENT_RAW),
            '%d %b %Y'
        )
    ) AS 'Specimen collection event (days from enrollment)'

FROM ravedata.specimen_transmittal

JOIN enrollment
    ON specimen_transmittal.Subject = enrollment.Subject

WHERE specimen_transmittal.RecordActive = 1
  AND enrollment.RecordActive = 1;
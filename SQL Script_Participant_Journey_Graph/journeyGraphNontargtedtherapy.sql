SELECT 
    DISTINCT prior__therapy_supplement.Subject,
    CMCAT AS 'Non Targeted Therapy',
    CMSTDAT_RAW AS 'Start Date',
    CMENDAT_RAW AS 'End Date',
    DSSTDAT_ENROLLMENT_RAW AS 'Enrollment Date',
    BESTRESP AS 'Best Response',
    RSDAT1_RAW AS 'Date of assessment',

    DATEDIFF(
        STR_TO_DATE(TRIM(CMSTDAT_RAW), '%d %b %Y'),
        STR_TO_DATE(TRIM(DSSTDAT_ENROLLMENT_RAW), '%d %b %Y')
    ) AS 'N-startDate from enrollment',

    DATEDIFF(
        STR_TO_DATE(TRIM(CMENDAT_RAW), '%d %b %Y'),
        STR_TO_DATE(TRIM(DSSTDAT_ENROLLMENT_RAW), '%d %b %Y')
    ) AS 'N-endDate from enrollment'

FROM ravedata.prior__therapy_supplement

JOIN ravedata.enrollment
    ON prior__therapy_supplement.Subject = enrollment.Subject

WHERE prior__therapy_supplement.RecordActive = 1
  AND CMCAT IS NOT NULL


UNION ALL


SELECT 
    DISTINCT prior__radiation_supplement.Subject,
    'radiation' AS CMCAT,
    PRSTDAT_RAW AS 'Start Date',
    PRENDAT_RAW AS 'End Date',
    DSSTDAT_ENROLLMENT_RAW AS 'Enrollment Date',
    BESTRESP AS 'Best Response',
    'Null' AS RSDAT1_RAW,

    DATEDIFF(
        STR_TO_DATE(TRIM(PRSTDAT_RAW), '%d %b %Y'),
        STR_TO_DATE(TRIM(DSSTDAT_ENROLLMENT_RAW), '%d %b %Y')
    ) AS 'N-startDate from enrollment',

    DATEDIFF(
        STR_TO_DATE(TRIM(PRENDAT_RAW), '%d %b %Y'),
        STR_TO_DATE(TRIM(DSSTDAT_ENROLLMENT_RAW), '%d %b %Y')
    ) AS 'N-endDate from enrollment'

FROM ravedata.prior__radiation_supplement

JOIN ravedata.enrollment
    ON prior__radiation_supplement.Subject = enrollment.Subject

WHERE prior__radiation_supplement.RecordActive = 1
  AND PRTRT_RAD IS NOT NULL


UNION ALL


SELECT
    DISTINCT prior__surgery_supplement.Subject,
    'surgery' AS CMCAT,
    PRSTDAT_RAW AS 'Start Date',
    'No end date' AS 'End Date',
    DSSTDAT_ENROLLMENT_RAW AS 'Enrollment Date',
    'Null' AS BESTRESP,
    'Null' AS RSDAT1_RAW,

    DATEDIFF(
        STR_TO_DATE(TRIM(PRSTDAT_RAW), '%d %b %Y'),
        STR_TO_DATE(TRIM(DSSTDAT_ENROLLMENT_RAW), '%d %b %Y')
    ) AS 'N-startDate from enrollment',

    NULL AS 'N-endDate from enrollment'

FROM ravedata.prior__surgery_supplement

JOIN ravedata.enrollment
    ON prior__surgery_supplement.Subject = enrollment.Subject

WHERE prior__surgery_supplement.RecordActive = 1
  AND PRTRT IS NOT NULL;
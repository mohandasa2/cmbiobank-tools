SELECT 
    targeted_therapy_administration.Subject, 

    enrollment.CTEP_SDC_MED_V10_CD AS 'Disease type',

    LOWER(
        TRIM(
            REPLACE(
                REPLACE(
                    REPLACE(
                        REPLACE(
                            REPLACE(
                                REPLACE(
                                    REPLACE(
                                        REPLACE(
                                            REPLACE(
                                                REGEXP_REPLACE(
                                                    CMTRT_DSL,
                                                    '\\s*\\(.*\\)',
                                                    ''
                                                ),
                                                'fam-trastuzumab deruxtecan-nxki',
                                                'trastuzumab'
                                            ),
                                            'isatuximab-irfc',
                                            'isatuximab'
                                        ),
                                        'sacituzumab govitecan-hziy',
                                        'sacituzumab'
                                    ),
                                    'ado-trastuzumab emtansine',
                                    'trastuzumab'
                                ),
                                'lutetium Lu 177 vipivotide tetraxetan',
                                'vipivotide tetraxetan'
                            ),
                            'amivantamab-vmjw',
                            'amivantamab'
                        ),
                        'mirvetuximab soravtansine-gynx',
                        'mirvetuximab soravtansine'
                    ),
                    'zolbetuximab - clzb',
                    'zolbetuximab'
                ),
                'datopotamab deruxtecan-dlnk',
                'datopotamab deruxtecan'
            )
        )
    ) AS `Targeted Therapy`,

    targeted_therapy_administration.TX_CYCLE_NUM AS 'Targeted Therapy #',

    targeted_therapy_administration.CMSTDAT_RAW AS 'Therapy Start Date',

    targeted_therapy_administration.CMENDAT_RAW AS 'Therapy End Date',

    enrollment.DSSTDAT_ENROLLMENT_RAW AS 'Enrollment Date',

    /* Therapy Start Date - Enrollment Date */
    DATEDIFF(
        STR_TO_DATE(
            TRIM(targeted_therapy_administration.CMSTDAT_RAW),
            '%d %b %Y'
        ),
        STR_TO_DATE(
            TRIM(enrollment.DSSTDAT_ENROLLMENT_RAW),
            '%d %b %Y'
        )
    ) AS 'Start Date from Enrollment',

    /* Therapy End Date - Enrollment Date */
    DATEDIFF(
        STR_TO_DATE(
            TRIM(targeted_therapy_administration.CMENDAT_RAW),
            '%d %b %Y'
        ),
        STR_TO_DATE(
            TRIM(enrollment.DSSTDAT_ENROLLMENT_RAW),
            '%d %b %Y'
        )
    ) AS 'End Date from Enrollment',

    course_assessment.BESTRESP AS 'Current response Assessment',

    course_assessment.RSDAT_X1_RAW AS 'Date of Current Response',

    course_assessment.BESTRESP_SPD AS 'Best overall response Assessment',

    course_assessment.RSDAT_X3_RAW AS 'Date of Best overall Response',

    course_assessment.RSDAT_X2_RAW AS 'Date of Progression',

    course_assessment.DSTERM_CD AS 'Targeted Therapy Disposition',

    TRIM(
        REGEXP_REPLACE(
            REPLACE(
                REPLACE(
                    REPLACE(
                        course_assessment.COVAL,
                        '"',
                        ''
                    ),
                    '&#x20;',
                    ' '
                ),
                '&nbsp;',
                ' '
            ),
            '[[:cntrl:]]+',
            ' '
        )
    ) AS 'Comments'

FROM ravedata.targeted_therapy_administration

LEFT JOIN ravedata.course_assessment
    ON targeted_therapy_administration.Subject = course_assessment.Subject
    AND targeted_therapy_administration.TX_CYCLE_NUM = course_assessment.TX_CYCLE_NUM

LEFT JOIN ravedata.enrollment
    ON targeted_therapy_administration.Subject = enrollment.Subject

WHERE targeted_therapy_administration.RecordActive = 1
  AND course_assessment.RecordActive = 1
  AND enrollment.RecordActive = 1;
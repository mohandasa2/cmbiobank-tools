import os
import csv
from datetime import datetime


# ============================================================
# FILE LOCATIONS
# ============================================================

os.chdir("/Users/mohandasa2/Desktop/CatalogData/RAVE")

input_file = "Moonshot Report 10.20.2026.csv"
entity_file = "entity_ids.20260914.csv"
output_file = "Inventory_Output.csv"


# ============================================================
# FUNCTION: PARSE DATE/TIME
# ============================================================

def parse_datetime(value):

    if value is None:
        return None

    # Remove extra spaces
    value = " ".join(str(value).strip().split())

    if value == "":
        return None

    date_formats = [

        # 7/16/2024 12:00:00 AM
        "%m/%d/%Y %I:%M:%S %p",

        # 7/16/2024 12:00 AM
        "%m/%d/%Y %I:%M %p",

        # 3/6/26 13:25
        "%m/%d/%y %H:%M",

        # 3/6/26 13:25:00
        "%m/%d/%y %H:%M:%S",

        # 3/6/2026 13:25
        "%m/%d/%Y %H:%M",

        # 3/6/2026 13:25:00
        "%m/%d/%Y %H:%M:%S",

        # Date only
        "%m/%d/%Y",
        "%m/%d/%y"
    ]

    for date_format in date_formats:

        try:
            return datetime.strptime(
                value,
                date_format
            )

        except ValueError:
            continue

    return None


# ============================================================
# FUNCTION: NORMALIZE ID FOR MATCHING
#
# Matching is case-insensitive.
#
# Example:
#
# 10323-7D95ML41-2
# 10323-7d95ml41-2
#
# Both become:
#
# 10323-7D95ML41-2
# ============================================================

def normalize_id(value):

    if value is None:
        return ""

    return str(value).strip().upper()


# ============================================================
# FUNCTION: CLEAN VALUE FOR OUTPUT
#
# Keeps original capitalization.
# ============================================================

def clean_value(value):

    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# LOAD ENTITY ID FILE
# ============================================================

print()
print("Loading entity ID mappings...")
print()


patient_map = {}
specimen_map = {}
subspecimen_map = {}


with open(
    entity_file,
    "r",
    encoding="cp1252",
    newline=""
) as entity_f:

    entity_reader = csv.DictReader(
        entity_f,
        delimiter=","
    )


    # ========================================================
    # CLEAN COLUMN NAMES
    # ========================================================

    entity_reader.fieldnames = [

        column.strip()

        for column in entity_reader.fieldnames
    ]


    print("Entity ID columns found:")

    for column in entity_reader.fieldnames:

        print(
            "   ",
            repr(column)
        )

    print()


    # ========================================================
    # REQUIRED ENTITY COLUMNS
    # ========================================================

    required_entity_columns = [

        "ctep_id",
        "pub_id",

        "rave_spec_id",
        "pub_spec_id",

        "bcr_subspec_id",
        "pub_subspec_id"
    ]


    missing_entity_columns = [

        column

        for column in required_entity_columns

        if column not in entity_reader.fieldnames
    ]


    if missing_entity_columns:

        print("ERROR: Missing entity columns:")

        for column in missing_entity_columns:

            print(
                "   ",
                repr(column)
            )

        raise ValueError(
            "Required columns are missing "
            "from entity_ids file."
        )


    # ========================================================
    # CREATE LOOKUP DICTIONARIES
    # ========================================================

    for row in entity_reader:


        # ====================================================
        # PATIENT
        #
        # ctep_id -> pub_id
        # ====================================================

        ctep_id_key = normalize_id(
            row["ctep_id"]
        )

        pub_id = clean_value(
            row["pub_id"]
        )


        if ctep_id_key:

            patient_map[
                ctep_id_key
            ] = pub_id


        # ====================================================
        # SPECIMEN
        #
        # rave_spec_id -> pub_spec_id
        # ====================================================

        rave_spec_id_key = normalize_id(
            row["rave_spec_id"]
        )

        pub_spec_id = clean_value(
            row["pub_spec_id"]
        )


        if rave_spec_id_key:

            specimen_map[
                rave_spec_id_key
            ] = pub_spec_id


        # ====================================================
        # SUBSPECIMEN
        #
        # bcr_subspec_id -> pub_subspec_id
        #
        # If bcr_subspec_id is blank, it is simply not
        # added to the lookup dictionary.
        #
        # This does NOT cause a Moonshot row to be skipped.
        # ====================================================

        bcr_subspec_id_key = normalize_id(
            row["bcr_subspec_id"]
        )

        pub_subspec_id = clean_value(
            row["pub_subspec_id"]
        )


        if bcr_subspec_id_key:

            subspecimen_map[
                bcr_subspec_id_key
            ] = pub_subspec_id


# ============================================================
# ENTITY MAPPING SUMMARY
# ============================================================

print("ENTITY ID MAPPINGS LOADED")
print("----------------------------------------")

print(
    f"Patient mappings:       "
    f"{len(patient_map):,}"
)

print(
    f"Specimen mappings:      "
    f"{len(specimen_map):,}"
)

print(
    f"Subspecimen mappings:   "
    f"{len(subspecimen_map):,}"
)

print()


# ============================================================
# OUTPUT HEADER
# ============================================================

output_header = [

    "Subject ID",
    "Public Patient ID",

    "Original Id",
    "Public Specimen ID",

    "Parent ID",

    "BSI ID",
    "Public Sub specimen ID",

    "Derived Biospecimen Type",

    "Anatomic Site",

    "Hours in fixative (calculated)",

    "Collection Date",

    "QC Tumor Content after Enrichment (Moonshot)",

    "QC % Necrosis (Moonshot)",

    "Purification",

    "QC % Tumor (Moonshot)",

    "Vial Status",

    "Cell Count (x10^6)",

    "RIN",

    "DV200",

    "DIN",

    "Concentration by TapeStation (ng/µL)",

    "Concentration by Nanodrop (ng/µL)",

    "Concentration by Qubit (ng/µL)",

    "Volume",

    "Volume Unit",

    "Suspension"
]


# ============================================================
# DUPLICATE TRACKING
# ============================================================

seen = set()


# ============================================================
# COUNTERS
# ============================================================

total_rows = 0
written_rows = 0

duplicate_rows = 0
skipped_status_rows = 0
bad_rows = 0


# ============================================================
# FIXATION COUNTERS
# ============================================================

fixation_calculated = 0
fixation_missing = 0
fixation_date_error = 0
negative_fixation = 0


# ============================================================
# MAPPING COUNTERS
# ============================================================

patient_mapped = 0
patient_not_mapped = 0

specimen_mapped = 0
specimen_not_mapped = 0

subspecimen_mapped = 0
subspecimen_not_mapped = 0


# ============================================================
# UNMAPPED EXAMPLES
# ============================================================

missing_patient_examples = set()

missing_specimen_examples = set()

missing_subspecimen_examples = set()


# ============================================================
# OPEN MOONSHOT INPUT AND OUTPUT
#
# BOTH ARE COMMA-SEPARATED CSV FILES
# ============================================================

with open(
    input_file,
    "r",
    encoding="cp1252",
    newline=""
) as inven, open(
    output_file,
    "w",
    encoding="utf-8-sig",
    newline=""
) as inven_Output:


    # ========================================================
    # COMMA-SEPARATED INPUT
    # ========================================================

    reader = csv.reader(
        inven,
        delimiter=","
    )


    # ========================================================
    # COMMA-SEPARATED OUTPUT
    # ========================================================

    writer = csv.writer(
        inven_Output,
        delimiter=","
    )


    # ========================================================
    # READ HEADER
    # ========================================================

    try:

        header = next(reader)

    except StopIteration:

        raise ValueError(
            "Moonshot input file is empty."
        )


    header = [

        column.strip()

        for column in header
    ]


    print(
        "Number of Moonshot columns:",
        len(header)
    )


    # ========================================================
    # CREATE HEADER LOOKUP
    # ========================================================

    header_index = {

        name: idx

        for idx, name in enumerate(header)
    }


    # ========================================================
    # REQUIRED MOONSHOT COLUMNS
    # ========================================================

    required_columns = [

        "Subject ID",

        "Parent ID",

        "Original Id",

        "BSI ID",

        "Material Type",

        "Anatomic Site",

        "Collection Date/Time",

        "Fixation End Date/Time",

        "Volume",

        "Volume Unit",

        "Concentration by Qubit (ng/µL)",

        "Concentration by Nanodrop (ng/µL)",

        "Concentration by TapeStation (ng/µL)",

        "DV200",

        "DIN",

        "RIN",

        "Cell Count (x10^6)",

        "Vial Status",

        "QC % Tumor (Moonshot)",

        "QC Tumor Content after Enrichment (Moonshot)",

        "Purification",

        "Suspension/Solvent",

        "QC % Necrosis (Moonshot)"
    ]


    # ========================================================
    # CHECK REQUIRED COLUMNS
    # ========================================================

    missing = [

        column

        for column in required_columns

        if column not in header_index
    ]


    if missing:

        print()
        print("ERROR: Missing Moonshot columns:")

        for column in missing:

            print(
                "   ",
                repr(column)
            )

        print()
        print("Columns actually found:")

        for number, column in enumerate(header):

            print(
                number,
                repr(column)
            )

        raise ValueError(
            "Required Moonshot columns are missing."
        )


    # ========================================================
    # COLUMN LOCATIONS
    # ========================================================

    Subject_ID = header_index[
        "Subject ID"
    ]

    Parent_ID = header_index[
        "Parent ID"
    ]

    Original_Id = header_index[
        "Original Id"
    ]

    BSI_ID = header_index[
        "BSI ID"
    ]

    MaterialType = header_index[
        "Material Type"
    ]

    AnatomicSite = header_index[
        "Anatomic Site"
    ]

    CollectionDate = header_index[
        "Collection Date/Time"
    ]

    FixationDate = header_index[
        "Fixation End Date/Time"
    ]

    Volume = header_index[
        "Volume"
    ]

    Volume_Unit = header_index[
        "Volume Unit"
    ]

    con_Qubit = header_index[
        "Concentration by Qubit (ng/µL)"
    ]

    con_nanodrop = header_index[
        "Concentration by Nanodrop (ng/µL)"
    ]

    con_tape = header_index[
        "Concentration by TapeStation (ng/µL)"
    ]

    DV200 = header_index[
        "DV200"
    ]

    DIN = header_index[
        "DIN"
    ]

    RIN = header_index[
        "RIN"
    ]

    cell_count = header_index[
        "Cell Count (x10^6)"
    ]

    Vial_Status = header_index[
        "Vial Status"
    ]

    qc_tumor = header_index[
        "QC % Tumor (Moonshot)"
    ]

    tumor_enrich = header_index[
        "QC Tumor Content after Enrichment (Moonshot)"
    ]

    Purification = header_index[
        "Purification"
    ]

    Suspension = header_index[
        "Suspension/Solvent"
    ]

    qc_nec = header_index[
        "QC % Necrosis (Moonshot)"
    ]


    # ========================================================
    # DISPLAY COLUMN LOCATIONS
    # ========================================================

    print(
        "Subject ID column:",
        Subject_ID
    )

    print(
        "Original Id column:",
        Original_Id
    )

    print(
        "BSI ID column:",
        BSI_ID
    )

    print(
        "Vial Status column:",
        Vial_Status
    )

    print(
        "Collection Date column:",
        CollectionDate
    )

    print(
        "Fixation End Date column:",
        FixationDate
    )

    print()
    print("Starting Moonshot processing...")
    print()


    # ========================================================
    # WRITE OUTPUT HEADER
    # ========================================================

    writer.writerow(
        output_header
    )


    # ========================================================
    # PROCESS MOONSHOT ROWS
    # ========================================================

    for row_number, i in enumerate(
        reader,
        start=2
    ):


        total_rows += 1


        # ====================================================
        # PROGRESS
        # ====================================================

        if total_rows % 10000 == 0:

            print(

                f"Processed {total_rows:,} rows | "

                f"Written {written_rows:,}"
            )


        # ====================================================
        # SKIP COMPLETELY EMPTY ROWS
        # ====================================================

        if not i or not any(i):

            continue


        # ====================================================
        # CLEAN VALUES
        # ====================================================

        i = [

            clean_value(value)

            for value in i
        ]


        # ====================================================
        # CHECK COLUMN COUNT
        # ====================================================

        if len(i) != len(header):

            bad_rows += 1

            if bad_rows <= 10:

                print(

                    f"WARNING row {row_number}: "

                    f"{len(i)} columns; "

                    f"expected {len(header)}"
                )

            continue


        # ====================================================
        # VIAL STATUS
        # ====================================================

        vial_status = i[
            Vial_Status
        ]


        # ====================================================
        # SKIP UNAVAILABLE VIALS
        # ====================================================

        if vial_status in {

            "Out",
            "Reserved",
            "Empty",
            "Destroyed/Broken"

        }:

            skipped_status_rows += 1

            continue


        # ====================================================
        # ORIGINAL IDS FOR OUTPUT
        # ====================================================

        subject_id = clean_value(
            i[Subject_ID]
        )

        original_id = clean_value(
            i[Original_Id]
        )

        bsi_id = clean_value(
            i[BSI_ID]
        )


        # ====================================================
        # NORMALIZED IDS FOR MATCHING
        #
        # Case-insensitive matching.
        # ====================================================

        subject_id_key = normalize_id(
            subject_id
        )

        original_id_key = normalize_id(
            original_id
        )

        bsi_id_key = normalize_id(
            bsi_id
        )


        # ====================================================
        # PUBLIC PATIENT ID
        #
        # Subject ID -> ctep_id -> pub_id
        # ====================================================

        public_patient_id = patient_map.get(
            subject_id_key,
            ""
        )


        if public_patient_id:

            patient_mapped += 1

        else:

            patient_not_mapped += 1

            if (
                subject_id
                and
                len(missing_patient_examples) < 20
            ):

                missing_patient_examples.add(
                    subject_id
                )


        # ====================================================
        # PUBLIC SPECIMEN ID
        #
        # Original Id -> rave_spec_id -> pub_spec_id
        # ====================================================

        public_specimen_id = specimen_map.get(
            original_id_key,
            ""
        )


        if public_specimen_id:

            specimen_mapped += 1

        else:

            specimen_not_mapped += 1

            if (
                original_id
                and
                len(missing_specimen_examples) < 20
            ):

                missing_specimen_examples.add(
                    original_id
                )


        # ====================================================
        # PUBLIC SUBSPECIMEN ID
        #
        # BSI ID -> bcr_subspec_id -> pub_subspec_id
        #
        # IMPORTANT:
        #
        # Missing mapping DOES NOT cause this row to be
        # skipped.
        #
        # Public Sub specimen ID is simply blank.
        # ====================================================

        public_subspecimen_id = (
            subspecimen_map.get(
                bsi_id_key,
                ""
            )
        )


        if public_subspecimen_id:

            subspecimen_mapped += 1

        else:

            subspecimen_not_mapped += 1


            if (
                bsi_id
                and
                len(missing_subspecimen_examples) < 20
            ):

                missing_subspecimen_examples.add(
                    bsi_id
                )


        # ====================================================
        # MATERIAL TYPE
        # ====================================================

        material_type = i[
            MaterialType
        ]


        # ====================================================
        # ANATOMIC SITE
        # ====================================================

        anatomic_site = i[
            AnatomicSite
        ]


        # ====================================================
        # PURIFICATION
        # ====================================================

        purification = i[
            Purification
        ]


        # ====================================================
        # EMBEDDED BLOCK -> FFPE BLOCK
        # ====================================================

        if material_type == "Embedded Block":

            material_type = "FFPE Block"


        # ====================================================
        # BONE MARROW
        # ====================================================

        if anatomic_site == "Bone Marrow":


            # Curl -> Tissue Curl

            if material_type == "Curl":

                material_type = "Tissue Curl"


            purification = (

                purification

                .replace(
                    "CD138 Sort Negative Fraction",
                    "CD138 '-' BM"
                )

                .replace(
                    "CD138 Sort Positive Fraction",
                    "CD138 + BM"
                )
            )


        # ====================================================
        # WHOLE BLOOD
        # ====================================================

        elif anatomic_site == "Whole Blood":


            purification = (

                purification

                .replace(
                    "CD138 Sort Negative Fraction",
                    "CD138 '-' Blood"
                )

                .replace(
                    "CD138 Sort Positive Fraction",
                    "CD138 + Blood"
                )

                .replace(
                    "CD3 Sort Positive Fraction",
                    "CD38 + Blood"
                )

                .replace(
                    "CD3 Sort Negative  Fraction",
                    "CD38 - Blood"
                )
            )


        # ====================================================
        # OTHER CURLS
        # ====================================================

        elif material_type == "Curl":

            material_type = "Tissue Curl"


        # ====================================================
        # HOURS IN FIXATIVE
        #
        # Fixation End Date/Time
        #          -
        # Collection Date/Time
        #
        # Rounded to nearest whole hour.
        #
        # Negative values are retained.
        # ====================================================

        collection_value = i[
            CollectionDate
        ]

        fixation_value = i[
            FixationDate
        ]


        hours_in_fixative = ""


        if collection_value and fixation_value:


            collection_dt = parse_datetime(
                collection_value
            )

            fixation_dt = parse_datetime(
                fixation_value
            )


            if (
                collection_dt is not None
                and
                fixation_dt is not None
            ):


                hours = (

                    fixation_dt

                    -

                    collection_dt

                ).total_seconds() / 3600


                # --------------------------------------------
                # ROUND TO WHOLE HOURS
                # --------------------------------------------

                hours_in_fixative = str(
                    round(hours)
                )


                fixation_calculated += 1


                # --------------------------------------------
                # COUNT NEGATIVE VALUES
                # BUT KEEP THEM
                # --------------------------------------------

                if hours < 0:

                    negative_fixation += 1


            else:

                fixation_date_error += 1


                # Print first 10 date parsing problems

                if fixation_date_error <= 10:

                    print()

                    print(
                        f"WARNING row {row_number}: "
                        "Could not parse date."
                    )

                    print(
                        "Collection:",
                        repr(collection_value)
                    )

                    print(
                        "Fixation:",
                        repr(fixation_value)
                    )

                    print()


        else:

            fixation_missing += 1


        # ====================================================
        # BUILD OUTPUT ROW
        # ====================================================

        output_row = [

            # Subject ID
            subject_id,

            # Public Patient ID
            public_patient_id,

            # Original Id
            original_id,

            # Public Specimen ID
            public_specimen_id,

            # Parent ID
            i[Parent_ID],

            # BSI ID
            bsi_id,

            # Public Sub specimen ID
            public_subspecimen_id,

            # Derived Biospecimen Type
            material_type,

            # Anatomic Site
            anatomic_site,

            # Hours in fixative
            hours_in_fixative,

            # Collection Date
            collection_value,

            # QC Tumor Content after Enrichment
            i[tumor_enrich],

            # QC % Necrosis
            i[qc_nec],

            # Purification
            purification,

            # QC % Tumor
            i[qc_tumor],

            # Vial Status
            vial_status,

            # Cell Count
            i[cell_count],

            # RIN
            i[RIN],

            # DV200
            i[DV200],

            # DIN
            i[DIN],

            # TapeStation
            i[con_tape],

            # Nanodrop
            i[con_nanodrop],

            # Qubit
            i[con_Qubit],

            # Volume
            i[Volume],

            # Volume Unit
            i[Volume_Unit],

            # Suspension
            i[Suspension]
        ]


        # ====================================================
        # DUPLICATE CHECK
        # ====================================================

        row_key = tuple(
            output_row
        )


        if row_key in seen:

            duplicate_rows += 1

            continue


        seen.add(
            row_key
        )


        # ====================================================
        # WRITE CSV ROW
        # ====================================================

        writer.writerow(
            output_row
        )


        written_rows += 1


        # ====================================================
        # FLUSH EVERY 10,000 RECORDS
        # ====================================================

        if written_rows % 10000 == 0:

            inven_Output.flush()


# ============================================================
# FINAL REPORT
# ============================================================

print()
print("========================================")
print("PROCESSING COMPLETE")
print("========================================")

print(
    f"Total Moonshot rows:            "
    f"{total_rows:,}"
)

print(
    f"Rows written:                   "
    f"{written_rows:,}"
)

print(
    f"Vial status skipped:            "
    f"{skipped_status_rows:,}"
)

print(
    f"Duplicate rows removed:         "
    f"{duplicate_rows:,}"
)

print(
    f"Bad rows skipped:               "
    f"{bad_rows:,}"
)


# ============================================================
# FIXATION REPORT
# ============================================================

print()
print("FIXATION CALCULATION")
print("----------------------------------------")

print(
    f"Hours calculated:               "
    f"{fixation_calculated:,}"
)

print(
    f"Missing collection/fixation:    "
    f"{fixation_missing:,}"
)

print(
    f"Unrecognized date format:       "
    f"{fixation_date_error:,}"
)

print(
    f"Negative fixation intervals:    "
    f"{negative_fixation:,}"
)


# ============================================================
# PUBLIC ID MAPPING REPORT
# ============================================================

print()
print("PUBLIC ID MAPPING")
print("----------------------------------------")

print(
    f"Patient IDs mapped:             "
    f"{patient_mapped:,}"
)

print(
    f"Patient IDs NOT mapped:         "
    f"{patient_not_mapped:,}"
)

print()

print(
    f"Specimen IDs mapped:            "
    f"{specimen_mapped:,}"
)

print(
    f"Specimen IDs NOT mapped:        "
    f"{specimen_not_mapped:,}"
)

print()

print(
    f"Subspecimen IDs mapped:         "
    f"{subspecimen_mapped:,}"
)

print(
    f"Subspecimen IDs NOT mapped:     "
    f"{subspecimen_not_mapped:,}"
)


# ============================================================
# SHOW UNMAPPED EXAMPLES
#
# These are informational ONLY.
# They are NOT excluded from output.
# ============================================================

if missing_patient_examples:

    print()
    print("Example unmapped Subject IDs:")
    print("----------------------------------------")

    for value in sorted(
        missing_patient_examples
    ):

        print(value)


if missing_specimen_examples:

    print()
    print("Example unmapped Original IDs:")
    print("----------------------------------------")

    for value in sorted(
        missing_specimen_examples
    ):

        print(value)


if missing_subspecimen_examples:

    print()
    print("Example unmapped BSI IDs:")
    print("----------------------------------------")

    for value in sorted(
        missing_subspecimen_examples
    ):

        print(value)


# ============================================================
# RECORD RECONCILIATION
#
# IMPORTANT:
#
# Missing public IDs are NOT exclusions.
#
# Only:
#
#   1. Vial Status
#   2. Duplicate records
#   3. Bad rows
#
# reduce the output count.
# ============================================================

expected_output = (

    total_rows

    - skipped_status_rows

    - duplicate_rows

    - bad_rows
)


print()
print("========================================")
print("RECORD RECONCILIATION")
print("========================================")

print(
    f"Input data rows:                "
    f"{total_rows:,}"
)

print(
    f"Vial status excluded:           "
    f"{skipped_status_rows:,}"
)

print(
    f"Duplicates removed:             "
    f"{duplicate_rows:,}"
)

print(
    f"Bad rows excluded:              "
    f"{bad_rows:,}"
)

print("----------------------------------------")

print(
    f"Expected output data rows:      "
    f"{expected_output:,}"
)

print(
    f"Actual output data rows:        "
    f"{written_rows:,}"
)

print("----------------------------------------")


if expected_output == written_rows:

    print(
        "RECONCILIATION: PASS"
    )

else:

    print(
        "RECONCILIATION: FAIL"
    )

    print(
        "Difference:",
        expected_output - written_rows
    )


# ============================================================
# OUTPUT LOCATION
# ============================================================

print()
print(
    f"Output file: {output_file}"
)
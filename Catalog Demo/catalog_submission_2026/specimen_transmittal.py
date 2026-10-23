import os
import csv
from CatalogData import catalog

os.chdir("/Users/mohandasa2/Desktop/CatalogData/RAVE")

input_file = "specimen_transmittal.CSV"
output_file = "specimen_transmittal_output.txt"


# ============================================================
# Normalize text for matching
# Handles extra spaces, tabs, non-breaking spaces, etc.
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    value = str(value)
    value = value.replace("\xa0", " ")
    value = value.replace("\t", " ")
    value = value.replace("\r", " ")
    value = value.replace("\n", " ")

    # Collapse multiple spaces into one
    value = " ".join(value.split())

    return value.strip()


# ============================================================
# Determine:
#   Specimen Category
#   Specimen Type
#   Specimen Preservation Method
#
# Based ONLY on BESPEC_DRV (Specimen type)
# ============================================================

def get_specimen_info(specimen_type):

    # Keep original value for output
    original_type = normalize_text(specimen_type)

    # Uppercase normalized value for matching
    type_match = original_type.upper()

    # --------------------------------------------------------
    # 1. Blank specimen type
    # --------------------------------------------------------

    if type_match == "":
        return (
            "Not Reported",
            "Not Reported",
            "Not Reported"
        )

    # --------------------------------------------------------
    # 2. Blood
    # If "Blood" appears anywhere in the type
    # --------------------------------------------------------

    if "BLOOD" in type_match:
        return (
            "Blood",
            original_type,
            ""
        )

    # --------------------------------------------------------
    # 3. Bone Marrow
    # If "Bone Marrow" appears anywhere in the type
    # --------------------------------------------------------

    if "BONE MARROW" in type_match:
        return (
            "Bone Marrow",
            original_type,
            ""
        )

    # --------------------------------------------------------
    # 4. Snap Frozen Tissue
    # Category = Tissue
    # Type = Frozen Tissue
    # Method = Liquid Nitrogen
    # --------------------------------------------------------

    if "SNAP FROZEN TISSUE" in type_match:
        return (
            "Tissue",
            "Frozen Tissue",
            "Liquid Nitrogen"
        )

    # --------------------------------------------------------
    # 5. FFPE Block
    # --------------------------------------------------------

    if type_match == "FFPE BLOCK":
        return (
            "Tissue",
            original_type,
            "Formalin Fixed Paraffin Embedded Tissue"
        )

    # --------------------------------------------------------
    # 6. Unstained Slide
    # --------------------------------------------------------

    if type_match == "UNSTAINED SLIDE":
        return (
            "Tissue",
            original_type,
            "Formalin Fixed Paraffin Embedded Tissue"
        )

    # --------------------------------------------------------
    # 7. Cell Block
    # --------------------------------------------------------

    if type_match == "CELL BLOCK":
        return (
            "Tissue",
            original_type,
            "Formalin Fixed Paraffin Embedded Tissue"
        )

    # --------------------------------------------------------
    # 8. Curl
    # --------------------------------------------------------

    if type_match == "CURL":
        return (
            "Tissue",
            original_type,
            "Formalin Fixed Paraffin Embedded Tissue"
        )

    # --------------------------------------------------------
    # 9. Stained Slide
    # --------------------------------------------------------

    if type_match == "STAINED SLIDE":
        return (
            "Tissue",
            original_type,
            "Formalin Fixed Paraffin Embedded Tissue"
        )

    # --------------------------------------------------------
    # 10. Formalin Fixed Tissue
    # --------------------------------------------------------

    if type_match == "FORMALIN FIXED TISSUE":
        return (
            "Tissue",
            original_type,
            "Formalin Fixed Tissue"
        )

    # --------------------------------------------------------
    # 11. Fresh Tissue in Media to PDMR
    # Handles multiple spaces in source value
    # --------------------------------------------------------

    if type_match == "FRESH TISSUE IN MEDIA TO PDMR":
        return (
            "Tissue",
            original_type,
            "Fresh Tissue"
        )

    # --------------------------------------------------------
    # 12. Everything else
    # Category = Tissue
    # Method = blank
    # --------------------------------------------------------

    return (
        "Tissue",
        original_type,
        ""
    )


# ============================================================
# Read specimen transmittal file
# ============================================================

transList = {}

with open(
    input_file,
    "r",
    newline="",
    encoding="utf-8-sig"
) as filespecimen:

    reader = csv.DictReader(filespecimen)

    # Check that required columns exist
    required_columns = [
        "BEDAT_RAW",
        "ASMTTPT_DRV",
        "TISTYP",
        "SPECID",
        "BESPEC_DRV",
        "subjectId",
        "Subject",
        "siteid",
        "Site",
        "BSPDMRYN",
        "RecordActive",
        "project",
        "SPECID_DBGAP",
        "SiteNumber"
    ]

    missing_columns = [
        col for col in required_columns
        if col not in reader.fieldnames
    ]

    if missing_columns:
        raise ValueError(
            "Missing columns in specimen_transmittal.CSV: "
            + ", ".join(missing_columns)
        )

    # --------------------------------------------------------
    # Process rows
    # --------------------------------------------------------

    for row in reader:

        # ----------------------------------------------------
        # RecordActive must be 1
        # ----------------------------------------------------

        if normalize_text(row["RecordActive"]) != "1":
            continue

        # ----------------------------------------------------
        # Skip PDMR records
        # ----------------------------------------------------

        if normalize_text(row["BSPDMRYN"]).upper() == "YES":
            continue

        # ----------------------------------------------------
        # Build Subject ID
        # ----------------------------------------------------

        search = (
            normalize_text(row["project"]) + "_" +
            normalize_text(row["subjectId"]) + "_" +
            normalize_text(row["Subject"]) + "_" +
            normalize_text(row["siteid"]) + "_" +
            normalize_text(row["Site"]) + "_" +
            normalize_text(row["SiteNumber"])
        )

        # ----------------------------------------------------
        # Specimen type comes directly from BESPEC_DRV
        # ----------------------------------------------------

        specimen_type = row["BESPEC_DRV"]

        # ----------------------------------------------------
        # Determine final specimen information
        # ----------------------------------------------------

        (
            specimen_category,
            specimen_type_final,
            preservation_method
        ) = get_specimen_info(specimen_type)

        # ----------------------------------------------------
        # Create output record
        # ----------------------------------------------------

        output_record = [
            normalize_text(row["BEDAT_RAW"]),
            specimen_category,
            normalize_text(row["SPECID"]),
            specimen_type_final,
            normalize_text(row["ASMTTPT_DRV"]),
            normalize_text(row["TISTYP"]),
            normalize_text(row["SPECID_DBGAP"]),
            preservation_method
        ]

        # ----------------------------------------------------
        # Store only unique records
        # ----------------------------------------------------

        if search not in transList:
            transList[search] = []

        if output_record not in transList[search]:
            transList[search].append(output_record)


# ============================================================
# Write output
# ============================================================

with open(
    output_file,
    "w",
    encoding="utf-8"
) as output:

    output.write(
        "SubjectID\t"
        "Date of Specimen Collection\t"
        "Specimen Category\t"
        "Specimen ID\t"
        "Specimen type\t"
        "Collection Timepoint\t"
        "Tissue Category\t"
        "dbGap_SPECID\t"
        "Specimen_preservation_method\n"
    )

    for subject_id, records in transList.items():

        for record in records:

            output.write(
                subject_id + "\t" +
                "\t".join(record) +
                "\n"
            )


print(f"Output written to: {output_file}")
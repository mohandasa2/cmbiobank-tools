import os
import pandas as pd
from sqlalchemy import create_engine

# Function to load CSV files into MySQL using SQLAlchemy
def load_csv_to_mysql(csv_dir, engine):
    for file_name in os.listdir(csv_dir):
        if file_name.endswith(".CSV"):

            base,ext=os.path.splitext(file_name)
            file_name=base+ext.lower()

            table_name = os.path.splitext(file_name)[0]  # Extract table name from file name
            csv_path = os.path.join(csv_dir, file_name)
            print(f"\nReading: {csv_path}", flush=True)

            df = pd.read_csv(csv_path,low_memory=False)
            print(f"Successfully read {len(df):,} rows", flush=True)
            try:
                df.to_sql(name=table_name, con=engine, if_exists='append', index=False)
                print(f"Loaded {file_name} into MySQL")
            except Exception as e:
                print(f"Error loading {file_name} into MySQL: {e}")

# MySQL database connection parameters
host = 'moonshotbiobank-dev-db.cy7uk48sck0v.us-east-1.rds.amazonaws.com'
database = 'ravedata'
user = 'amohandas'
password = 'VCWzutM7Kmq#'

# Create MySQL connection engine using SQLAlchemy
engine = create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}/{database}")
#
# Directory containing CSV files
# csv_directory = '/Users/mohandasa2/OneDrive - National Institutes of Health/General - NCI-Moonshot Biobank IT/DataTest/10323_4200_20251005_062000'
csv_directory = '/Users/mohandasa2/Library/CloudStorage/OneDrive-NationalInstitutesofHealth/NCI-Moonshot Biobank IT - Documents/General/Rave Data Dumps/10323_6929_20261018_213000'

# Load CSV files into MySQL using SQLAlchemy engine
load_csv_to_mysql(csv_directory, engine)

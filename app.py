import pandas as pd
import json
import os
import sys
import glob
import re
from dotenv import load_dotenv

load_dotenv()

# module to get column names of each dataset from schemas file
def get_column_names(schemas, ds_name, sorting_key='column_position'):
    column_details = schemas[ds_name]
    columns = sorted(column_details, key=lambda col : col[sorting_key])
    return list(map(lambda col : col['column_name'], columns))

# module to read csv files of datasets using column names from schemas
def read_csv(file, schemas):
    file_path = re.split('[/\\\]', file)
    ds_name = file_path[-2]
    file_name = file_path[-1]
    columns = get_column_names(schemas, ds_name)
    df = pd.read_csv(file, names=columns, header=None, chunksize=10000)
    return df

# module to insert into sql
def to_sql(df, db_conn_uri, ds_name):
    df.to_sql(
        ds_name,
        db_conn_uri,
        if_exists='append',
        index=False
    )

# module to load data into db
def db_loader(src_base_dir, db_conn_uri, ds_name):
    schemas = json.load(open(f'{src_base_dir}/schemas.json'))
    files = glob.glob(f'{src_base_dir}/{ds_name}/part-*')
    if len(files) == 0:
        raise NameError(f'No files found for dataset {ds_name}')
    
    for file in files:
        df_reader = read_csv(file, schemas)
        for idx, df in enumerate(df_reader):
            print(f'Populating chunk {idx} of {ds_name}')
            to_sql(df, db_conn_uri, ds_name)

# module to get env variables and process files
def process_files(ds_names=None):
    src_base_dir = os.environ.get('SRC_BASE_DIR')
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT')
    db_username = os.environ.get('DB_USERNAME')
    db_password = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')
    db_conn_uri = f'postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}'
    schemas = json.load(open(f'{src_base_dir}/schemas.json'))
    if not ds_names:
        ds_names = schemas.keys()
    for ds_name in ds_names:
        try:
            print(f'Processing {ds_name}')
            db_loader(src_base_dir, db_conn_uri, ds_name)
        except NameError as ne:
            print(ne)
            pass

if __name__ == '__main__':
    if len(sys.argv) == 2:
        ds_names = json.loads(sys.argv[1])
        process_files(ds_names)
    else:
        process_files()
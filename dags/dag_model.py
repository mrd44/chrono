# We'll start by importing the DAG object

#from lightgbm.sklearn import LGBMClassifier
from  sklearn.preprocessing import  LabelEncoder
import pickle
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.email_operator import EmailOperator
from airflow.utils.dates import days_ago
import xgboost as xgb
import os 
import pandas_gbq
from google.oauth2 import service_account
import pandas as pd
import glob
import logging
import sys
from datetime import timedelta, datetime
from google.cloud import storage

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from google.cloud import storage

project= "test-chronotruck"
bucket_path="test-chr-ml/primary/data.csv"


# Authentification à Google Big Query
CREDENTIALS = service_account.Credentials.from_service_account_file(
    '/opt/airflow/data/service-account.json' # Chemin d'accès au compte de service
)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"]='/opt/airflow/data/service-account.json'

pandas_gbq.context.credentials = CREDENTIALS

# initializing the default arguments that we'll pass to our DAG
# Arguments du DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(2),
    'retries': 1,
    'retry_delay': timedelta(seconds=5),
    'provide_context': True
}

# Création du DAG
dag = DAG(
    'tax_income',
    default_args=default_args,
    description='DAG PREDICTION',
    schedule_interval="0 5 * * *" # Le DAG sera exécuté tous les jours à 5h
)



def load_csv_from_bucket() -> pd.DataFrame:

    """
    Loads multiple CSV files from bucket .

    """

    logging.info('Starting load_csv_from_bucket function...')

    # Create a Google Cloud Storage client.
    storage_client = storage.Client()

    # Extract the bucket name and folder path from the provided bucket path.
    bucket_name = bucket_path.split("/")[0]
    folder = "/".join(bucket_path.split("/")[1:]) + "/census_"
    
    logging.info(f'Downloading CSV files from {bucket_name} ')
    # Download all CSV files in the specified folder to a temporary directory.
    files_found = False

    for blob in storage_client.list_blobs(bucket_name, prefix=folder):
        filename = blob.name.split("/")[-1]
        if filename[-3:] == "csv":
            files_found = True
            blob.download_to_filename("/tmp/" + filename)

    if not files_found:
        logging.error(f'No CSV files found in {bucket_path}.')
        sys.exit()

    all_files = glob.glob("/tmp/*.csv")
    li = []
    logging.info('Concatenating CSV files into a single DataFrame...')
    # Concatenate all CSV files into a single Pandas DataFrame.
    for filename in all_files:
        df = pd.read_csv(filename, index_col=None, sep=",")
        li.append(df)

    df = pd.concat(li, axis=0, ignore_index=True)

    logging.info('Select specific columns and rename them')
    # Select specific columns and rename them.
    features=df.iloc[:, [0,12,7,4,19]]
    new_columns=['age','sex','marital_stat','education','tax_filer_stat']
    column_dict = dict(zip(features.columns, new_columns))
    features = features.rename(columns=column_dict)
    
    logging.info('Exporting DataFrame to BigQuery...')
    # Export the selected columns to BigQuery.
    pandas_gbq.to_gbq(
        features,
        'datawarehouse.tax',
        project_id='test-chronotruck',
        if_exists='replace',
        table_schema = [
            {'name':'age','type': 'INTEGER'},
            {'name':'sex','type': 'STRING'},
            {'name':'marital_stat','type': 'STRING'},
            {'name':'education','type': 'STRING'},
             {'name':'tax_filer_stat','type': 'STRING'}
            
        ]      
        
    )
    logging.info('Finished load_csv_from_bucket function.')
       
def model_predict (): 



    # Load data from BigQuery.
    logging.info('Loading data from BigQuery...')

    features = pandas_gbq.read_gbq(
         
        """
        SELECT age,sex,marital_stat,education,tax_filer_stat
        
        FROM datawarehouse.tax
    
        """,
        project_id=project,
        credentials=CREDENTIALS
    ) 
 
    #One-hot encode categorical features.
    logging.info('One-hot encoding categorical features...')

    df = pd.get_dummies(features, columns = ['sex','marital_stat','education','tax_filer_stat'])
   
    
   # Load XGBoost model and perform predictions.
    logging.info('Loading XGBoost model and performing predictions...')
    model_xgb_2 = xgb.Booster()
    model_xgb_2.load_model("/opt/airflow/data/xgbc.json")
    predictions=model_xgb_2.predict(xgb.DMatrix(df))

  # Add predictions to original DataFrame.
    logging.info('Adding predictions to DataFrame...')
    features["predictions"]=predictions
    features["predictions"]=features["predictions"].astype(str)


   # Export DataFrame to BigQuery.
    logging.info('Exporting DataFrame to BigQuery...')
    pandas_gbq.to_gbq(
        features,
        'datawarehouse.tax-prediction',
        project_id='test-chronotruck',
        if_exists='replace',
        table_schema = [
            {'name':'age','type': 'INTEGER'},
            {'name':'sex','type': 'STRING'},
            {'name':'marital_stat','type': 'STRING'},
            {'name':'education','type': 'STRING'},
           {'name':'tax_filer_stat','type': 'STRING'},
           {'name':'predictions','type': 'STRING'}
            
        ]
        )
    logging.info('Finished model_predict function.')
    



task_extract = PythonOperator(
    task_id='extract_and_load',
    dag=dag,
    python_callable=load_csv_from_bucket
)


task_predict = PythonOperator(
    task_id='model_predict',
    dag=dag,
    python_callable=model_predict
)

task_extract >> task_predict
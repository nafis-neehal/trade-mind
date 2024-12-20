from pathlib import Path
import yaml
from dotenv import load_dotenv
import os
import pandas as pd

# Custom imports
from FeatureProcessor import FeatureProcessor
from HopsworkFeatureStore import HopsworkFeatureStore
from StockData import StockData

import warnings
warnings.filterwarnings('ignore')

load_dotenv()

# Define the base directory as the project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Use BASE_DIR to dynamically load the config file
CONFIG_FILE = BASE_DIR / "src" / "config.yml"
with open(CONFIG_FILE, 'r') as file:
    configs = yaml.safe_load(file)

global_flag = 1


def run_stock_profile(symbol, init=False, **kwargs):
    stock = StockData(symbol)
    if init:
        # <--- use this if we don't have any data on stock yet
        if 'days_before' in kwargs:
            stock.init_data(days_before=kwargs['days_before'])
        else:
            # <---- default to 30 days, hourly data
            stock.init_data(days_before=30)
    else:
        # <--- use this to periodically update the data up to the latest hour
        global global_flag
        global_flag = stock.update_data()


def run_feature_engineering_pipeline(symbol):
    # Process the features for stock
    feature_processor = FeatureProcessor(symbol=symbol)

    # Dynamically create the filename for JSON data
    file_name = feature_processor.create_filename()
    json_data = feature_processor.read_json_file(file_name)
    if json_data:
        df = feature_processor.save_json_features_to_dataframe(json_data)
        engineered_df = feature_processor.feature_engineering(df)
        feature_processor.save_new_features_to_file(engineered_df)


def run_feature_store_ingestion(symbol):
    # Define your configurations
    # Replace with your Hopsworks project name
    PROJECT_NAME = configs['hopsworks']['project_name']
    FEATURE_GROUP_NAME = f"{symbol.split('/')[0].lower()}_features"
    API_KEY = os.getenv("HOPSWORKS_API_KEY")

    # Use BASE_DIR to dynamically build the paths for data directories and files
    data_eng_dir = BASE_DIR / "data" / "engineered"
    file_name = f"stockdata_{symbol.split('/')[0]}_engineered.csv"
    CSV_PATH = data_eng_dir / file_name

    # Initialize and run the pipeline
    hopswork_fs = HopsworkFeatureStore(
        PROJECT_NAME,
        FEATURE_GROUP_NAME,
        API_KEY,
        str(CSV_PATH)  # Convert Path object to string for compatibility
    )
    hopswork_fs.run_pipeline()


if __name__ == "__main__":
    # Fetch data for BTC/USD for the last 20 days - initial data fetch
    symbol = configs['stock_api_params']['symbol']
    print(f"Fetching data for {symbol}...")
    run_stock_profile(symbol, init=False)
    print(f"Data fetched for {symbol}")

    if global_flag == 1:
        print("Running feature engineering pipeline...")
        run_feature_engineering_pipeline(symbol)
        print("Feature engineering pipeline completed")
        print("Running feature store ingestion pipeline...")
        run_feature_store_ingestion(symbol)
        print("Feature store ingestion pipeline completed")
    elif global_flag == -1:
        print("Data already up to date")
    else:
        print("Failed to update data")

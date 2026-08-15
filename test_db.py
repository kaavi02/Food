import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get('DATABASE_URL')
print(f"Connecting to: {db_url}")
try:
    engine = create_engine(db_url)
    with engine.connect() as connection:
        print("Successfully connected to the database!")
except Exception as e:
    print(f"Failed to connect to the database. Error: {e}")

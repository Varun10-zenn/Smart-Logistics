import sqlalchemy
from sqlalchemy import create_engine, text
from backend.app.core.config import settings

def check_db():
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            print("Connected to MySQL successfully!")
            
            # Check tables
            res = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in res]
            print(f"Tables ({len(tables)}): {tables}")
            
            if 'users' in tables:
                res = conn.execute(text("SELECT email FROM users"))
                users = [row[0] for row in res]
                print(f"Users in DB ({len(users)}): {users}")
            else:
                print("Table 'users' does not exist.")
    except Exception as e:
        print(f"Database Error: {e}")

if __name__ == "__main__":
    check_db()

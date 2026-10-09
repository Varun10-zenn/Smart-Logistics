import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from backend.app.core.database import SessionLocal
from backend.app.schemas.user import UserCreate
from backend.app.services.user_service import create_user

def main():
    db = SessionLocal()
    try:
        user_data = UserCreate(
            email="varun@gmail.com",
            full_name="Varun",
            password="test1234",
            role_code="admin"
        )
        user = create_user(db, user_data)
        print(f"User created: {user.email}")
    except Exception as e:
        print(f"Error creating user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()

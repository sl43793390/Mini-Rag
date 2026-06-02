from db.database import Database

db = Database()
db.create_user("admin", "admin123", role="admin")
user = db.verify_user("admin", "admin123")
print(f"Admin user verified: {user is not None}")
if user:
    print(f"Role: {user['role']}")

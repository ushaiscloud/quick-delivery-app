from flask_login import UserMixin
from database import get_db

class User(UserMixin):
    def __init__(self, id, full_name, email, phone, role):
        self.id = id
        self.full_name = full_name
        self.email = email
        self.phone = phone
        self.role = role

    @staticmethod
    def get(user_id):
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE id = ?', (user_id,)
        ).fetchone()
        db.close()
        if not user:
            return None
        return User(
            id=user['id'],
            full_name=user['full_name'],
            email=user['email'],
            phone=user['phone'],
            role=user['role']
        )

    @staticmethod
    def get_by_email(email):
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()
        db.close()
        return user
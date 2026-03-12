from flask_login import UserMixin

from db import get_db

class User(UserMixin):
    def __init__(self, id_, name, email, profile_pic):
        self.id = id_
        self.name = name
        self.email = email
        self.profile_pic = profile_pic

    @staticmethod
    def get(user_id):
        db = get_db()
        user = db.execute(
            "SELECT * FROM user WHERE id = ?", (user_id,)
        ).fetchone()
        if not user:
            return None

        user = User(
            id_=user[0], name=user[1], email=user[2], profile_pic=user[3]
        )
        return user

    @staticmethod
    def create(id_, name, email, profile_pic):
        db = get_db()
        db.execute(
            "INSERT INTO user (id, name, email, profile_pic) "
            "VALUES (?, ?, ?, ?)",
            (id_, name, email, profile_pic),
        )
        db.commit()

    @staticmethod
    def get_by_email(email):
        db = get_db()
        user = db.execute(
            "SELECT * FROM user WHERE email = ?", (email,)
        ).fetchone()
        if not user:
            return None
        return User(id_=user[0], name=user[1], email=user[2], profile_pic=user[3])

    @staticmethod
    def update_profile(id_, name, profile_pic):
        db = get_db()
        db.execute(
            "UPDATE user SET name = ?, profile_pic = ? WHERE id = ?",
            (name, profile_pic, id_),
        )
        db.commit()
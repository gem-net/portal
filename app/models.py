from datetime import datetime

from flask_login import UserMixin

from app import db, lm


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    display_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(64), nullable=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    in_cgem = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<User {}>'.format(self.email)


@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


db.create_all()

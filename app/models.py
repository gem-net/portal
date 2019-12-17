import logging
from datetime import datetime

from flask_login import UserMixin

from . import db, lm, name_dict


logger = logging.getLogger(__name__)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    use_name = db.Column(db.String(64), nullable=False)
    display_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(64), nullable=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    in_cgem = db.Column(db.Boolean, default=False)
    alt_email_str = db.Column(db.String(255), nullable=True)
    asana_id = db.Column(db.String(64), nullable=True)
    # task_list_id = db.Column(db.String(64), nullable=True)

    def __repr__(self):
        return '<User {}>'.format(self.email)

    @property
    def alt_emails(self):
        """Get list of non-primary emails associated with google ID."""
        if not self.alt_email_str:
            return []
        return self.alt_email_str.split(',')

    def get_official_name(self):
        if self.email in name_dict:
            return name_dict[self.email]
        for email in self.alt_emails:
            if email in name_dict:
                return name_dict[email]
        return 'unknown'

    @property
    def known_emails(self):
        """Get set of all known emails for this user."""
        name_emails = {i for i in name_dict if name_dict[i] == self.use_name}
        return {self.email}.union(set(self.alt_emails)).union(name_emails)


@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


db.create_all()

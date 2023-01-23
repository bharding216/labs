from . import db

class tests(db.Model):
    test_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.String(16000000))
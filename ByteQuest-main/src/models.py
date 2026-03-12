from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False) #TODO: THIS WILL GENERATE THIS AS A SPECIAL KEY TO GET IN
    password = db.Column(db.String(250), nullable=False)
    fname = db.Column(db.String(250), nullable=False)
    lname = db.Column(db.String(250), nullable=False)
    cdate = db.Column(db.String(250), default="none") #completion date

# Dynamically add article progress columns (Chapters 1–12, 3–4 articles each)
for chapter in range(1, 13):
    # example for editing article counts
    if article in (1,2,3): 
        article_count = 2; 
    else:
        artile_count = 3 # i think this is wrong

    #actually adds a column for progress to article_1_1, then 1_2 1_3 2_1 (etc) 
    for article in range(1, article_count + 1):
        col_name = f'article_{chapter}_{article}'
        setattr(Users, col_name, db.Column(db.Integer, default=0)) 

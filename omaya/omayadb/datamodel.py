import os
from peewee import *
import datetime

db = PostgresqlDatabase(os.environ.get('OMAYA_DBNAME', 'omayadb'),
                           user = os.environ.get('OMAYA_DBUSER', 'omaya'),
                           password = os.environ.get('OMAYA_PASSWORD', 'password'),
                           host = os.environ.get('OMAYA_HOST', 'localhost'),
                           port = int(os.environ.get('OMAYA_PORT', '5432')),
                        )

class BaseModel(Model):
    class Meta:
        database = db

def connect():
    if db.is_closed():
        db.connect()

def close():
    if not db.is_closed():
        db.close()

class OmayaLog(BaseModel):
    id = BigAutoField(primary_key=True)
    date = DateTimeField(default=datetime.datetime.now)
    loglevel = CharField()
    logtext = TextField()


def create_tables():
    db.create_tables([OmayaLog,
    ])

def drop_tables():
    db.drop_tables([OmayaLog,
    ])

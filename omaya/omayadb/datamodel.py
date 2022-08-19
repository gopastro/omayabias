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

class OmayaCal(BaseModel):
    id = BigAutoField(primary_key=True)
    date = DateTimeField(default=datetime.datetime.now)
    card_id = IntegerField(default=0)
    sis_ch = IntegerField(default=0)
    sis_slope = DecimalField()
    sis_offset = DecimalField()

    def get_slope_offset(card_id, sis_ch):
        slope = OmayaCal.select(sis_slope).where(OmayaCal.card_id == card_id,
                                                 OmayaCal.sis_ch == sis_ch)
        offset = OmayaCal.select(sis_offset).where(OmayaCal.card_id == card_id,
                                                   OmayaCal.sis_ch == sis_ch)
        return slope, offset


def create_cal_tables():
    db.create_tables([OmayaCal,
    ])

def drop_cal_tables():
    db.drop_tables([OmayaCal,
    ])

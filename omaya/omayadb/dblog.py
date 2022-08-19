from omaya.omayadb.datamodel import OmayaLog, OmayaCal
import datetime
import logging

def logOmaya(loglevel, msg):
    omayalog = OmayaLog(loglevel=logging.getLevelName(loglevel),
                        logtext=msg)
    omayalog.save()

def calOmaya(card_id, sis_ch, sis_slope, sis_offset):
    omayacal = OmayaCal(card_id=card_id,
                        sis_ch=sis_ch,
                        sis_slope=sis_slope,
                        sis_offset=sis_offset)
    omayacal.save()                        

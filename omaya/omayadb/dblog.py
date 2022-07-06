from omaya.omayadb.datamodel import OmayaLog
import datetime
import logging

def logOmaya(loglevel, msg):
    omayalog = OmayaLog(loglevel=logging.getLevelName(loglevel),
                        logtext=msg)
    omayalog.save()

                        

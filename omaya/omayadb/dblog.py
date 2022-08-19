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

def get_sis_slope_offset(card_id, sis_ch):
    try:
        'get the latest value for slope and offset'
        query = OmayaCal.select().where((OmayaCal.card_id==card_id) & (OmayaCal.sis_ch==sis_ch)).order_by(OmayaCal.date.desc()).get()
        print('latest value is:\n')
        print('{}\t {:d}\t {:d}\t {:0.5f}\t {:0.5f}'.format(query.date, query.card_id,
                                                        query.sis_ch,query.sis_slope,
                                                        query.sis_offset))
        slope = query.sis_slope
        offset = query.sis_offset
    except:
        print('Instance does not exist in database. Run mixer_calibration from sweep_test to add values to database')
        slope='N/A'
        offset='N/A'
        pass
    return slope, offset
    

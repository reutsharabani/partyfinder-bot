import datetime
import db
import os
from zoneinfo import ZoneInfo
import random
import logging
import boto3
from boto3.exceptions import Boto3Error

backup_bucket_name = os.environ['BACKUP_BUCKET_NAME']
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('core')


def s3_connection():
    session = boto3.Session(aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                            aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'])
    return session.client('s3')


def to_user_tz(start_t, end_t, user_tz):
    start = datetime.datetime.fromtimestamp(start_t).astimezone(ZoneInfo(user_tz))
    end = datetime.datetime.fromtimestamp(end_t).astimezone(ZoneInfo(user_tz))
    return {"start": str(start),
            "end": str(end),
            "duration": str(end - start)}


def init_user(discord_id, mmr):
    try:
        return db.register(discord_id, mmr)
    except:
        logger.exception(f'failed to register user {discord_id} ')


def relevant_players(discord_id, mmr_diff=1000):
    candidates = sorted(db.relevant_players(discord_id, mmr_diff))
    return random.sample(candidates, k=min(len(candidates), 10))


def update_mmr(discord_id, mmr):
    old_mmr = db.get_mmr(discord_id)
    db.update_mmr(discord_id, mmr)
    return old_mmr


def backup():
    backup_id = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    try:
        db.backup(backup_id)
        s3_connection().upload_file(backup_id, backup_bucket_name, backup_id)
    except Boto3Error as e:
        logger.error(e)
        return "backup failed"
    finally:
        try:
            os.remove(backup_id)
        except:
            pass
    return "backup done %s" % backup_id


def backups():
    resp = s3_connection().list_objects_v2(Bucket=backup_bucket_name)
    for obj in resp['Contents']:
        yield obj['Key']


def restore(backup_name):
    db.close_connection()
    s3_connection().download_file(backup_bucket_name, backup_name, db.db_file_name)
    db.open_connection()
    return 'restored from %s' % backup_name

import datetime
import logging
import os

import boto3
from boto3.exceptions import Boto3Error

import db

backup_bucket_name = os.environ['BACKUP_BUCKET_NAME']
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('s3')


def s3_connection():
    session = boto3.Session(aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                            aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'])
    return session.client('s3')


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

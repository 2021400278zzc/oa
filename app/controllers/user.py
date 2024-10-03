import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Literal

from flask import current_app as app
from tencentcloud.common import credential
from tencentcloud.sms.v20210111 import models, sms_client

from app.models.member import Member
from app.models.verification import Verification
from app.utils.constant import ResponseConstant as R
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.utils import is_value_valid


@Log.track_execution()
def info(id):
    with CRUD(Member, id=id) as u:
        if query := u.query_key():
            info = query.first()
            return info.to_dict()
    return None

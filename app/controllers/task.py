# 日报控制器
import os
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urljoin
from uuid import uuid4

from flask import current_app as app
from PIL import Image
from werkzeug.datastructures import FileStorage

from app.models.llm_record import LLMRecord
from app.models.member import Member
from app.models.period_task import PeriodTask
from app.utils.constant import LocalPath as Local
from app.utils.constant import ResponseConstant as R
from app.utils.constant import UrlTemplate as Url
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.utils import is_value_valid
from config.development import Config


@Log.track_execution(when_error=R.CODE_INTERNAL_SERVER)
def create_task(
    assigner_id: str,
    assignee_id: str,
    start_time: str,
    end_time: str,
    basic_task: str,
    detail_task: str,
) -> int:
    start_date = process_datetime(start_time)
    end_date = process_datetime(end_time)

    assigner_info = CRUD(Member, id=assigner_id).query_key().first()
    assignee_info = CRUD(Member, id=assignee_id).query_key().first()

    if assignee_info.department_id != assigner_info.department_id:
        return R.CODE_CONFLICTION

    with CRUD(
        PeriodTask,
        assigner_id=assigner_id,
        assignee_id=assignee_id,
        start_time=start_date,
        end_time=end_date,
        basic_task_requirements=basic_task,
        detail_task_requirements=detail_task,
        updated_by=assigner_info.name,
    ) as task:
        if not task.add():
            return R.CODE_INTERNAL_SERVER

    return R.CODE_OK


@Log.track_execution(when_error=R.CODE_INTERNAL_SERVER)
def modify_task(
    updater_id: str,
    task_id: str,
    start_time: str,
    end_time: str,
    basic_task: str,
    detail_task: str,
) -> int:
    start_date = process_datetime(start_time)
    end_date = process_datetime(end_time)

    updater_info = CRUD(Member, id=updater_id).query_key().first()

    with CRUD(PeriodTask, task_id=task_id) as t:
        updated = t.update(
            start_time=start_date,
            end_time=end_date,
            basic_task_requirements=basic_task,
            detail_task_requirements=detail_task,
            updated_by=updater_info.name,
        )

    if not updated:
        return R.CODE_INTERNAL_SERVER

    return R.CODE_OK


# TODO
@Log.track_execution(when_error=R.CODE_INTERNAL_SERVER)
def generate_task(user_id: str, text: str):

    received_text = ...

    with CRUD(
        LLMRecord, user_id=user_id, request_text=text, received_text=received_text
    ) as llm:
        llm.add()

    return R.CODE_OK


# js_datetime: 20yy-mm-ddT15:30:00
def process_datetime(js_datetime: str) -> datetime:
    utc_offset = Config.UTC_OFFSET

    local_date = datetime.strptime(js_datetime, "%Y-%m-%dT%H:%M:%S")
    local_timezone = timezone(timedelta(hours=utc_offset))
    local_timezone_date = local_date.replace(tzinfo=local_timezone)

    utc_date = local_timezone_date.astimezone(timezone.utc)

    return utc_date

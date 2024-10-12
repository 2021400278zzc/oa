# 日报控制器
import os
from datetime import datetime
from uuid import uuid4

from PIL import Image
from werkzeug.datastructures import FileStorage

from app.models.daily_report import DailyReport
from app.models.llm_record import LLMRecord
from app.models.period_task import PeriodTask
from app.modules.pool import submit_task
from app.utils.constant import LLMTemplate as LLM
from app.utils.constant import LocalPath as Local
from app.utils.constant import ResponseConstant as R
from app.utils.constant import UrlTemplate as Url
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.utils import Timer
from config.development import Config


@Log.track_execution(when_error="")
def create_report(id: str, text: str, pictures: list[FileStorage]) -> str:
    """创建日报，并将图片唯一命名以PNG方式保存至本地
    Args:
        id (str): 用户id
        text (str): 日报内容
        pictures (list[FileStorage]): 图片的form数据，以列表方式传入
    Returns:
        str: 成功时返回日报的唯一id，失败则返回空字符串
    """

    picture_urls, picture_paths = save_pictures(pictures)

    with CRUD(
        DailyReport,
        user_id=id,
        report_text=text,
        report_picture=picture_urls,
        generating=True,
    ) as report:
        instance = report.add()

    delay_time = Timer(minutes=Config.REPORT_GENERATE_DELAY_MINS)
    submit_task(
        generate_report_review, instance.report_id, picture_paths, delay=delay_time
    )

    return instance.report_id


@Log.track_execution(when_error=False)
def update_report(
    id: str, report_id: str, text: str, pictures: list[FileStorage]
) -> bool:
    """暂未使用（未计划的）"""

    picture_urls, _ = save_pictures(pictures)

    with CRUD(DailyReport, id=report_id) as u:
        u.update(report_text=text, report_picture=picture_urls)

    return True


def save_pictures(pictures: list[FileStorage]) -> tuple[list, list]:
    """使用uuid作为文件名将网络图片保存至本地

    Args:
        pictures (list[FileStorage]): 上传的网络图片

    Returns:
        tuple[list, list]: 返回元组，图片url与图片路径
    """
    picture_urls = []
    picture_paths = []

    for picture in pictures:
        uuid = str(uuid4())
        picture_urls.append(Url.REPORT_PICTURE(uuid))

        filename = os.path.join(Local.REPORT_PICTURE, uuid)
        picture_paths.append(filename)
        try:
            Image.open(picture).convert("RGB").save(filename, "PNG")
        except:
            picture.save(filename)

    return picture_urls, picture_paths


@Log.track_execution()
def generate_report_review(report_id: str, picture_path: list[str]) -> None:
    if not (q_report := CRUD(DailyReport, report_id=report_id).query_key()):
        raise FileNotFoundError(
            "task generate_report_review: 无法找到指定用户的日报记录。"
        )
    report: DailyReport = q_report.first()

    if not (q_task := CRUD(PeriodTask, assignee_id=report.user_id).query_key()):
        raise FileNotFoundError(
            "task generate_report_review: 无法找到指定用户的任务记录。"
        )
    task: PeriodTask = q_task.first()

    task_days = (task.end_time - task.start_time).day
    elapsed_days = datetime.now() - task.start_timeq
    previous_task_describe = task.completed_task_description
    daily_task = report.daily_task
    daily_report = report.report_text

    prompt = LLM.DAILY_REPORT_REVIEW(
        daily_task, task_days, elapsed_days, previous_task_describe, daily_report
    )

    # TODO:Picture path, Access GPT

    reply = ""

    with CRUD(
        LLMRecord,
        user_id=report.user_id,
        method="report",
        request_text=prompt,
        received_text=reply,
    ) as record:
        record.add()

    LLM.DAILY_REPORT_REVIEW_SUMMARY(reply)

    with CRUD() as u:
        u.update(report, report)

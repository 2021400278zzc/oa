# 任务计划
import os
from datetime import datetime

from app.controllers.report import generate_report_review
from app.models.daily_report import DailyReport
from app.models.period_task import PeriodTask
from app.modules.llm import create_completion
from app.modules.pool import submit_task
from app.utils.constant import LLMPrompt as LLM
from app.utils.constant import LLMStructure as LLMS
from app.utils.constant import LocalPath as Local
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.response import Response
from app.utils.utils import Timer
from config import Config


@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def check_daily_report() -> Response:
    """检查是否有未完成的日报"""
    # 计算前一天UTC的开始时间与结束时间
    yesterday_date = datetime.now().day - 1
    today_start = Timer.date_to_utc(
        Config.TIMEZONE, day=yesterday_date, hour=0, minute=0, second=0
    )
    today_end = Timer.date_to_utc(
        Config.TIMEZONE, day=yesterday_date, hour=23, minute=59, second=59
    )

    with CRUD(DailyReport) as report:
        if not (
            query := report.query_key(
                report.model.created_at > today_start,
                report.model.created_at < today_end,
                report.model.report_review == None,
            )
        ):
            Log.info("检查日报已中止，因为并未找到任何项")
            return Response(Response.r.OK)
        delay = 0
        for rep in query.all():
            image_path = [
                os.path.join(Local.REPORT_PICTURE, pic.split("/")[-1])
                for pic in rep.report_picture
            ]
            submit_task(
                generate_report_review,
                rep.report_id,
                image_path,
                delay=Timer(minutes=delay),
            )
            delay += 1

    return Response(Response.r.OK)


@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def daily_generation() -> Response:
    """生成每日任务，以及任务进度报告"""
    with CRUD(PeriodTask) as task:
        if not (query := task.query_key(task.model.end_time >= Timer.utc_now())):
            Log.info("生成任务已中止，因为并未找到任何项")
            return Response(Response.r.ERR_NOT_FOUND)
        task.need_update()
        tasks: list[PeriodTask] = query.all()
        # 对每个任务进行处理
        for t in tasks:
            # 获取LLM需要使用的必要元数据
            basic = t.basic_task_requirements
            detail = t.detail_task_requirements
            completed = t.completed_task_description
            days = (t.end_time - t.start_time).day
            elapsed = (Timer.utc_now() - t.start_time).day
            remaining = (t.end_time - Timer.utc_now()).day

            daily_task, daily_review = None, None

            with CRUD(DailyReport, user_id=t.assignee_id) as r:
                if q_report := r.query_key():
                    report = q_report.order_by(r.model.created_at.desc()).first()
                    daily_task = report.daily_task
                    daily_review = report.report_review

            prompt = LLM.DAILY_SUMMARY(
                basic,
                detail,
                days,
                elapsed,
                remaining,
                completed,
                daily_task,
                daily_review,
            )

            # 操作LLM
            reply = create_completion(
                prompt,
                t.assignee_id,
                "task",
                dictionary_like=True,
                response_format=LLMS.DailySummary,
            )

            completion = reply.get("completion_status")
            next_task = reply.get("next_task")

            # 将内容存入各自的模型中
            t.completed_task_description = completion
            with CRUD(DailyReport) as r:
                if not r.add(user_id=t.assignee_id, daily_task=next_task):
                    Log.error(r.error)
                    return Response(Response.r.ERR_SQL)

    return Response(Response.r.OK)

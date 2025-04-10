# 日报控制器
import os
from datetime import datetime
from uuid import uuid4

from PIL import Image
from werkzeug.datastructures import FileStorage

from app.models.daily_report import DailyReport
from app.models.period_task import PeriodTask
from app.modules.llm import create_completion
from app.modules.pool import submit_task
from app.utils.constant import LLMPrompt as LLM
from app.utils.constant import LLMStructure as LLMS
from app.utils.constant import LocalPath as Local
from app.utils.constant import UrlTemplate as Url
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.response import Response
from app.utils.utils import Timer
from config import Config

def generate_unique_id() -> str:
    """
    生成一个随机唯一 ID，基于 UUID4。
    Returns:
        str: UUID4 唯一标识符
    """
    return str(uuid4())  # 转为字符串

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def create_daily_report(
    user_id: str, report_text: str, pictures: list[FileStorage]
) -> Response:
    """
    创建日报，并将上传的附件唯一命名并保存至本地。
    尽管指明是创建日报，但实际生成时间为每日的固定时间点（例如 0:30）。

    Args:
        user_id (str): 用户 ID
        report_text (str): 日报内容
        attachments (list[FileStorage]): 上传的附件列表
    Returns:
        Response: 成功返回包含日报 ID 的响应，失败返回错误信息
    """

    # 保存附件到本地，并获取对应的 URL 和文件路径
    picture_urls, picture_paths = save_pictures(pictures)

    # 为日报生成唯一 ID（可以使用 UUID 或其他方法生成）
    report_id = generate_unique_id()

    # 使用 CRUD 操作保存日报信息
    with CRUD(DailyReport, user_id=user_id, report_id=report_id) as report:
        if not report.update(
            user_id=user_id,
            report_id=report_id,
            report_text=report_text,
            report_picture=picture_urls,
            generating=True
        ):
            return Response(Response.r.ERR_SQL)

    # 设置生成日报的延迟时间
    delay_time = Timer(minutes=Config.REPORT_GENERATE_DELAY_MINS)

    # 提交后台任务，用于生成日报的审核
    submit_task(generate_report_review, report_id, picture_paths, delay=delay_time)

    return Response(Response.r.OK, data=report_id)

@Log.track_execution(when_error=Response(Response.r.ERR_INTERNAL))
def create_report(
    user_id: str, report_text: str, pictures: list[FileStorage]
) -> Response:
    """填写日报，并将图片唯一命名以PNG方式保存至本地。
    Args:
        user_id (str): 用户id
        report_text (str): 日报内容
        pictures (list[FileStorage]): 图片的form数据，以列表方式传入
    Returns:
        str: 成功时返回日报的唯一id，失败则返回空字符串
    """
    try:
        # 自动生成report_id
        report_id = str(uuid4())
        
        # 保存图片
        picture_urls, picture_paths = save_pictures(pictures)
        
        # 获取用户当前的所有任务信息
        now = datetime.now()
        with CRUD(PeriodTask) as crud:
            current_tasks = crud.query_key(
                assignee_id=user_id
            )
            if current_tasks:
                current_tasks = current_tasks.filter(
                    PeriodTask.start_time <= now,
                    PeriodTask.end_time >= now
                )
            
            if not current_tasks or current_tasks.count() == 0:
                return Response(Response.r.ERR_NOT_FOUND, message="未找到用户当前任务")

            # 获取所有当前任务
            tasks = current_tasks.all()
            Log.info(f"用户当前任务数量: {len(tasks)}")

            # 合并所有任务的信息
            combined_task_requirements = []
            combined_completed_tasks = []
            max_days = 0  # 使用最长的任务周期
            earliest_start = now
            latest_end = now

            # 收集所有任务的信息
            for task in tasks:
                # 合并任务要求
                if task.basic_task_requirements:
                    combined_task_requirements.append(task.basic_task_requirements)
                # 合并已完成内容
                if task.completed_task_description:
                    combined_completed_tasks.append(task.completed_task_description)
                # 更新时间范围
                if task.start_time < earliest_start:
                    earliest_start = task.start_time
                if task.end_time > latest_end:
                    latest_end = task.end_time

            # 计算最长任务周期
            total_days = (latest_end - earliest_start).days
            elapsed_days = (now - earliest_start).days

            # 组合任务信息为统一描述
            combined_requirements = "\n".join([
                f"任务 {i+1}: {req}" 
                for i, req in enumerate(combined_task_requirements)
            ])
            combined_completed = "\n".join([
                f"任务 {i+1} 已完成: {comp}" 
                for i, comp in enumerate(combined_completed_tasks) if comp
            ])
            
            # 使用 GPT 生成日报评价
            review_prompt = LLM.DAILY_REPORT_REVIEW_JSON(
                combined_requirements,       # 合并后的所有任务描述
                total_days,                 # 使用最长的任务周期
                elapsed_days,               # 已经过的时间
                combined_completed,         # 合并后的已完成内容
                "",                        # 今日任务（暂无）
                report_text                # 今日完成情况
            )
            
            # 生成评价，包含图片路径
            review = create_completion(
                send_text=review_prompt,
                user_id=user_id,
                method="report",
                send_images=picture_paths,     # 添加图片路径
                dictionary_like=True,
                response_format=LLMS.DailyReport,
                model_type="deepseek"
            )

            # 创建新的日报记录，包含评价信息和所有关联的任务ID
            with CRUD(DailyReport) as crud:
                if not crud.add(crud.create_instance(),
                    user_id=user_id,
                    report_id=report_id,
                    report_text=report_text,
                    report_picture=picture_urls,
                    task_ids=[task.task_id for task in tasks],  # 保存所有相关任务的ID
                    report_review=review,            # 保存完整的评价
                    basic_score=review['basic']['score'],    # 基本分
                    excess_score=review['excess']['score'],  # 超额分
                    extra_score=review['extra']['score'],    # 额外分
                    efficiency=review['efficiency']['score'],   # 效率
                    innovation=review['innovation']['score'],   # 创新性
                    generating=False                 # 评价已生成
                ):
                    return Response(Response.r.ERR_SQL)

        return Response(Response.r.OK, data=report_id)

    except Exception as e:
        Log.error(f"Error in create_report: {str(e)}")
        try:
            # 如果出错但 report_id 已生成，创建一个待评价的日报
            if 'report_id' in locals():
                with CRUD(DailyReport) as crud:
                    if crud.add(crud.create_instance(),
                        user_id=user_id,
                        report_id=report_id,
                        report_text=report_text,
                        report_picture=picture_urls if 'picture_urls' in locals() else [],
                        task_ids=[task.task_id for task in tasks] if 'tasks' in locals() else [],
                        generating=True  # 标记为正在生成
                    ):
                        return Response(Response.r.OK, data=report_id)
        except Exception as inner_e:
            Log.error(f"Error in fallback creation: {str(inner_e)}")
        
        return Response(Response.r.ERR_INTERNAL)


def save_pictures(pictures: list[FileStorage]) -> tuple[list, list]:
    """使用uuid作为文件名将网络图片保存至本地
    Args:
        pictures (list[FileStorage]): 上传的网络图片
    Returns:
        tuple[list, list]: 返回元组，图片url与图片路径
    """
    picture_urls = []
    picture_paths = []

    if pictures:
        for picture in pictures:
            if picture and picture.filename:
                try:
                    # 生成唯一的文件名
                    uuid = str(uuid4())
                    picture_urls.append(Url.REPORT_PICTURE(uuid))

                    # 确保目录存在
                    os.makedirs(Local.REPORT_PICTURE, exist_ok=True)
                    
                    # 构建完整的文件路径
                    filename = os.path.join(Local.REPORT_PICTURE, uuid)
                    picture_paths.append(filename)
                    
                    # 保存图片
                    try:
                        with Image.open(picture) as img:
                            # 转换为 RGB 模式（如果不是的话）
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            # 保存为 PNG
                            img.save(filename, "PNG", optimize=True)
                    except Exception as e:
                        Log.error(f"Error processing image with PIL: {str(e)}")
                        # 如果 PIL 处理失败，直接保存原始文件
                        picture.save(filename)
                        
                except Exception as e:
                    Log.error(f"Error saving picture: {str(e)}")
                    continue

    return picture_urls, picture_paths


@Log.track_execution(when_error=False)
def update_report(
    user_id: str, report_id: str, text: str, pictures: list[FileStorage]
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
    """生成日报评价并传入至数据库中

    Args:
        report_id (str): 日报id
        picture_path (list[str]): 图片本地路径

    Raises:
        所有错误最终会被写入至日志
    """
    if not (q_report := CRUD(DailyReport, report_id=report_id).query_key()):
        raise FileNotFoundError(
            "report generate_report_review: 无法找到指定用户的日报记录。"
        )
    report: DailyReport = q_report.first()

    with CRUD(PeriodTask, assignee_id=report.user_id) as i_task:
        if not (
            q_task := i_task.query_key(
                i_task.model.start_time < report.created_at,
                i_task.model.end_time > report.created_at,
            )
        ):
            raise FileNotFoundError(
                "task generate_report_review: 无法找到指定用户的任务记录。"
            )
    task: PeriodTask = q_task.first()

    task_days = (task.end_time - task.start_time).day
    elapsed_days = datetime.now() - task.start_time
    previous_task_describe = task.completed_task_description
    daily_task = report.daily_task
    daily_report = report.report_text

    review_prompt = LLM.DAILY_REPORT_REVIEW_JSON(
        daily_task, task_days, elapsed_days, previous_task_describe, daily_report
    )

    review = create_completion(
        review_prompt,
        report.user_id,
        "report",
        picture_path,
        dictionary_like=True,
        response_format=LLMS.DailyReport,
    )

    with CRUD(DailyReport, report_id=report_id) as s:
        s.update(
            report_review=review,
            basic_score=review["basic"]["score"],
            excess_score=review["excess"]["score"],
            extra_score=review["extra"]["score"],
            generating=False,
        )

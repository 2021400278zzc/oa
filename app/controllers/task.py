from app.models.member import Member
from app.models.period_task import PeriodTask
from app.modules.llm import create_completion
from app.utils.constant import LLMTemplate as LLM
from app.utils.constant import ResponseConstant as R
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.utils import Timer


@Log.track_execution(when_error=R.CODE_INTERNAL_SERVER)
def create_task(
    assigner_id: str,
    assignee_id: str,
    start_time: str,
    end_time: str,
    basic_task: str,
    detail_task: str,
) -> int:
    """为用户创建任务
    Args:
        assigner_id (str): 任务创建者id
        assignee_id (str): 任务接受者id
        start_time (str): 任务开始时间
        end_time (str): 任务结束时间
        basic_task (str): 任务基本概述
        detail_task (str): 任务详细内容
    Returns:
        int: 响应码
    """
    # 将js日期转为utc时间
    start_date = Timer.js_to_utc(start_time)
    end_date = Timer.js_to_utc(end_time)

    # 获取双方信息
    assigner_info = CRUD(Member, id=assigner_id).query_key().first()
    assignee_info = CRUD(Member, id=assignee_id).query_key().first()

    # 如果组别不匹配，则返回冲突错误
    if assignee_info.department_id != assigner_info.department_id:
        return R.CODE_CONFLICTION

    # 查找是否存在任务的结束时间大于现在任务开始时间的项，即是否存在未结束的任务
    with CRUD(PeriodTask, assignee_id=assignee_id) as q_period:
        if q_period.query_key(q_period.model.end_time > start_time):
            return R.CODE_CONFLICTION

    # 更新任务信息
    with CRUD(
        PeriodTask,
        assigner_id=assigner_id,
        assignee_id=assignee_id,
        start_time=start_date,
        end_time=end_date,
        basic_task_requirements=basic_task,
        detail_task_requirements=detail_task,
        updated_by=assigner_id,
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
    start_date = Timer.js_to_utc(start_time)
    end_date = Timer.js_to_utc(end_time)

    updater_info = CRUD(Member, id=updater_id).query_key().first()

    with CRUD(PeriodTask, task_id=task_id) as t:
        updated = t.update(
            start_time=start_date,
            end_time=end_date,
            basic_task_requirements=basic_task,
            detail_task_requirements=detail_task,
            updated_by=updater_id,
        )

    if not updated:
        return R.CODE_INTERNAL_SERVER

    return R.CODE_OK


@Log.track_execution(when_error=R.CODE_INTERNAL_SERVER)
def generate_task(
    assigner_id: str, assignee_id: str, start_time: str, end_time: str, basic_task: str
) -> int | str:
    """使用LLM由任务概述生成详细任务
    Args:
        assigner_id (str): 生成任务者id
        assignee_id (str): 任务接受者id
        start_time (str): 开始时间，js字符串
        end_time (str): 结束时间，js字符串
        basic_task (str): 基本任务概述
    Returns:
        (int | str): 返回错误码或LLM回复
    """
    if not (q_assignee := CRUD(Member, id=assignee_id).query_key()):
        return R.CODE_NOT_FOUND

    assignee: Member = q_assignee.first()

    department = assignee.department.name
    if parent_department := assignee.department.parent.name:
        department = f"{parent_department}-{department}"
    days = (Timer.js_to_utc(start_time) - Timer.js_to_utc(end_time)).days

    task_prompt = LLM.TASK_GENERATION(department, basic_task, days)
    received_task = create_completion(task_prompt, assigner_id, "task")

    return received_task

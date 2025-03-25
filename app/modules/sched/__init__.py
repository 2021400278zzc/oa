# 注意: 文件名与类名不匹配
# daily_task_sched.py 中实际包含 PeriodTaskScheduler 类
# period_task_sched.py 中实际包含 DailyTaskScheduler 类
from app.modules.sched.daily_task_sched import PeriodTaskScheduler
from app.modules.sched.period_task_sched import DailyTaskScheduler
from app.modules.sched.ability_assessment_sched import AbilityAssessmentScheduler
from app.modules.sched.member_score_sched import MemberScoreScheduler

def init_schedulers(app):
    """初始化所有定时任务调度器"""
    # 初始化每日任务调度器 (实际在 period_task_sched.py 中)
    daily_task_scheduler = DailyTaskScheduler(app)
    
    # 初始化周期任务得分计算调度器 (实际在 daily_task_sched.py 中)
    period_task_scheduler = PeriodTaskScheduler(app)
    
    # 初始化能力评估调度器
    ability_assessment_scheduler = AbilityAssessmentScheduler(app)
    
    # 初始化成员得分更新调度器
    member_score_scheduler = MemberScoreScheduler(app)
    
    return {
        'daily_task': daily_task_scheduler,
        'period_task': period_task_scheduler,
        'ability_assessment': ability_assessment_scheduler,
        'member_score': member_score_scheduler
    }

from flask import Blueprint, jsonify, current_app
from app.utils.auth import require_role
from app.utils.constant import DataStructure as D
from app.utils.response import Response
import logging
from datetime import datetime

# 创建调度器任务蓝图
scheduler_bp = Blueprint("scheduler", __name__, url_prefix="/api/scheduler")

# 注意：调度器类的导入已移至各个函数内部
# 这样可以避免循环导入问题

# def get_schedulers():
#     """从应用上下文获取调度器实例"""
#     # 使用Flask的应用上下文获取调度器实例
#     app = current_app._get_current_object()
    
#     # 尝试从app.schedulers字典获取调度器实例
#     period_task_scheduler = None
#     daily_task_scheduler = None
    
#     if hasattr(app, 'schedulers'):
#         period_task_scheduler = app.schedulers.get('period_task', None)
#         daily_task_scheduler = app.schedulers.get('daily_task', None)
#         if period_task_scheduler and daily_task_scheduler:
#             logging.info("从app.schedulers成功获取调度器实例")
#             return period_task_scheduler, daily_task_scheduler
    
#     # 如果从app.schedulers获取失败，尝试从应用对象直接获取
#     period_task_scheduler = getattr(app, 'period_task_scheduler', None)
#     daily_task_scheduler = getattr(app, 'daily_task_scheduler', None)
    
#     # 如果应用对象没有存储调度器实例，尝试全局查找
#     if not period_task_scheduler:
#         try:
#             from run import period_task_scheduler as global_period_scheduler
#             period_task_scheduler = global_period_scheduler
#         except (ImportError, AttributeError):
#             logging.warning("无法导入全局周期任务调度器实例")
    
#     if not daily_task_scheduler:
#         try:
#             from run import daily_task_scheduler as global_daily_scheduler
#             daily_task_scheduler = global_daily_scheduler
#         except (ImportError, AttributeError):
#             logging.warning("无法导入全局每日任务调度器实例")
    
#     return period_task_scheduler, daily_task_scheduler

@scheduler_bp.route('/direct/score-calculation', methods=['POST'])
@require_role(D.admin, D.leader)  # 只允许管理员和组长访问
def direct_run_score_calculation(user_id: str):
    """直接执行周期任务评分计算核心逻辑，不依赖调度器实例"""
    try:
        # 直接创建PeriodTaskScheduler实例并使用其核心方法
        from app.modules.sched.daily_task_sched import PeriodTaskScheduler
        from flask import current_app
        
        app = current_app._get_current_object()
        # 创建临时实例，但不启动调度器
        temp_scheduler = PeriodTaskScheduler(app)
        
        # 直接执行评分计算逻辑
        with app.app_context():
            temp_scheduler.auto_calculate_period_task_scores()
        
        return jsonify({
            "code": Response.r.OK,
            "message": "直接执行周期任务评分计算成功",
            "data": {"executed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            "status": "OK"
        })
    except Exception as e:
        logging.error(f"直接执行周期任务评分计算失败: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": f"直接执行周期任务评分计算失败: {str(e)}",
            "data": None,
            "status": "ERROR"
        }), 500

@scheduler_bp.route('/direct/task-generation', methods=['POST'])
@require_role(D.admin, D.leader)  # 只允许管理员和组长访问
def direct_run_task_generation(user_id: str):
    """直接执行每日任务生成核心逻辑，不依赖调度器实例"""
    try:
        # 直接创建DailyTaskScheduler实例并使用其核心方法
        from app.modules.sched.period_task_sched import DailyTaskScheduler
        from flask import current_app
        from datetime import datetime
        
        app = current_app._get_current_object()
        # 创建临时实例，但不启动调度器
        temp_scheduler = DailyTaskScheduler(app)
        
        # 直接执行任务生成逻辑
        with app.app_context():
            temp_scheduler.generate_daily_tasks()
        
        return jsonify({
            "code": Response.r.OK,
            "message": "直接执行每日任务生成成功",
            "data": {"executed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            "status": "OK"
        })
    except Exception as e:
        logging.error(f"直接执行每日任务生成失败: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": f"直接执行每日任务生成失败: {str(e)}",
            "data": None,
            "status": "ERROR"
        }), 500

@scheduler_bp.route('/direct/ability-assessment', methods=['POST'])
@require_role(D.admin, D.leader)  # 只允许管理员和组长访问
def direct_run_ability_assessment(user_id: str):
    """直接执行能力评估核心逻辑，不依赖调度器实例"""
    try:
        # 直接创建AbilityAssessmentScheduler实例并使用其核心方法
        from app.modules.sched.ability_assessment_sched import AbilityAssessmentScheduler
        from flask import current_app
        
        app = current_app._get_current_object()
        # 创建临时实例，但不启动调度器
        temp_scheduler = AbilityAssessmentScheduler(app)
        
        # 直接执行能力评估逻辑
        with app.app_context():
            result = temp_scheduler.run_assessment_now()
        
        return jsonify({
            "code": Response.r.OK,
            "message": "直接执行能力评估成功",
            "data": {
                "executed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "result": result
            },
            "status": "OK"
        })
    except Exception as e:
        logging.error(f"直接执行能力评估失败: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": f"直接执行能力评估失败: {str(e)}",
            "data": None,
            "status": "ERROR"
        }), 500

@scheduler_bp.route('/direct/member-score-update', methods=['POST'])
@require_role(D.admin, D.leader)  # 只允许管理员和组长访问
def direct_run_member_score_update(user_id: str):
    """直接执行成员得分更新核心逻辑，不依赖调度器实例"""
    try:
        # 直接创建MemberScoreScheduler实例并使用其核心方法
        from app.modules.sched.member_score_sched import MemberScoreScheduler
        from flask import current_app
        
        app = current_app._get_current_object()
        # 创建临时实例，但不启动调度器
        temp_scheduler = MemberScoreScheduler(app)
        
        # 直接执行成员得分更新逻辑
        with app.app_context():
            temp_scheduler._update_member_scores()
        
        return jsonify({
            "code": Response.r.OK,
            "message": "直接执行成员得分更新成功",
            "data": {"executed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            "status": "OK"
        })
    except Exception as e:
        logging.error(f"直接执行成员得分更新失败: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": f"直接执行成员得分更新失败: {str(e)}",
            "data": None,
            "status": "ERROR"
        }), 500

@scheduler_bp.route('/direct/daily-task-notification', methods=['POST'])
@require_role(D.admin, D.leader)  # 只允许管理员和组长访问
def direct_run_daily_task_notification(user_id: str):
    """直接执行每日任务通知发送逻辑，不依赖调度器实例"""
    try:
        # 直接创建NotificationScheduler实例并使用其核心方法
        from app.modules.sched.notification_sched import NotificationScheduler
        from flask import current_app
        
        app = current_app._get_current_object()
        # 创建临时实例，但不启动调度器
        temp_scheduler = NotificationScheduler(app)
        
        # 直接执行通知发送逻辑
        with app.app_context():
            temp_scheduler.send_daily_task_notifications()
        
        return jsonify({
            "code": Response.r.OK,
            "message": "直接执行每日任务通知发送成功",
            "data": {"executed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            "status": "OK"
        })
    except Exception as e:
        logging.error(f"直接执行每日任务通知发送失败: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": f"直接执行每日任务通知发送失败: {str(e)}",
            "data": None,
            "status": "ERROR"
        }), 500

@scheduler_bp.route('/direct/daily-report-reminder', methods=['POST'])
@require_role(D.admin, D.leader)  # 只允许管理员和组长访问
def direct_run_daily_report_reminder(user_id: str):
    """直接执行日报填写提醒通知发送逻辑，不依赖调度器实例"""
    try:
        # 直接创建NotificationScheduler实例并使用其核心方法
        from app.modules.sched.notification_sched import NotificationScheduler
        from flask import current_app
        
        app = current_app._get_current_object()
        # 创建临时实例，但不启动调度器
        temp_scheduler = NotificationScheduler(app)
        
        # 直接执行通知发送逻辑
        with app.app_context():
            temp_scheduler.send_daily_report_reminder()
        
        return jsonify({
            "code": Response.r.OK,
            "message": "直接执行日报填写提醒通知发送成功",
            "data": {"executed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            "status": "OK"
        })
    except Exception as e:
        logging.error(f"直接执行日报填写提醒通知发送失败: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": f"直接执行日报填写提醒通知发送失败: {str(e)}",
            "data": None,
            "status": "ERROR"
        }), 500

@scheduler_bp.route('/direct/clean-expired-notifications', methods=['POST'])
@require_role(D.admin, D.leader)  # 只允许管理员和组长访问
def direct_run_notification_cleanup(user_id: str):
    """直接执行过期通知清理逻辑，不依赖调度器实例"""
    try:
        # 直接创建NotificationScheduler实例并使用其核心方法
        from app.modules.sched.notification_sched import NotificationScheduler
        from flask import current_app
        
        app = current_app._get_current_object()
        # 创建临时实例，但不启动调度器
        temp_scheduler = NotificationScheduler(app)
        
        # 直接执行通知清理逻辑
        with app.app_context():
            temp_scheduler.clean_expired_notifications()
        
        return jsonify({
            "code": Response.r.OK,
            "message": "直接执行过期通知清理成功",
            "data": {"executed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            "status": "OK"
        })
    except Exception as e:
        logging.error(f"直接执行过期通知清理失败: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": f"直接执行过期通知清理失败: {str(e)}",
            "data": None,
            "status": "ERROR"
        }), 500

@scheduler_bp.route('/direct/progress-notification', methods=['POST'])
@require_role(D.admin, D.leader)  # 只允许管理员和组长访问
def direct_run_progress_notification(user_id: str):
    """直接执行进度通知发送逻辑，不依赖调度器实例"""
    try:
        # 直接创建ProgressNotificationScheduler实例并使用其核心方法
        from app.modules.sched.progress_notification_sched import ProgressNotificationScheduler
        from flask import current_app
        
        app = current_app._get_current_object()
        # 创建临时实例，但不启动调度器
        temp_scheduler = ProgressNotificationScheduler(app)
        
        # 直接执行通知发送逻辑
        with app.app_context():
            success = temp_scheduler.run_notification_now()
        
        if success:
            return jsonify({
                "code": Response.r.OK,
                "message": "直接执行进度通知发送成功",
                "data": {"executed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                "status": "OK"
            })
        else:
            return jsonify({
                "code": Response.r.ERR_INTERNAL,
                "message": "执行进度通知发送失败",
                "data": None,
                "status": "ERROR"
            }), 500
            
    except Exception as e:
        logging.error(f"直接执行进度通知发送失败: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": f"直接执行进度通知发送失败: {str(e)}",
            "data": None,
            "status": "ERROR"
        }), 500

@scheduler_bp.route('/direct/force-progress-check', methods=['POST'])
@require_role(D.admin, D.leader)  # 只允许管理员和组长访问
def direct_force_progress_check(user_id: str):
    """强制执行进度检查和更新逻辑（不受时间限制），仅供管理员和组长使用"""
    try:
        # 直接创建ProgressNotificationScheduler实例并使用其核心方法
        from app.modules.sched.progress_notification_sched import ProgressNotificationScheduler
        from flask import current_app
        from datetime import datetime
        
        app = current_app._get_current_object()
        # 创建临时实例，但不启动调度器
        temp_scheduler = ProgressNotificationScheduler(app)
        
        # 直接执行进度检查和更新逻辑
        with app.app_context():
            success = temp_scheduler.run_check_and_notification_now()
        
        if success:
            return jsonify({
                "code": Response.r.OK,
                "message": "强制执行进度检查和更新成功",
                "data": {
                    "executed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "check_type": "force"
                },
                "status": "OK"
            })
        else:
            return jsonify({
                "code": Response.r.ERR_INTERNAL,
                "message": "强制执行进度检查和更新失败",
                "data": None,
                "status": "ERROR"
            }), 500
            
    except Exception as e:
        logging.error(f"强制执行进度检查和更新失败: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": f"强制执行进度检查和更新失败: {str(e)}",
            "data": None,
            "status": "ERROR"
        }), 500

@scheduler_bp.route('/direct/batch-progress-update', methods=['POST'])
@require_role(D.admin)  # 只允许管理员访问
def direct_run_batch_progress_update(user_id: str):
    """直接执行批量进度更新逻辑，不依赖调度器实例"""
    try:
        from app.modules.sched.progress_notification_sched import ProgressNotificationScheduler
        from flask import current_app, request
        
        # 获取请求参数
        data = request.get_json()
        if not data:
            return jsonify({
                "code": Response.r.ERR_INVALID_ARGUMENT,
                "message": "缺少请求数据",
                "data": None,
                "status": "ERROR"
            }), 400

        task_id = data.get('task_id')
        report_text = data.get('report_text')
        department_id = data.get('department_id')  # 可选参数

        if not task_id:
            return jsonify({
                "code": Response.r.ERR_INVALID_ARGUMENT,
                "message": "缺少task_id参数",
                "data": None,
                "status": "ERROR"
            }), 400

        if not report_text:
            report_text = f"管理员手动更新 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 的任务进度"

        app = current_app._get_current_object()
        # 创建临时实例，但不启动调度器
        temp_scheduler = ProgressNotificationScheduler(app)
        
        # 直接执行批量进度更新逻辑
        with app.app_context():
            result = temp_scheduler.run_batch_update_now(
                task_id=task_id,
                report_text=report_text,
                department_id=department_id
            )
        
        if result.get('success', False):
            return jsonify({
                "code": Response.r.OK,
                "message": "直接执行批量进度更新成功",
                "data": {
                    "executed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "result": result
                },
                "status": "OK"
            })
        else:
            return jsonify({
                "code": Response.r.ERR_INTERNAL,
                "message": result.get('message', '批量进度更新失败'),
                "data": result,
                "status": "ERROR"
            }), 500
            
    except Exception as e:
        logging.error(f"直接执行批量进度更新失败: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": f"直接执行批量进度更新失败: {str(e)}",
            "data": None,
            "status": "ERROR"
        }), 500

@scheduler_bp.route('/direct/batch-progress-update-all', methods=['POST'])
@require_role(D.admin)  # 只允许管理员访问
def direct_run_batch_progress_update_all(user_id: str):
    """直接执行所有活跃任务的批量进度更新逻辑，不依赖调度器实例"""
    try:
        from app.modules.sched.progress_notification_sched import ProgressNotificationScheduler
        from flask import current_app
        
        app = current_app._get_current_object()
        # 创建临时实例，但不启动调度器
        temp_scheduler = ProgressNotificationScheduler(app)
        
        # 直接执行批量进度更新逻辑
        with app.app_context():
            success = temp_scheduler.batch_update_all_departments_progress()
        
        if success:
            return jsonify({
                "code": Response.r.OK,
                "message": "直接执行所有活跃任务的批量进度更新成功",
                "data": {
                    "executed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "update_type": "all_active_tasks"
                },
                "status": "OK"
            })
        else:
            return jsonify({
                "code": Response.r.ERR_INTERNAL,
                "message": "执行所有活跃任务的批量进度更新失败",
                "data": None,
                "status": "ERROR"
            }), 500
            
    except Exception as e:
        logging.error(f"直接执行所有活跃任务的批量进度更新失败: {str(e)}")
        return jsonify({
            "code": Response.r.ERR_INTERNAL,
            "message": f"直接执行所有活跃任务的批量进度更新失败: {str(e)}",
            "data": None,
            "status": "ERROR"
        }), 500 
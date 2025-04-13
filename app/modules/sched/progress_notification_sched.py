from datetime import datetime
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from app.models.department import Department
from app.controllers.task_progress import notify_below_average_members, create_task_progress, update_task_progress
from app.utils.logger import Log
from app.models.member import Member
from app.models.period_task import PeriodTask

class ProgressNotificationScheduler:
    """进度检查和通知调度器"""

    def __init__(self, app: Flask):
        """初始化调度器
        Args:
            app: Flask应用实例
        """
        self.app = app
        self.scheduler = BackgroundScheduler()
        self.setup_jobs()

    def setup_jobs(self):
        """设置调度任务"""
        # 每天早上5点检查进度并通知
        self.scheduler.add_job(
            func=self.check_and_notify_all_departments,
            trigger='cron',
            hour=5,
            minute=0,
            id='progress_check_and_notification'
        )
        
        # 每天早上5点执行批量进度更新
        self.scheduler.add_job(
            func=self.batch_update_all_departments_progress,
            trigger='cron',
            hour=5,
            minute=0,
            id='batch_progress_update'
        )

    def start(self):
        """启动调度器"""
        try:
            self.scheduler.start()
            Log.info("进度检查和通知调度器已启动")
        except Exception as e:
            Log.error(f"启动进度检查和通知调度器失败: {str(e)}")

    def stop(self):
        """停止调度器"""
        try:
            self.scheduler.shutdown()
            Log.info("进度检查和通知调度器已停止")
        except Exception as e:
            Log.error(f"停止进度检查和通知调度器失败: {str(e)}")

    def check_and_notify_all_departments(self):
        """检查并通知所有部门的进度情况"""
        try:
            with self.app.app_context():
                # 获取所有部门
                departments = Department.query.all()
                if not departments:
                    Log.error("没有找到任何部门")
                    return False
                
                success_count = 0
                skip_count = 0
                error_count = 0
                
                for department in departments:
                    try:
                        Log.info(f"开始处理部门 {department.name} (ID: {department.id})")
                        
                        # 先检查部门是否有成员
                        member_count = Member.query.filter_by(department_id=department.id).count()
                        Log.info(f"部门 {department.name} 的成员数量: {member_count}")
                        
                        if member_count == 0:
                            Log.info(f"跳过部门 {department.name}：没有成员")
                            skip_count += 1
                            continue
                            
                        # 为每个部门执行进度检查和通知
                        try:
                            result = notify_below_average_members(department.id)
                        except Exception as e:
                            Log.error(f"调用notify_below_average_members时出错，部门：{department.name}，错误：{str(e)}")
                            error_count += 1
                            continue
                            
                        if not result:
                            Log.error(f"部门 {department.name} 进度检查和通知失败: 返回结果为空")
                            error_count += 1
                            continue
                            
                        if result.code != 200:
                            if "没有成员" in str(result.message):
                                Log.info(f"跳过部门 {department.name}：{result.message}")
                                skip_count += 1
                            else:
                                error_msg = str(result.message) if result.message else "未知错误"
                                Log.error(f"部门 {department.name} 进度检查和通知失败: {error_msg}")
                                if result.data:
                                    Log.error(f"错误详情: {result.data}")
                                error_count += 1
                        else:
                            if not result.data:
                                Log.error(f"部门 {department.name} 返回数据为空")
                                error_count += 1
                                continue
                                
                            # 如果是今日暂无进度记录的情况，也算作成功
                            if "今日暂无进度记录" in str(result.data.get('message', '')):
                                Log.info(f"部门 {department.name} 今日暂无进度记录")
                                success_count += 1
                                continue
                                
                            below_average_count = len(result.data.get('below_average_members', []))
                            total_members = result.data.get('total_members', 0)
                            members_with_progress = result.data.get('members_with_progress', 0)
                            Log.info(f"部门 {department.name} 进度检查和通知完成：总成员 {total_members} 人，"
                                   f"有进度记录 {members_with_progress} 人，"
                                   f"低于平均进度 {below_average_count} 人")
                            success_count += 1
                    except Exception as e:
                        Log.error(f"处理部门 {department.name} 进度检查和通知时出错: {str(e)}")
                        error_count += 1
                        continue

                summary = (f"进度检查和通知完成：成功 {success_count} 个部门，"
                          f"跳过 {skip_count} 个部门，失败 {error_count} 个部门")
                Log.info(summary)
                return success_count > 0  # 只要有一个部门成功就返回True

        except Exception as e:
            Log.error(f"执行部门进度检查和通知时出错: {str(e)}")
            return False

    def run_check_and_notification_now(self):
        """立即执行一次进度检查和通知"""
        try:
            with self.app.app_context():
                success = self.check_and_notify_all_departments()
                return success
        except Exception as e:
            Log.error(f"立即执行进度检查和通知失败: {str(e)}")
            return False

    def batch_update_task_progress(self, task_id: str, report_text: str, department_id: str = None) -> dict:
        """批量创建或更新所有成员的任务进度记录
        Args:
            task_id: 任务ID
            report_text: 日报内容
            department_id: 部门ID（可选）
        Returns:
            dict: 处理结果统计
        """
        try:
            # 验证任务是否存在
            task = PeriodTask.query.filter_by(task_id=task_id).first()
            if not task:
                Log.error(f"找不到指定的任务: {task_id}")
                return {
                    'success': False,
                    'message': f"找不到指定的任务: {task_id}"
                }

            # 获取需要处理的成员列表
            query = Member.query
            if department_id:
                query = query.filter_by(department_id=department_id)
            members = query.all()

            if not members:
                Log.error(f"找不到需要处理的成员 (department_id: {department_id if department_id else 'all'})")
                return {
                    'success': False,
                    'message': "找不到需要处理的成员"
                }

            # 批量处理每个成员的进度
            results = []
            success_count = 0
            total_count = len(members)
            
            for member in members:
                try:
                    # 尝试创建进度记录
                    result = create_task_progress(
                        user_id=member.id,
                        task_id=task_id,
                        report_text=report_text
                    )
                    
                    # 如果创建失败（可能已存在记录），尝试更新
                    if result.code != 200:
                        result = update_task_progress(
                            user_id=member.id,
                            task_id=task_id,
                            report_text=report_text
                        )
                    
                    if result.code == 200:
                        success_count += 1
                        results.append({
                            'user_id': member.id,
                            'success': True,
                            'message': '进度更新成功',
                            'data': result.data
                        })
                    else:
                        results.append({
                            'user_id': member.id,
                            'success': False,
                            'message': str(result.message),
                            'data': result.data
                        })
                except Exception as e:
                    Log.error(f"处理成员 {member.id} 的进度时出错: {str(e)}")
                    results.append({
                        'user_id': member.id,
                        'success': False,
                        'message': str(e),
                        'data': None
                    })

            Log.info(f"批量处理任务进度完成：总计 {total_count} 人，成功 {success_count} 人")
            
            return {
                'success': True,
                'total_count': total_count,
                'success_count': success_count,
                'results': results
            }

        except Exception as e:
            Log.error(f"批量处理任务进度时出错: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }

    def run_batch_update_now(self, task_id: str, report_text: str, department_id: str = None) -> dict:
        """立即执行一次批量进度更新
        Args:
            task_id: 任务ID
            report_text: 日报内容
            department_id: 部门ID（可选）
        Returns:
            dict: 处理结果统计
        """
        try:
            with self.app.app_context():
                return self.batch_update_task_progress(task_id, report_text, department_id)
        except Exception as e:
            error_msg = str(e)
            Log.error(f"立即执行批量进度更新失败: {error_msg}")
            return {
                'success': False,
                'message': error_msg
            }

    def batch_update_all_departments_progress(self):
        """每日批量更新所有部门成员的任务进度"""
        try:
            with self.app.app_context():
                # 获取所有部门
                departments = Department.query.all()
                if not departments:
                    Log.error("没有找到任何部门")
                    return False

                # 获取所有活跃的周期任务
                current_time = datetime.now()
                active_tasks = PeriodTask.query.filter(
                    PeriodTask.start_time <= current_time,
                    PeriodTask.end_time >= current_time
                ).all()

                if not active_tasks:
                    Log.info("当前没有活跃的周期任务")
                    return True

                total_results = []
                for task in active_tasks:
                    # 为每个任务生成通用的日报内容
                    report_text = f"系统自动更新 {current_time.strftime('%Y-%m-%d')} 的任务进度"
                    
                    # 为每个部门更新进度
                    for department in departments:
                        try:
                            result = self.batch_update_task_progress(
                                task_id=task.task_id,
                                report_text=report_text,
                                department_id=department.id
                            )
                            
                            if result['success']:
                                Log.info(f"成功更新部门 {department.name} 的任务 {task.task_id} 进度")
                            else:
                                Log.error(f"更新部门 {department.name} 的任务 {task.task_id} 进度失败: {result.get('message', '未知错误')}")
                            
                            total_results.append({
                                'department_id': department.id,
                                'department_name': department.name,
                                'task_id': task.task_id,
                                'result': result
                            })
                        
                        except Exception as e:
                            error_msg = str(e)
                            Log.error(f"处理部门 {department.name} 的任务 {task.task_id} 时出错: {error_msg}")
                            total_results.append({
                                'department_id': department.id,
                                'department_name': department.name,
                                'task_id': task.task_id,
                                'error': error_msg
                            })

                # 统计总体结果
                success_count = sum(1 for r in total_results if r.get('result', {}).get('success', False))
                total_count = len(total_results)
                
                Log.info(f"批量更新任务进度完成：总计 {total_count} 个任务-部门组合，成功 {success_count} 个")
                return success_count > 0  # 只要有一个成功就返回True

        except Exception as e:
            Log.error(f"执行批量进度更新时出错: {str(e)}")
            return False 
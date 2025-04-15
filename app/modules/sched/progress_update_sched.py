from datetime import datetime
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from app.models.department import Department
from app.controllers.task_progress import update_task_progress, update_department_progress, create_task_progress
from app.utils.logger import Log
from app.models.member import Member
from app.models.period_task import PeriodTask

class ProgressUpdateScheduler:
    _instance = None
    """进度更新调度器
    
    负责定期计算和更新：
    1. 各成员的任务进度
    2. 各部门的成员进度汇总统计（平均进度、最高进度、最低进度）
    
    注意：部门本身并没有任务，部门进度指的是该部门所有成员的进度统计。
    """

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
            Log.info("进度更新调度器已启动")
        except Exception as e:
            Log.error(f"启动进度更新调度器失败: {str(e)}")

    def stop(self):
        """停止调度器"""
        try:
            self.scheduler.shutdown()
            Log.info("进度更新调度器已停止")
        except Exception as e:
            Log.error(f"停止进度更新调度器失败: {str(e)}")

    def batch_update_task_progress(self, department_id: str = None) -> dict:
        """批量创建或更新所有成员的任务进度记录
        Args:
            department_id: 部门ID（可选）
        Returns:
            dict: 处理结果统计
        """
        try:
            current_time = datetime.now()
            
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
            total_tasks_count = 0
            updated_task_ids = set()  # 记录已更新的任务ID，用于后续更新部门统计
            departments_to_update = set()  # 记录需要更新统计的部门ID
            
            for member in members:
                try:
                    # 查找该成员的所有活跃任务
                    member_tasks = PeriodTask.query.filter(
                        PeriodTask.assignee_id == member.id,
                        PeriodTask.start_time <= current_time,
                        PeriodTask.end_time >= current_time
                    ).all()
                    
                    if not member_tasks:
                        Log.info(f"成员 {member.id} 没有需要更新的活跃任务")
                        results.append({
                            'user_id': member.id,
                            'success': True,
                            'message': '没有需要更新的活跃任务',
                            'data': None
                        })
                        continue
                    
                    # 为每个任务更新进度
                    member_success_count = 0
                    member_task_results = []
                    
                    for task in member_tasks:
                        total_tasks_count += 1
                        
                        # 尝试创建进度记录
                        result = create_task_progress(
                            user_id=member.id,
                            task_id=task.task_id
                        )
                        
                        # 如果创建失败（可能已存在记录），尝试更新
                        if result.code != 200:
                            result = update_task_progress(
                                user_id=member.id,
                                task_id=task.task_id
                            )
                        
                        if result.code == 200:
                            member_success_count += 1
                            success_count += 1
                            member_task_results.append({
                                'task_id': task.task_id,
                                'success': True,
                                'message': '进度更新成功',
                                'data': result.data
                            })
                            
                            # 记录已更新的任务，用于后续更新部门统计
                            updated_task_ids.add(task.task_id)
                            departments_to_update.add(member.department_id)
                        else:
                            member_task_results.append({
                                'task_id': task.task_id,
                                'success': False,
                                'message': str(result.message),
                                'data': result.data
                            })
                    
                    # 记录该成员的所有任务结果
                    results.append({
                        'user_id': member.id,
                        'success': member_success_count > 0,
                        'message': f'成功更新 {member_success_count}/{len(member_tasks)} 个任务',
                        'tasks': member_task_results
                    })
                        
                except Exception as e:
                    Log.error(f"处理成员 {member.id} 的进度时出错: {str(e)}")
                    results.append({
                        'user_id': member.id,
                        'success': False,
                        'message': str(e),
                        'data': None
                    })

            # 更新部门进度统计
            department_stats = []
            
            if departments_to_update and updated_task_ids:
                Log.info(f"开始更新部门成员进度汇总统计，部门: {departments_to_update}")
                
                for dept_id in departments_to_update:
                    try:
                        # 更新部门成员进度汇总统计（平均进度、最高进度、最低进度）
                        result = update_department_progress(
                            department_id=dept_id,
                            date=current_time
                        )
                        
                        if result.code == 200:
                            Log.info(f"成功更新部门 {dept_id} 的成员进度汇总统计")
                            department_stats.append({
                                'department_id': dept_id,
                                'success': True,
                                'data': result.data
                            })
                        else:
                            Log.error(f"更新部门 {dept_id} 的成员进度汇总统计失败: {result.message}")
                            department_stats.append({
                                'department_id': dept_id,
                                'success': False,
                                'message': result.message
                            })
                            
                    except Exception as e:
                        Log.error(f"更新部门 {dept_id} 的成员进度汇总统计时出错: {str(e)}")
                        department_stats.append({
                            'department_id': dept_id,
                            'success': False,
                            'message': str(e)
                        })

            Log.info(f"批量处理任务进度完成：总计 {len(members)} 人，{total_tasks_count} 个任务，成功 {success_count} 个，更新了 {len(department_stats)} 个部门成员进度汇总")
            
            return {
                'success': True,
                'total_members': len(members),
                'total_tasks': total_tasks_count,
                'success_count': success_count,
                'results': results,
                'department_stats': department_stats
            }

        except Exception as e:
            Log.error(f"批量处理任务进度时出错: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }

    def run_batch_update_now(self, department_id: str = None) -> dict:
        """立即执行一次批量进度更新
        Args:
            department_id: 部门ID（可选）
        Returns:
            dict: 处理结果统计
        """
        try:
            with self.app.app_context():
                return self.batch_update_task_progress(department_id)
        except Exception as e:
            error_msg = str(e)
            Log.error(f"立即执行批量进度更新失败: {error_msg}")
            return {
                'success': False,
                'message': error_msg
            }

    def batch_update_all_departments_progress(self):
        """每日批量更新所有部门的成员进度统计
        
        注意：部门本身没有任务，部门进度是指该部门所有成员的进度统计，
        包括平均进度、最高进度、最低进度等指标。
        """
        try:
            with self.app.app_context():
                # 获取所有部门
                departments = Department.query.all()
                if not departments:
                    Log.error("没有找到任何部门")
                    return False

                total_results = []
                success_count = 0
                
                # 为每个部门计算所有成员的进度统计
                for department in departments:
                    try:
                        Log.info(f"开始计算部门 {department.name} 的成员进度统计")
                        
                        # 更新该部门所有成员的进度数据
                        result = self.batch_update_task_progress(department_id=department.id)
                        
                        if result['success']:
                            Log.info(f"成功更新部门 {department.name} 的成员进度: {result['success_count']}/{result['total_tasks']} 个任务")
                            success_count += 1
                        else:
                            Log.error(f"更新部门 {department.name} 的成员进度失败: {result.get('message', '未知错误')}")
                        
                        total_results.append({
                            'department_id': department.id,
                            'department_name': department.name,
                            'result': result
                        })
                    
                    except Exception as e:
                        error_msg = str(e)
                        Log.error(f"计算部门 {department.name} 的成员进度统计时出错: {error_msg}")
                        total_results.append({
                            'department_id': department.id,
                            'department_name': department.name,
                            'error': error_msg
                        })

                # 统计总体结果
                success_departments = sum(1 for r in total_results if r.get('result', {}).get('success', False))
                total_departments = len(total_results)
                
                Log.info(f"部门成员进度统计完成：总计 {total_departments} 个部门，成功 {success_departments} 个")
                return success_departments > 0  # 只要有一个部门成功就返回True

        except Exception as e:
            Log.error(f"执行部门成员进度统计时出错: {str(e)}")
            return False 
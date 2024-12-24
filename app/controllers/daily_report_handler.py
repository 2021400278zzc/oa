import base64
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from PIL import Image
from werkzeug.datastructures import FileStorage

from app.models.daily_task import DailyTask
from app.models.daily_report import DailyReport
from app.modules.llm import create_completion
from app.utils.constant import LLMPrompt as LLM
from app.utils.constant import LLMStructure as LLMS
from app.utils.constant import LocalPath as Local
from app.utils.constant import UrlTemplate as Url
from app.utils.database import CRUD
from app.utils.logger import Log
from app.utils.response import Response
from app.modules.sql import db

class DailyReportHandler:
    """日报处理器"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.tomorrow = self.today + timedelta(days=1)

    def get_today_tasks(self) -> List[Dict]:
        """获取今日任务信息"""
        # 获取用户今日的所有每日任务
        daily_tasks = DailyTask.query.filter(
            DailyTask.assignee_id == self.user_id,
            DailyTask.task_date >= self.today,
            DailyTask.task_date < self.tomorrow
        ).all()
        
        # 检查今天是否已提交日报
        today_report = DailyReport.query.filter(
            DailyReport.user_id == self.user_id,
            DailyReport.created_at >= self.today,
            DailyReport.created_at < self.tomorrow
        ).first()
        
        tasks_info = []
        for task in daily_tasks:
            tasks_info.append({
                "task_id": task.task_id,
                "basic_task": task.basic_task_requirements,
                "detail_task": task.detail_task_requirements,
                "completed": bool(today_report),  # 通过日报判断完成状态
                "completed_description": task.completed_task_description,
                "created_at": task.created_at.isoformat()
            })
        
        return tasks_info

    def process_image(self, image_path: str) -> Optional[str]:
        """处理图片并转换为base64格式
        Args:
            image_path: 图片路径
        Returns:
            str: base64编码的图片数据
        """
        try:
            with open(image_path, 'rb') as img_file:
                img_data = img_file.read()
                return base64.b64encode(img_data).decode('utf-8')
        except Exception as e:
            Log.error(f"Error processing image {image_path}: {str(e)}")
            return None

    def save_pictures(self, pictures: List[FileStorage]) -> Tuple[List[str], List[str]]:
        """保存图片并返回URL和路径"""
        picture_urls = []
        picture_paths = []
        
        if pictures:
            # 确保目录存在
            os.makedirs(Local.REPORT_PICTURE, exist_ok=True)
            
            for picture in pictures:
                if picture and picture.filename:
                    try:
                        # 生成唯一文件名
                        uuid_filename = str(uuid.uuid4())
                        # 构建URL和路径
                        picture_urls.append(Url.REPORT_PICTURE(uuid_filename))
                        filename = os.path.join(Local.REPORT_PICTURE, uuid_filename)
                        picture_paths.append(filename)
                        
                        # 保存图片
                        with Image.open(picture) as img:
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            img.save(filename, "PNG", optimize=True)
                    except Exception as e:
                        Log.error(f"Error saving picture: {str(e)}")
                        continue
        
        return picture_urls, picture_paths

    def generate_report_review(self, report_text: str, tasks_info: List[Dict], picture_paths: List[str]) -> Dict:
        """生成日报评价"""
        # 处理图片数据
        image_data = []
        for path in picture_paths:
            base64_data = self.process_image(path)
            if base64_data:
                image_data.append(base64_data)
        
        # 整合任务信息
        all_requirements = []
        all_completed = []
        
        for task in tasks_info:
            all_requirements.append(task["basic_task"])
            if task["completed_description"]:
                all_completed.append(task["completed_description"])
        
        # 生成评价提示
        review_prompt = LLM.DAILY_REPORT_REVIEW_JSON(
            "\n".join(all_requirements),
            1,  # 每日任务都是1天
            0,  # 当天的已过时间为0
            "\n".join(all_completed),
            "\n".join(task["detail_task"] for task in tasks_info),
            report_text
        )
        
        try:
            # 创建评价
            review = create_completion(
                review_prompt,
                self.user_id,
                "report",
                image_data if image_data else None,
                dictionary_like=True,
                response_format=LLMS.DailyReport,
                model_type="4o"
            )
            
            # 确保评分不为空
            if not review.get('basic', {}).get('score') or \
               not review.get('excess', {}).get('score') or \
               not review.get('extra', {}).get('score'):
                Log.error("Invalid review scores")
                review = {
                    "basic": {"status": "基础评分", "score": 60},
                    "excess": {"status": "超额评分", "score": 0},
                    "extra": {"status": "额外评分", "score": 0},
                    "total": {"status": "总评", "score": 60}
                }
            
            return review
            
        except Exception as e:
            Log.error(f"Error generating review: {str(e)}")
            return {
                "basic": {"status": "评价生成失败", "score": 60},
                "excess": {"status": "无法评估", "score": 0},
                "extra": {"status": "无法评估", "score": 0},
                "total": {"status": "系统评价失败", "score": 60}
            }

    def handle_report_submission(self, report_text: str, pictures: List[FileStorage]) -> Response:
        """处理日报提交，同时完成当日任务"""
        try:
            # 获取今日任务信息
            tasks_info = self.get_today_tasks()
            if not tasks_info:
                return Response(Response.r.ERR_NOT_FOUND, message="未找到今日任务")
            
            # 检查是否已提交今日日报
            existing_report = DailyReport.query.filter(
                DailyReport.user_id == self.user_id,
                DailyReport.created_at >= self.today,
                DailyReport.created_at < self.tomorrow
            ).first()
            
            if existing_report:
                return Response(Response.r.ERR_CONFLICTION, message="今日已提交日报")
            
            # 保存图片
            picture_urls, picture_paths = self.save_pictures(pictures) if pictures else ([], [])
            
            # 生成日报评价
            review = self.generate_report_review(report_text, tasks_info, picture_paths)
            
            try:
                # 开始数据库事务
                # 1. 创建日报记录
                report = DailyReport(
                    user_id=self.user_id,
                    report_id=str(uuid.uuid4()),
                    report_text=report_text,
                    report_picture=picture_urls,
                    task_ids=[task["task_id"] for task in tasks_info],
                    report_review=review,
                    basic_score=review['basic']['score'],
                    excess_score=review['excess']['score'],
                    extra_score=review['extra']['score'],
                    generating=False
                )
                
                # 2. 更新所有今日任务的完成状态
                daily_tasks = DailyTask.query.filter(
                    DailyTask.assignee_id == self.user_id,
                    DailyTask.task_date >= self.today,
                    DailyTask.task_date < self.tomorrow
                ).all()
                
                for task in daily_tasks:
                    task.completed_task_description = report_text
                    task.updated_at = datetime.now()
                
                # 保存所有更改
                db.session.add(report)
                db.session.commit()
                
                return Response(Response.r.OK, data={
                    "report_id": report.report_id,
                    "review": review,
                    "total_score": review['basic']['score'] + review['excess']['score'] + review['extra']['score'],
                    "completed_tasks": [
                        {
                            "task_id": task.task_id,
                            "completed_at": task.updated_at.isoformat()
                        } for task in daily_tasks
                    ]
                })
                
            except Exception as e:
                db.session.rollback()
                Log.error(f"Error saving report and updating tasks: {str(e)}")
                raise
                
        except Exception as e:
            Log.error(f"Error in handle_report_submission: {str(e)}")
            return Response(Response.r.ERR_INTERNAL, message=str(e))
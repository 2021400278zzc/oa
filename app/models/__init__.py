from flask import Flask
from flask_migrate import revision, upgrade

from app.utils.constant import DataStructure as D
from app.utils.database import CRUD
from app.utils.logger import Log

from . import daily_report, department, member, period_task, verification,gpt,daily_task
from .department import Department
from .member import Member


def dev_init(app: Flask) -> None:
    """初始化数据库"""
    try:
        with app.app_context():
            upgrade(revision="head")  # 更新db结构
            revision(message="init", autogenerate=True)

            # 创建主要部门 - 开发组
            with CRUD(Department, name="开发组") as d:
                if not d.query_key():
                    d.add()
                dev_id = d.query_key().first().id

            # 创建开发组的子部门
            dev_departments = ["开发组-前端", "开发组-后端", "开发组-游戏开发", "开发组-OA开发"]
            for dept_name in dev_departments:
                with CRUD(Department, name=dept_name) as d:
                    if not d.query_key():
                        instance = d.create_instance(no_attach=True)
                        d.update(instance, name=dept_name, parent_id=dev_id)
                        d.add(instance)

            # 获取OA开发组ID
            with CRUD(Department, name="开发组-OA开发") as d:
                dep_id = d.query_key().first().id

            # 创建其他部门
            other_departments = ["美术组", "AI工程师组", "视频组", "大数据组"]
            for dept_name in other_departments:
                with CRUD(Department, name=dept_name) as d:
                    if not d.query_key():
                        d.add()

            # 获取美术组ID            
            with CRUD(Department, name="美术组") as d:
                art_id = d.query_key().first().id

            # 以下保持原有成员配置不变
            with CRUD(Member, id="2021400122") as k:
                if not k.query_key():
                    k.add(name="kyl", major="empty", role=D.admin, learning="None")
                    k.instance.set_password()
                else:
                    k.update(
                        name="kyl",
                        major="empty",
                        role=D.admin,
                        learning="None",
                        phone="18664341145",
                        email="3105189545@qq.com",
                        department_id=dep_id,
                    )

            with CRUD(Member, id="2020400065") as w:
                if not w.query_key():
                    w.add(name="wl", major="empty", role=D.admin, learning="None")
                    w.instance.set_password("13713819950abc!")
                else:
                    w.update(
                        name="wl",
                        major="empty",
                        role=D.leader,
                        learning="None",
                        phone="17748539690",
                        email="2261076785@qq.com",
                        department_id=art_id,
                    )

            with CRUD(Member, id="123456") as w:
                if not w.query_key():
                    w.add(name="zch", major="25互联网G6", role=D.admin, learning="开发")
                    w.instance.set_password("123456")
                else:
                    w.update(
                        name="zch",
                        major="25互联网G6",
                        role=D.member,
                        learning="开发",
                        department_id=dep_id,
                    )

            with CRUD(Member, id="2021400278") as w:
                if not w.query_key():
                    w.add(name="zzc", major="21云计算", role=D.admin, learning="开发")
                    w.instance.set_password("123456")
                else:
                    w.update(
                        name="zzc",
                        major="21云计算",
                        role=D.admin,
                        learning="开发",
                        department_id=dep_id,
                    )

            with CRUD(Member, id="654321") as w:
                if not w.query_key():
                    w.add(name="zch", major="25互联网G6", role=D.admin, learning="开发")
                    w.instance.set_password("123456")
                else:
                    w.update(
                        name="jyy",
                        major="21人工智能",
                        role=D.sub_leader,
                        learning="开发",
                        department_id=dep_id,
                    )

    except Exception as e:
        with app.app_context():
            Log.error(f"Failed to initialize the db: {e}")
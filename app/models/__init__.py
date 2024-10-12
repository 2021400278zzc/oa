import sys

from flask import Flask
from flask_migrate import revision, upgrade

from app.utils.constant import DataStructure as D
from app.utils.database import CRUD
from app.utils.logger import Log

from . import daily_report, department, member, period_task, verification
from .department import Department
from .member import Member


def dev_init(app: Flask) -> None:
    try:
        with app.app_context():
            upgrade(revision="head")  # 更新db结构
            revision(message="init", autogenerate=True)

            with CRUD(Department, name="开发组") as d:
                if not d.query_key():
                    d.add()

            with CRUD(Department, name="开发组") as d:
                if not d.query_key(name="OA开发组"):
                    instance = d.create_instance(no_attach=True)
                    d.update(
                        instance, name="OA开发组", parent_id=d.query_key().first().id
                    )
                    d.add(instance)

            with CRUD(Department, name="OA开发组") as d:
                dep_id = d.query_key().first().id

            with CRUD(Department, name="美术组") as d:
                if not d.query_key():
                    d.add()

            with CRUD(Department, name="美术组") as d:
                art_id = d.query_key().first().id

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
        raise RuntimeError(f"Failed to initialize the db: {e}")

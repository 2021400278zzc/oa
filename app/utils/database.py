from enum import Enum
from typing import Any

from flask_sqlalchemy.model import Model
from flask_sqlalchemy.query import Query
from sqlalchemy.exc import SQLAlchemyError

from app.modules.sql import db
from app.utils.constant import SQLStatus

from .logger import Log


class CRUD(SQLStatus):
    """操作数据库模型的上下文管理器
    Args:
        model (Model, Option): 需要进行操作的模型。如果不传入，则需要确保在上下文中均传入可操作的实例。
        **kwargs: 需要操作的键值对
    在进行非查询操作时，必须使用with以应用上下文管理器，这样，CRUD类才会应用所做出的更改。\n
    :Example:
    .. code-block:: python
        # 增加或更改的示例
        with CRUD(Model, id=user_id) as r:
            if query := r.query_key(): # 如果有指定id的条目，则更新键为name的内容
                res = query.first()
                r.update(res, name="Kimu")
            else: # 否则创建一个新的实例，并设置键name，加入至表中
                instance = r.create_instance()
                r.update(instance, name="Kimu")
                r.add(instance)
        # 查询的示例
        if query := CRUD(Model, id=user_id).query():
            result = query.first()
    """

    def __init__(self, model: Model = None, **kwargs) -> None:
        self.model = model
        self.instance: Model = None
        self.kwargs = kwargs
        self.error: Exception | None = None
        self.status = self.OK
        self._need_commit: bool = False

    def __enter__(self) -> "CRUD":
        return self

    def create_instance(self, no_attach: bool = False) -> Model:
        """创建包含kwargs更改的模型的实例并附加到父类的实例对象中
        Args:
            no_attach (bool, optional): 创建实例但不附加至父类。默认为False。
        Returns:
            Model: 返回实例中已被更改的模型实例对象。
        """
        if no_attach:
            return self.model(**self.kwargs)
        if not self.instance:
            self.instance = self.model(**self.kwargs)
        return self.instance

    def need_update(self) -> None:
        """对该实例的更改需要应用到数据库中"""
        self._need_commit = True

    def add(self, instance: Model = None, **kwargs) -> Model | None:
        """添加条目
        Args:
            instance (Model, optional): 模型实例，当提供时会以该实例为基添加条目。不提供则使用类的实例。
            **kwargs: 对该实例的属性做出额外的更改。
        Returns:
            (Model | None): 当操作成功时返回实例对象。否则返回None。
        """
        try:
            instance = instance if instance else self.create_instance()
            # 对于函数中传入的kwargs，使用update函数以在实例中更新新的值
            if update := self.update(instance, **kwargs):
                instance = update
            db.session.add(instance)
            self._need_commit = True
            return self.instance
        except SQLAlchemyError as e:
            self.error = e
            self.status = self.SQL_ERR
        except Exception as e:
            self.error = e
            self.status = self.INTERNAL_ERR
        return None

    def query_key(self, **kwargs) -> Query | None:
        """通过指定的键值查询条目
        Args:
            **kwargs: 当提供kwargs时，会使用kwargs的值进行查询，否则使用创建实例时传入的kwargs进行查询。
        Returns:
            (Query | None): 如果查询存在内容，则返回Query对象。否则返回None。
        """
        try:
            kw = kwargs if kwargs else self.kwargs
            query = self.model.query.filter_by(**kw)
            if not query.all():
                self.status = self.NOT_FOUND
                return None
            return query
        except SQLAlchemyError as e:
            self.error = e
            self.status = self.SQL_ERR
        except Exception as e:
            self.error = e
            self.status = self.INTERNAL_ERR
        return None

    def update(self, instance: Model = None, **kwargs) -> Model | None:
        """更新条目
        Args:
            instance (Model, optional): 已更改的实例，当提供时会将该实例的更改提交。不提供则查找匹配类参数的第一条项目并将其作为实例。
            **kwargs: 当提供实例时，会对该实例的属性进行更改，否则对父类的实例进行更改。
        Returns:
            (Model | None): 当操作成功时返回实例对象。否则返回None。
        """
        try:
            # 为了兼容add的操作，如果创建的实例在表内不存在，则直接进入setattr操作
            if (query := self.query_key()) and not instance:
                instance = query.first()
                # raise LookupError(f"Cannot find row by specified keys: {self.kwargs}.")
            for k, v in kwargs.items():
                setattr(instance, k, v)
            self._need_commit = True
            return instance
        except SQLAlchemyError as e:
            self.error = e
            self.status = self.SQL_ERR
        except Exception as e:
            self.error = e
            self.status = self.INTERNAL_ERR
        return None

    def delete(self, instance: Model = None, first_record=False, **kwargs) -> bool:
        try:
            query = self.query_key() or self.query_key(**kwargs)
            if query:
                query = query.first() if first_record else query
                query.delete()

            db.session.delete(instance)
            self._need_commit = True
            return True
        except SQLAlchemyError as e:
            self.error = e
            self.status = self.SQL_ERR
        except Exception as e:
            self.error = e
            self.status = self.INTERNAL_ERR
        return False

    def query_to_dict(self, *exclude_keys: str):
        """将记录实例转为字典，并排除不需要的键

        Args:
            instance (Model): _description_

        Returns:
            _type_: _description_
        """
        if not (query := self.query_key()):
            return {}

        instance = query.first()

        instance_dict = {
            k: v if not isinstance(v, Enum) else v.value
            for k, v in {
                column.name: getattr(instance, column.name)
                for column in self.model.__table__.columns
            }.items()
        }

        keys = [key.split(".") for key in exclude_keys]

        def filter(dic: dict, paths: list[str]) -> dict:
            result = {}

            # 对每个顶层键进行判别，如果不存在排除则添加至result
            for key in dic:
                if not any(path[0] == key for path in paths):
                    result[key] = dic[key]

            # 对需要进行处理的键进行判别
            for path in paths:
                # 当需要处理的顶层键在字典中时才进行处理
                if path[0] in dic:
                    # 当该需要处理的键只有单元素时，将该键设为空
                    if len(path) == 1:
                        continue
                    # 否则开始进入递归处理流程
                    if path[0] not in result:
                        result[path[0]] = {}
                    if isinstance(dic[path[0]], dict):
                        result[path[0]] = filter(
                            dic[path[0]], [p[1:] for p in paths if p[0] == path[0]]
                        )
            return result

        return filter(instance_dict, keys)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.error or exc_type or exc_val or exc_tb:
            Log.error(f"CRUD: <catch: {self.error}> <except: ({exc_type}: {exc_val})>")
            db.session.rollback()

        if self._need_commit:
            db.session.commit()

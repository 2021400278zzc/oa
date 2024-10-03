from flask_sqlalchemy.model import Model
from flask_sqlalchemy.query import Query
from sqlalchemy.exc import SQLAlchemyError

from app.modules.sql import db
from app.utils.constant import SQLStatus

from .logger import Log


class CRUD(SQLStatus):
    """操作数据库模型的上下文管理器
    Args:
        model (Model): 需要进行操作的模型
        **kwargs: 需要操作的键值对
    :Example:
    .. code-block:: python
        with CRUD(Model, id=user_id) as r:
            if query := r.query_key(): # 如果有指定id的条目，则更新键为name的内容
                res = query.first()
                r.update(res, name="Kimu")
            else: # 否则创建一个新的实例，并设置键name，加入至表中
                instance = r.create_instance()
                instance.name = "Kimy"
                r.add(instance)

    """

    def __init__(self, model: Model, **kwargs) -> None:
        self.model = model
        self.instance: Model = None
        self.kwargs = kwargs
        self.error: Exception | None = None
        self.status = self.OK
        self._need_update: bool = False

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

    def need_update(self):
        self._need_update = True

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
            if update := self.update(instance, **kwargs):
                instance = update
            db.session.add(instance)
            self._need_update = True
            return self.instance
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
            if (query := self.query_key()) and not instance:
                instance = query.first()
                # raise LookupError(f"Cannot find row by specified keys: {self.kwargs}.")
            for k, v in kwargs.items():
                setattr(instance, k, v)
            self._need_update = True
            return instance
        except SQLAlchemyError as e:
            self.error = e
            self.status = self.SQL_ERR
        except Exception as e:
            self.error = e
            self.status = self.INTERNAL_ERR
        return None

    def query_key(self) -> Query | None:
        """通过指定的键值查询条目，键值对需在创建CRUD上下文时指定
        Returns:
            (Query | None): 如果查询存在内容，则返回Query对象。否则返回None。
        """
        query = self.model.query.filter_by(**self.kwargs)
        if not query.all():
            self.status = self.NOT_FOUND
            return None
        return query

    def convert_dict(self, instance: Model, *args, **kwargs):
        return {
            column.name: getattr(instance, column.name)
            for column in instance.__table__.columns
        }

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.error or exc_type or exc_val or exc_tb:
            Log.error(f"CRUD: <catch: {self.error}> <except: ({exc_type}: {exc_val})>")
            db.session.rollback()

        if self._need_update:
            db.session.commit()

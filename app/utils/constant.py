class DataStructure:
    """基本的数据结构"""

    roles = ["admin", "leader", "subleader", "member"]
    admin = "admin"
    leader = "leader"
    sub_leader = "subleader"
    member = "member"


class SQLStatus:
    """SQLalchemy返回的状态常量"""

    OK = 0
    SQL_ERR = 1
    INTERNAL_ERR = 2

    NOT_FOUND = 5


class ResponseConstant:
    """用于响应的基本响应体常量"""

    CODE_OK = 200
    CODE_INVALID_ARGUMENTS = 400
    CODE_AUTH_FAILED = 401
    CODE_NOT_FOUND = 404
    CODE_CONFLICTION = 409
    CODE_INTERNAL_SERVER = 500

    STATE_OK = "OK"
    STATE_ERR = "ERR"
    STATE_AUTH_ERR = "AUTH_ERR"
    STATE_AUTH_EXPIRED = "AUTH_EXP"

    MSG_OK = "操作成功"
    MSG_ERR_AUTH = "认证失败"
    MSG_ERR_REACH_END = "未匹配任何期望条件而到达函数底部"
    MSG_ERR_ARGUMENT = "传入了错误的参数"
    MSG_EXPIRED = "请求中包含过期的内容"
    MSG_EXCEPT_SQL = "由于数据库操作时出现问题而造成的错误："
    MSG_EXCEPT_INTERNAL = "由于内部故障而造成的错误："
    MSG_CONDITION_NOT_MATCH = "条件不匹配"
    MSG_CONFLICTION = "项已存在"
    MSG_NOT_FOUND = "项未找到"

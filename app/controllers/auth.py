from app.models.member import Member
from app.models.verification import Verification
from app.utils.database import CRUD
from app.utils.utils import is_value_valid


def login(
    id: str = "", passwd: str = "", phone: str = "", email: str = "", code: str = ""
):

    # id与密码登陆的情况
    if is_value_valid(id, passwd):
        with CRUD(Member, id=id) as r:
            if (query := r.query_key().first()) and query.check_password(
                passwd
            ):  # id存在且密码校验正确
                return query.id

    # 手机与验证码登陆的情况
    if is_value_valid(phone, code):
        with CRUD(Member, phone=phone) as r:
            if (query := r.query_key().first()) and check_verify_code(
                code, phone=phone
            ):  # 手机和验证码正确
                return query.id

    # 邮箱与验证码登陆的情况
    if is_value_valid(email, code):
        with CRUD(Member, email=email) as r:
            if (query := r.query_key().first()) and check_verify_code(
                code, email=email
            ):  # 邮箱和验证码正确
                return query.id

    return None


def check_verify_code(code: str, email: str = "", phone: str = "") -> bool:
    return False


def send_verify_code(email: str = "", phone: str = ""):
    if email:
        type = "email"
        value = email
    if phone:
        type = "phone"
        value = phone

    code = ""
    with CRUD(Verification, type=type, value=value) as v:
        if query := v.query_key():
            code = query.generate_code()
        else:
            instance: Verification = v.create_instance()
            code = instance.generate_code()

        # TODO: send to phone or email

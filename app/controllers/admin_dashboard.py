import hashlib
from subprocess import PIPE, Popen

from flask import current_app as app
from sqlalchemy import inspect, text

from app.modules.sql import db


class AdminService:
    def admin(self, data):
        try:
            operation = data.get("operation")
            password = data.get("password")
            args = data.get("args", [])

            encrypt = hashlib.sha256("admin123".encode()).hexdigest()

            # 登录操作
            if operation == "login" and args == "sign":
                if hashlib.sha256(password.encode()).hexdigest() == encrypt:
                    return encrypt

            elif operation == "login" and args == "verify":
                return password == encrypt

            # 确认密码正确
            if password == encrypt:
                if operation == "databases":
                    inspector = inspect(db.engine)
                    tables = inspector.get_table_names()  # 获取所有表名
                    return tables

                if operation == "readall":
                    table_name = args[0]
                    result = db.session.execute(text(f"SELECT * FROM {table_name}"))
                    return [dict(zip(result.keys(), row)) for row in result]

                if operation == "insert":
                    table_name = args[2]
                    key = args[0]
                    value = args[1]
                    db.session.execute(
                        text(f"INSERT INTO {table_name} ({key}) VALUES ({value})")
                    )
                    db.session.commit()
                    return f"Inserted {key}: {value} into {table_name}"

                if operation == "delete":
                    table_name = args[2]
                    key = args[0]
                    value = args[1]
                    db.session.execute(
                        text(f"DELETE FROM {table_name} WHERE {key} = '{value}'")
                    )
                    db.session.commit()
                    return f"Deleted {key}: {value} from {table_name}"

                if operation == "clean":
                    table_name = args[0]
                    db.session.execute(text(f"TRUNCATE TABLE {table_name}"))
                    db.session.commit()
                    return f"Cleaned {table_name}"

                if operation == "deletedb":
                    db.session.execute(text("DROP DATABASE IF EXISTS oa;"))
                    db.session.execute(text("CREATE DATABASE oa;"))
                    return "Database reset"

                if operation == "apis":
                    routes = []
                    for rule in app.url_map.iter_rules():
                        routes.append(
                            {"path": str(rule), "methods": list(rule.methods)}
                        )
                    return routes

                if operation == "command":
                    command = self.get_command(args)
                    return self.execute_command(command)

            return "NOT PERMITTED!"

        except Exception as e:
            print(e)
            return str(e)

    def get_command(self, args):
        """根据参数生成系统命令"""
        if args[0] == "restart":
            return "bash /www/wwwroot/restartRonRon.sh"
        elif args[0] == "updateproj":
            return "/usr/bin/python3 /www/wwwroot/updateRonRon.py"
        elif args[0] == "showlog":
            return "tail -n 50 /www/wwwlogs/nodejs/RonRon.log"
        elif args[0] == "customer":
            return (
                f'python /home/kimu/RonRon-Egg/admin/shell.py -o write -k "{args[1]}"'
            )
        elif args[0] == "mysql":
            return args[1]
        elif args[0] == "hint":
            return f"bash -c 'compgen -c {args[1]}'"
        elif args[0] == "upon":
            return f"python /home/kimu/RonRon-Egg/admin/shell.py -o upon -k {args[1]}"
        return None

    def execute_command(self, command):
        """执行系统命令"""
        if command:
            process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()
            if stdout:
                return stdout.decode("utf-8")
            if stderr:
                return stderr.decode("utf-8")
        return "No output from command"

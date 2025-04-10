# DianChuang OA

## 项目简介
这是一个基于 Flask 构建的后端系统，支持与 MySQL 数据库交互并通过远程 API 实现人工智能模型调用。针对企业内部办公自动化管理进行设计，该项目采用 MVC 架构设计，具备高灵活性和扩展性，能够适应从小流量到中等流量的业务需求。

## 功能列表
- 基于 Flask 的后端框架
- 与 MySQL 数据库交互
- 通过远程 API 调用人工智能模型
- 数据库迁移管理
- 基本的 MVC 架构设计
- 定时任务调度系统
- 邮件和短信验证码功能
- JWT 用户认证

## 目录结构
```
├── app/                  # 主应用目录
│   ├── __init__.py      # Flask 应用初始化
│   ├── models/          # 数据模型
│   ├── views/           # 视图层
│   ├── controllers/     # 控制器层
│   ├── modules/         # 功能模块（如定时任务等）
│   └── utils/           # 工具函数
├── config/              # 配置文件
│   ├── development.py   # 开发环境配置
│   ├── production.py    # 生产环境配置
│   └── __init__.py      # 配置初始化
├── migrations/          # 数据库迁移目录
├── public/             # 静态资源目录
│   ├── user/           # 用户相关资源
│   │   └── picture/    # 用户头像
│   ├── www/            # 开发用控制台
│   ├── report/         # 报告文件
│   └── honors/         # 荣誉证书等
├── tests/              # 测试目录
├── .env                # 环境变量配置
├── .gitignore         # Git忽略文件
├── requirements.txt    # 项目依赖
└── run.py             # 项目启动文件
```

## 环境要求
- Python 3.12
- MySQL 8.0 或以上版本
- 操作系统：Windows/Linux/MacOS

## 安装步骤

1. 创建并激活虚拟环境：
   ```bash
   python -m venv .venv
   # Windows
   .venv\\Scripts\\activate
   # Linux/MacOS
   source .venv/bin/activate
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境变量：在项目根目录下创建 `.env` 文件，并添加以下配置信息：
   ```bash
   # 数据库配置
   DATABASE_URL=mysql://user:password@host/dbname
   MYSQL_HOST=localhost
   MYSQL_USER=root
   MYSQL_PASSWORD=your_password
   MYSQL_DB=oa

   # JWT配置
   JWT_SECRET_KEY=your_jwt_secret
   SECRET_KEY=your_app_secret

   # 腾讯云配置（短信服务）
   TENCENTCLOUD_SECRET_ID=your_secret_id
   TENCENTCLOUD_SECRET_KEY=your_secret_key
   SMS_SDK_APP_ID=your_app_id
   SIGN_NAME=your_sign_name
   TEMPLATE_ID=your_template_id

   # 邮件配置
   EMAIL_SMTP=smtp.example.com
   EMAIL_ACCOUNT=your_email
   EMAIL_PASSWORD=your_password

   # OpenAI配置
   OPENAI_API_KEY=your_api_key
   ```

4. 初始化数据库：
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

5. 启动项目：
   ```bash
   python run.py
   ```
   默认启动在 5002 端口

## 主要依赖版本
- Flask==3.1.0
- Flask-JWT-Extended==4.7.1
- Flask-SQLAlchemy==3.1.1
- Flask-Migrate==4.0.7
- Flask-Cors==5.0.0
- APScheduler==3.11.0
- SQLAlchemy==2.0.36
- Pillow==11.0.0
- python-dotenv==1.0.1
- tencentcloud-sdk-python==3.0.1286
- transformers==4.47.1

## 定时任务
项目包含两种类型的定时任务：
- 周期性任务（PeriodTaskScheduler）
- 每日任务（DailyTaskScheduler）

## 常见问题
1. **数据库连接失败**
   - 检查 MySQL 服务是否正常运行
   - 验证 .env 中的数据库配置是否正确
   - 确保数据库用户具有适当权限

2. **定时任务未执行**
   - 检查日志文件（app.log）中的错误信息
   - 确保应用以非调试模式运行（debug=False）

3. **文件上传失败**
   - 检查 public 目录的写入权限
   - 确保上传目录存在且可写

## 安全提示
- 请妥善保管 .env 文件，不要将其提交到版本控制系统
- 定期更新依赖包以修复潜在的安全漏洞
- 在生产环境中使用 HTTPS
- 定期更换 JWT 密钥

## 许可证
MIT License

## 贡献指南
1. Fork 本仓库
2. 创建特性分支
3. 提交更改
4. 发起 Pull Request

## 远程 API 集成
通过以下远程 API 实现与人工智能模型的交互（具体 API 信息根据使用情况进行补充）：
- API 地址：`https://api.example.com`
- 调用方式：`POST /api/v1/ai-model`
- 请求参数：`{"input": "your input data"}`

## 接口文档
### `/auth` 接口

1. **`login` (登录)**
   - **请求方式**：`POST /auth/login`
   - **请求参数**（JSON格式）：
     ```json
     {
       "username": "your_username",   // 可选
       "password": "your_password",   // 可选
       "phone": "your_phone",         // 可选
       "code": "your_code",           // 可选
       "email": "your_email",         // 可选
       "code": "your_email_code"      // 可选
     }
     ```
     - **备注**：至少需要提供 `username+password`，`phone+code`，或 `email+code` 之一的组合。
   
   - **成功响应**（状态码：`200`）：
     ```json
     {
       "token": "your_jwt_token",
       "msg": "操作成功",
       "status": "OK"
     }
     ```

2. **`/send_code` (发送验证码)**
   - **请求方式**：`POST /auth/send_code`
   - **请求参数**（JSON格式）：
     ```json
     {
       // phone 或 email 中的其中一个
       "phone": "your_phone",    
       "email": "your_email"     
     }
     ```
   - **成功响应**（状态码：`200`）：
     ```json
     {
       "data": null,
       "msg": "操作成功",
       "status": "OK"
     }
     ```

### `/static` 接口

1. **`/static/type/filename/option`**
   - **请求方式**：`GET /static/{type}/{filename}/{option}`
     - `type`: 文件类型，如图片、视频等。
     - `filename`: 文件名。
     - `option`: 可选参数，用于指定图像大小或其他文件选项。
     - **备注**: 一般不需要手动指定。
   
   - **成功响应**（状态码：`200`）：以流的方式返回文件内容。

### `/user` 接口

1. **`/info` (获取用户信息)**
   - **请求方式**：`GET /user/info`
   - **请求头**：需要 `Authorization` 头部，格式为 `Bearer <token>`。
   
   - **成功响应**（状态码：`200`）：
     ```json
     {
       "data": {
          "department": "",
          "email": "",
          "id": "",
          "learning": "",
          "major": "",
          "name": "",
          "parent_department": "",
          "phone": "",
          "picture": "",
          "role": "n"
         },
       "msg": "操作成功",
       "status": "OK"
     }
     ```

---

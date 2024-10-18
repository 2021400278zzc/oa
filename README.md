# DianChuang OA

## 项目简介
这是一个基于 Flask 构建的后端系统，支持与 MySQL 数据库交互并通过远程 API 实现人工智能模型调用。针对企业内部办公自动化管理进行设计，该项目采用 MVC 架构设计，具备高灵活性和扩展性，能够适应从小流量到中等流量的业务需求。

## 功能列表
- 基于 Flask 的后端框架
- 与 MySQL 数据库交互
- 通过远程 API 调用人工智能模型
- 数据库迁移管理
- 基本的 MVC 架构设计

## 目录结构
```
├── app/                  # 主应用目录
│   ├── __init__.py       # Flask 应用初始化
│   ├── models/           # 数据模型
│   ├── views/            # 视图层
│   ├── controllers/      # 控制器层
│   └── static/           # 静态文件目录
│   └── modules/          # 解耦化的模块
├── config/               # 配置文件
│   ├── development.py    # 开发环境配置
│   ├── production.py     # 生产环境配置
├── migrations/           # 数据库迁移目录
├─public                  # 静态文件位置
│  ├─user
│  │  └─picture           # 用户头像
│  └─www                  # 开发用控制台
├── .env                  # 环境变量配置
├── README.md             # 项目描述文件
└── run.py                # 项目启动文件
```

## 环境要求
- Python 3.10
- MySQL 8 或以上版本

## 安装步骤

1. 创建并激活 Conda 环境：
   ```bash
   conda create --name dcoa python=3.10
   conda activate dcoa
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境变量：在项目根目录下创建 `.env` 文件，并添加数据库及 API 相关的配置信息：
   ```bash
    DATABASE_URL=
    MYSQL_HOST=
    MYSQL_USER=
    MYSQL_PASSWORD=
    MYSQL_DB=
    JWT_SECRET_KEY=
    SECRET_KEY=
    TENCENTCLOUD_SECRET_ID=
    TENCENTCLOUD_SECRET_KEY=
    SMS_SDK_APP_ID=
    SIGN_NAME=
    TEMPLATE_ID=
    EMAIL_SMTP=
    EMAIL_ACCOUNT=
    EMAIL_PASSWORD=
    OPENAI_API_KEY=
   ```

4. 初始化数据库迁移：
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

5. 启动项目：
   ```bash
   python run.py
   ```

## 远程 API 集成
通过以下远程 API 实现与人工智能模型的交互（具体 API 信息根据使用情况进行补充）：
- API 地址：`https://api.example.com`
- 调用方式：`POST /api/v1/ai-model`
- 请求参数：`{"input": "your input data"}`

## 常见问题
- **如何配置数据库？** 请确保在 `.env` 文件中正确配置数据库连接信息。
- **如何修改项目环境配置？** 项目的配置文件位于 `config/` 目录下，根据环境选择合适的配置文件进行修改。

## 未来计划
- 添加更多的 AI API 功能
- 添加更多单元测试

---

###  `requirements.txt`

项目中的必要依赖：

```
Flask
Flask-MySQLdb
Flask-Migrate
flask_jwt_extended
flask-bcrypt
python-dotenv
SQLAlchemy
transformers 
requests      
pillow
tencentcloud-sdk-python
Flask-CORS
```

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

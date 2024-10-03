# DianChuang OA

## 项目简介
这是一个基于 Flask 构建的后端系统，支持与 MySQL 数据库交互并通过远程 API 实现人工智能模型调用。该项目采用 MVC 架构设计，具备高灵活性和扩展性，能够适应从小流量到中等流量的业务需求。

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

1. 克隆项目：
   ```bash
   git clone https://github.com/your/repo.git
   cd your_project
   ```

2. 创建并激活 Conda 环境：
   ```bash
   conda create --name dcoa python=3.10
   conda activate dcoa
   ```

3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

4. 配置环境变量：在项目根目录下创建 `.env` 文件，并添加数据库及 API 相关的配置信息：
   ```bash
   SECRET_KEY=your_secret_key
   MYSQL_HOST=localhost
   MYSQL_USER=root
   MYSQL_PASSWORD=your_password
   MYSQL_DB=your_database
   ```

5. 初始化数据库迁移：
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. 启动项目：
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
Flask==2.3.2
Flask-MySQLdb==1.0.1
Flask-Migrate==4.0.0
python-dotenv==1.0.0
SQLAlchemy==1.4.0
transformers==4.12.5  # 如果使用 transformers API
requests==2.28.0       # 用于调用远程 API
```

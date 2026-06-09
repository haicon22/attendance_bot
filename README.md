# 企业级 Telegram 考勤管理机器人

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![aiogram 3.x](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-teal.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7+-red.svg)](https://redis.io/)

## 功能特性

- **员工管理**: 注册、绑定 Telegram、部门/职位管理、多级权限
- **考勤打卡**: 上班/下班/外勤打卡、GPS 定位验证、防重复打卡
- **班次管理**: 固定班次、轮班、自定义时间、节假日设置
- **请假系统**: 多种请假类型、多级审批流程
- **管理后台**: REST API、统计报表、Excel/PDF 导出
- **自动通知**: 打卡提醒、迟到提醒、审批通知、每日汇总

## 技术架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Telegram   │────▶│   Nginx     │────▶│  Bot/API    │
│   Client    │     │  (LB/SSL)   │     │  (FastAPI)  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          ▼                    ▼                    ▼
                   ┌─────────────┐      ┌─────────────┐     ┌─────────────┐
                   │ PostgreSQL  │      │    Redis    │     │   Celery    │
                   │  (Primary)   │      │  (Cache)    │     │  (Workers)  │
                   └─────────────┘      └─────────────┘     └─────────────┘
```

## 快速开始

### 1. 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- 4 核 CPU / 8GB 内存（最低）

### 2. 部署

```bash
# 克隆项目
git clone <repo-url>
cd attendance_bot

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 启动服务
docker-compose up -d

# 查看状态
docker-compose ps
```

### 3. 配置 Telegram Bot

1. 在 Telegram 中搜索 @BotFather
2. 创建新 Bot，获取 Token
3. 将 Token 填入 `.env` 的 `BOT_TOKEN`
4. 设置 Webhook URL（如果使用 Webhook 模式）

### 4. 访问管理后台

- API 文档: `https://your-domain.com/docs`
- 健康检查: `https://your-domain.com/health`

## 项目结构

```
attendance_bot/
├── attendance_bot/          # 主应用代码
│   ├── api/                 # FastAPI REST API
│   ├── bot/                 # Telegram Bot (aiogram)
│   ├── config/              # 配置文件
│   ├── core/                # 核心组件 (DB, Redis, Security)
│   ├── models/              # SQLAlchemy 数据模型
│   ├── services/            # 业务逻辑层
│   ├── tasks/               # Celery 异步任务
│   └── tests/               # 单元测试
├── init-scripts/            # 数据库初始化脚本
├── nginx/                   # Nginx 配置
├── docs/                    # 文档
├── docker-compose.yml       # Docker Compose 配置
├── Dockerfile.*             # 各服务 Dockerfile
└── requirements.txt         # Python 依赖
```

## API 文档

启动服务后访问 `/docs` 查看完整的 Swagger/OpenAPI 文档。

### 主要端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/auth/login` | POST | 用户登录 |
| `/api/v1/users` | GET/POST | 用户管理 |
| `/api/v1/attendance/checkin` | POST | 上班打卡 |
| `/api/v1/attendance/checkout` | POST | 下班打卡 |
| `/api/v1/leaves/requests` | GET/POST | 请假管理 |
| `/api/v1/reports/generate` | POST | 生成报表 |
| `/api/v1/dashboard/stats` | GET | 仪表盘统计 |

## 测试

```bash
# 运行单元测试
docker-compose exec api pytest -v

# 运行覆盖率测试
docker-compose exec api pytest --cov=attendance_bot --cov-report=html
```

## 性能指标

| 指标 | 数值 |
|------|------|
| 并发用户 | 500-5000 |
| 响应时间 (P99) | < 200ms |
| 数据库连接池 | 20-50 |
| Redis 连接池 | 10-30 |

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

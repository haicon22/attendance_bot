# 企业级 Telegram 考勤管理机器人 - 系统架构设计

## 1. 系统概述

本系统是一个基于 Telegram Bot 的企业级考勤管理解决方案，支持 500-5000 名员工同时使用，采用微服务架构设计，支持横向扩展。

## 2. 技术栈

| 组件 | 技术选型 | 版本 |
|------|---------|------|
| 编程语言 | Python | 3.12 |
| Bot 框架 | aiogram | 3.x |
| Web 框架 | FastAPI | 0.110+ |
| ORM | SQLAlchemy | 2.0+ |
| 数据库 | PostgreSQL | 16+ |
| 缓存 | Redis | 7+ |
| 消息队列 | Redis Streams / Celery | - |
| 任务调度 | APScheduler | 3.10+ |
| 容器化 | Docker & Docker Compose | - |
| 反向代理 | Nginx | - |
| 报表生成 | ReportLab / openpyxl | - |
| 测试 | pytest | - |

## 3. 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户层 (User Layer)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Telegram    │  │ Web Admin   │  │ Mobile Browser          │  │
│  │ Bot Client  │  │ Dashboard   │  │ (Responsive)            │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      接入层 (Gateway Layer)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Nginx (Load Balancer)                 │   │
│  │  - SSL Termination  - Rate Limiting  - Static Files      │   │
│  └──────────────────────┬──────────────────────────────────┘   │
└─────────────────────────┼──────────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│   Telegram Webhook  │         │   FastAPI REST API  │
│   (aiogram 3.x)     │         │   (Admin Dashboard) │
│                     │         │                     │
│  - 打卡处理          │         │  - 员工管理          │
│  - 请假申请          │         │  - 考勤统计          │
│  - 位置验证          │         │  - 报表导出          │
│  - 通知推送          │         │  - 审批管理          │
└──────────┬──────────┘         └──────────┬──────────┘
           │                               │
           └───────────────┬───────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      服务层 (Service Layer)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ AuthService │  │ Attendance  │  │ LeaveService            │  │
│  │             │  │ Service     │  │                         │  │
│  │ - JWT Auth  │  │ - Clock In  │  │ - Leave Request         │  │
│  │ - RBAC      │  │ - Clock Out │  │ - Approval Flow         │  │
│  │ - Telegram  │  │ - GPS Check │  │ - Balance Calc            │  │
│  │   Binding   │  │ - Overtime  │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ ShiftService│  │ ReportService│  │ NotificationService     │  │
│  │             │  │              │  │                         │  │
│  │ - Fixed     │  │ - Daily     │  │ - Telegram Push         │  │
│  │ - Rotating  │  │ - Monthly   │  │ - Email                 │  │
│  │ - Holiday   │  │ - Yearly    │  │ - SMS (optional)        │  │
│  │ - Custom    │  │ - Export    │  │ - WebSocket             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐
│  PostgreSQL │  │    Redis    │  │   Celery Workers    │
│  (Primary)   │  │  (Cache +   │  │  (Background Tasks) │
│  - Users     │  │   Queue)    │  │                     │
│  - Attendance│  │  - Sessions │  │  - Report Generation│
│  - Leaves    │  │  - Rate Limit│  │  - Notification Send │
│  - Shifts    │  │  - Geo Cache │  │  - Data Cleanup      │
│  - Audit     │  │  - Locking   │  │  - Daily Summary     │
└─────────────┘  └─────────────┘  └─────────────────────┘
```

## 4. 核心模块说明

### 4.1 Bot 模块 (aiogram 3.x)
- **Webhook 模式**: 使用 Telegram Webhook 接收消息，支持高并发
- **FSM (Finite State Machine)**: 管理用户交互状态
- **Middleware**: 权限验证、日志记录、速率限制
- **Inline Keyboards**: 提供友好的交互界面

### 4.2 API 模块 (FastAPI)
- **RESTful API**: 完整的 CRUD 操作
- **JWT Authentication**: 基于角色的访问控制
- **OpenAPI/Swagger**: 自动生成 API 文档
- **Background Tasks**: 异步处理报表生成

### 4.3 数据层
- **SQLAlchemy 2.0**: 异步 ORM，支持连接池
- **Alembic**: 数据库迁移管理
- **Redis**: 分布式缓存和会话存储

### 4.4 任务调度
- **APScheduler**: 定时任务（提醒、汇总）
- **Celery**: 异步任务队列（报表生成、通知发送）

## 5. 扩展性设计

### 5.1 水平扩展
- Bot 服务无状态化，可通过 Nginx 负载均衡部署多个实例
- 使用 Redis 共享会话和锁
- PostgreSQL 读写分离（可选）

### 5.2 高可用
- Docker Compose 多副本部署
- Redis Sentinel 集群（生产环境）
- PostgreSQL 主从复制（生产环境）

### 5.3 性能优化
- 数据库索引优化
- Redis 缓存热点数据
- 异步 I/O 处理
- 连接池管理

## 6. 安全设计

- JWT Token 过期机制
- 密码 bcrypt 加密
- SQL 注入防护（ORM + 参数化查询）
- XSS 防护
- CSRF Token
- 速率限制（Rate Limiting）
- 操作审计日志
- GPS 位置加密存储

## 7. 部署架构

```
┌─────────────────────────────────────────────┐
│              Docker Host / K8s               │
│  ┌─────────┐ ┌─────────┐ ┌──────────────┐ │
│  │ Bot-1   │ │ Bot-2   │ │ Bot-N         │ │
│  │ (aiogram)│ │ (aiogram)│ │ (aiogram)     │ │
│  └────┬────┘ └────┬────┘ └──────┬───────┘ │
│       └─────────────┴─────────────┘         │
│  ┌─────────┐ ┌─────────┐ ┌──────────────┐ │
│  │ API-1   │ │ API-2   │ │ API-N         │ │
│  │(FastAPI)│ │(FastAPI)│ │(FastAPI)      │ │
│  └────┬────┘ └────┬────┘ └──────┬───────┘ │
│       └─────────────┴─────────────┘         │
│  ┌─────────┐ ┌─────────┐ ┌──────────────┐ │
│  │ Worker-1│ │ Worker-2│ │ Worker-N      │ │
│  │(Celery) │ │(Celery) │ │(Celery)       │ │
│  └─────────┘ └─────────┘ └──────────────┘ │
│  ┌─────────┐ ┌─────────┐ ┌──────────────┐ │
│  │Scheduler│ │  Redis  │ │ PostgreSQL   │ │
│  │(APSched)│ │(Cluster)│ │(Primary+Replica)│
│  └─────────┘ └─────────┘ └──────────────┘ │
│  ┌──────────────────────────────────────┐ │
│  │           Nginx (Load Balancer)      │ │
│  └──────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

## 8. 监控与日志

- **结构化日志**: JSON 格式，支持 ELK Stack
- **Metrics**: Prometheus + Grafana
- **Health Check**: /health 端点
- **Tracing**: OpenTelemetry (可选)

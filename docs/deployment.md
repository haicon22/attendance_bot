# 企业级 Telegram 考勤管理机器人 - 部署文档

## 系统要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 4 核 | 8 核+ |
| 内存 | 8 GB | 16 GB+ |
| 磁盘 | 50 GB SSD | 100 GB SSD+ |
| 网络 | 10 Mbps | 100 Mbps+ |

## 环境准备

### 1. 安装 Docker 和 Docker Compose

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 克隆项目

```bash
git clone <repository-url> attendance_bot
cd attendance_bot
cp .env.example .env
```

### 3. 配置环境变量

编辑 `.env` 文件：

```bash
# 数据库
DB_USER=attendance
DB_PASSWORD=your_secure_password_here
DB_NAME=attendance_db

# Redis
REDIS_PORT=6379

# Telegram Bot (从 @BotFather 获取)
BOT_TOKEN=your_bot_token_here
WEBHOOK_URL=https://your-domain.com
WEBHOOK_SECRET=your_webhook_secret_here

# JWT (生成强密钥)
JWT_SECRET=$(openssl rand -hex 32)

# 时区
TZ=Asia/Shanghai

# 扩展配置
BOT_REPLICAS=2
API_REPLICAS=2
WORKER_REPLICAS=2
```

## 部署步骤

### 1. 初始化数据库

```bash
# 启动数据库
docker-compose up -d postgres

# 等待数据库就绪
docker-compose exec postgres pg_isready -U attendance

# 数据库初始化脚本会自动执行（位于 init-scripts/）
```

### 2. 构建并启动所有服务

```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f bot
docker-compose logs -f api
docker-compose logs -f worker
```

### 3. 配置 Telegram Webhook

如果使用 Webhook 模式，确保：

1. 域名已解析到服务器
2. SSL 证书已配置（Nginx 自动处理）
3. Webhook URL 可访问

```bash
# 测试 Webhook 连通性
curl https://your-domain.com/webhook

# 手动设置 Webhook（如需要）
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com/webhook", "secret_token": "your_secret"}'
```

### 4. 配置 Nginx（生产环境）

如果使用外部 Nginx：

```bash
# 复制 SSL 证书到 nginx/ssl/
cp your-cert.pem nginx/ssl/cert.pem
cp your-key.pem nginx/ssl/key.pem

# 重启 Nginx
docker-compose restart nginx
```

## 监控与维护

### 查看服务状态

```bash
# 所有容器状态
docker-compose ps

# 资源使用
docker stats

# 数据库连接数
docker-compose exec postgres psql -U attendance -c "SELECT count(*) FROM pg_stat_activity;"

# Redis 状态
docker-compose exec redis redis-cli info
```

### 日志管理

```bash
# 查看所有日志
docker-compose logs

# 查看特定服务日志
docker-compose logs -f --tail=100 bot

# 清理日志
docker-compose logs --tail=0 > /dev/null
```

### 数据库备份

```bash
# 创建备份
docker-compose exec postgres pg_dump -U attendance attendance_db > backup_$(date +%Y%m%d).sql

# 恢复备份
docker-compose exec -T postgres psql -U attendance attendance_db < backup_20240601.sql
```

### 横向扩展

```bash
# 增加 Bot 实例
docker-compose up -d --scale bot=4

# 增加 API 实例
docker-compose up -d --scale api=4

# 增加 Worker 实例
docker-compose up -d --scale worker=6
```

## 安全加固

### 1. 修改默认密码

```bash
# 修改数据库密码
# 修改 JWT Secret
# 修改 Webhook Secret
```

### 2. 配置防火墙

```bash
# 仅开放必要端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### 3. 启用 HTTPS

```bash
# 使用 Let's Encrypt
docker-compose exec nginx certbot --nginx -d your-domain.com
```

## 故障排查

### 常见问题

| 问题 | 解决方案 |
|------|---------|
| Bot 无法接收消息 | 检查 WEBHOOK_URL 和 BOT_TOKEN |
| 数据库连接失败 | 检查 DATABASE_URL 和 Postgres 状态 |
| Redis 连接失败 | 检查 REDIS_URL 和 Redis 状态 |
| 打卡失败 | 检查 GPS 设置和班次配置 |
| 报表生成失败 | 检查 Worker 状态和磁盘空间 |

### 重置服务

```bash
# 停止所有服务
docker-compose down

# 删除数据卷（谨慎操作！）
docker-compose down -v

# 重新启动
docker-compose up -d
```

## 性能优化

### 数据库优化

```sql
-- 定期分析表
ANALYZE attendance_logs;
ANALYZE leave_requests;

-- 创建额外索引（如需要）
CREATE INDEX CONCURRENTLY idx_attendance_logs_time ON attendance_logs(log_time);
```

### Redis 优化

```bash
# 监控 Redis 内存
docker-compose exec redis redis-cli info memory

# 清理过期键
docker-compose exec redis redis-cli --eval "return redis.call('eval', 'local keys = redis.call(\'keys\', ARGV[1]) for i=1,#keys,5000 do redis.call(\'del\', unpack(keys, i, math.min(i+4999, #keys))) end return #keys', '0', 'session:*')"
```

## 升级指南

```bash
# 1. 备份数据
docker-compose exec postgres pg_dump -U attendance attendance_db > pre_upgrade_backup.sql

# 2. 拉取最新代码
git pull origin main

# 3. 重建镜像
docker-compose build --no-cache

# 4. 执行数据库迁移
docker-compose run --rm api alembic upgrade head

# 5. 重启服务
docker-compose up -d
```

## 联系支持

如有问题，请联系系统管理员或查看项目文档。

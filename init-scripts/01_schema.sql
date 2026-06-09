-- ============================================================
-- 企业级 Telegram 考勤管理机器人 - PostgreSQL 数据库 Schema
-- 版本: 1.0.0
-- 支持: 500-5000 员工
-- ============================================================

-- 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 全文搜索优化

-- ============================================================
-- 1. 部门表 (departments)
-- ============================================================
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    manager_id BIGINT,
    parent_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_departments_parent ON departments(parent_id);
CREATE INDEX idx_departments_code ON departments(code);

-- ============================================================
-- 2. 班次表 (shifts)
-- ============================================================
CREATE TABLE shifts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('fixed', 'rotating', 'custom')),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    break_duration INTEGER DEFAULT 60,  -- 分钟
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    allowed_radius INTEGER DEFAULT 500,  -- 米
    gps_required BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_shifts_type ON shifts(type);
CREATE INDEX idx_shifts_active ON shifts(is_active);

-- ============================================================
-- 3. 用户表 (users)
-- ============================================================
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    employee_number VARCHAR(50) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    shift_id INTEGER REFERENCES shifts(id) ON DELETE SET NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'employee' 
        CHECK (role IN ('super_admin', 'admin', 'manager', 'employee')),
    status VARCHAR(20) NOT NULL DEFAULT 'active' 
        CHECK (status IN ('active', 'inactive', 'suspended')),
    annual_leave_balance DECIMAL(5, 2) DEFAULT 0,
    sick_leave_balance DECIMAL(5, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    created_by BIGINT REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_users_employee_number ON users(employee_number);
CREATE INDEX idx_users_department ON users(department_id);
CREATE INDEX idx_users_shift ON users(shift_id);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_full_name_trgm ON users USING gin(full_name gin_trgm_ops);

-- ============================================================
-- 4. Telegram 账号绑定表 (user_telegram_bindings)
-- ============================================================
CREATE TABLE user_telegram_bindings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    bound_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_interaction TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, telegram_id)
);

CREATE INDEX idx_telegram_bindings_user ON user_telegram_bindings(user_id);
CREATE INDEX idx_telegram_bindings_telegram_id ON user_telegram_bindings(telegram_id);

-- ============================================================
-- 5. 班次例外表 (shift_exceptions)
-- ============================================================
CREATE TABLE shift_exceptions (
    id SERIAL PRIMARY KEY,
    shift_id INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    exception_date DATE NOT NULL,
    custom_start_time TIME,
    custom_end_time TIME,
    is_working_day BOOLEAN DEFAULT TRUE,
    reason VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(shift_id, exception_date)
);

CREATE INDEX idx_shift_exceptions_shift ON shift_exceptions(shift_id);
CREATE INDEX idx_shift_exceptions_date ON shift_exceptions(exception_date);

-- ============================================================
-- 6. 用户班次分配表 (user_shifts)
-- ============================================================
CREATE TABLE user_shifts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    shift_id INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, shift_id, effective_from)
);

CREATE INDEX idx_user_shifts_user ON user_shifts(user_id);
CREATE INDEX idx_user_shifts_active ON user_shifts(is_active);

-- ============================================================
-- 7. 考勤记录表 (attendance_logs)
-- ============================================================
CREATE TABLE attendance_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    log_type VARCHAR(20) NOT NULL CHECK (log_type IN ('check_in', 'check_out', 'field_work')),
    log_date DATE NOT NULL DEFAULT CURRENT_DATE,
    log_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    location_address VARCHAR(500),
    distance_from_office INTEGER,  -- 米
    status VARCHAR(20) NOT NULL DEFAULT 'normal' 
        CHECK (status IN ('normal', 'late', 'early_leave', 'overtime', 'field_work', 'absent')),
    device_info VARCHAR(255),
    ip_address INET,
    photo_url VARCHAR(500),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, log_date, log_type)
);

CREATE INDEX idx_attendance_user ON attendance_logs(user_id);
CREATE INDEX idx_attendance_date ON attendance_logs(log_date);
CREATE INDEX idx_attendance_user_date ON attendance_logs(user_id, log_date);
CREATE INDEX idx_attendance_status ON attendance_logs(status);
CREATE INDEX idx_attendance_type ON attendance_logs(log_type);

-- ============================================================
-- 8. 请假类型表 (leave_types)
-- ============================================================
CREATE TABLE leave_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    default_days DECIMAL(5, 2) DEFAULT 0,
    requires_approval BOOLEAN DEFAULT TRUE,
    approval_levels INTEGER DEFAULT 1,
    is_paid BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_leave_types_code ON leave_types(code);

-- ============================================================
-- 9. 请假申请表 (leave_requests)
-- ============================================================
CREATE TABLE leave_requests (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    leave_type_id INTEGER NOT NULL REFERENCES leave_types(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_days DECIMAL(5, 2) NOT NULL,
    reason TEXT NOT NULL,
    attachment_url VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
    current_approval_level INTEGER DEFAULT 1,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_leave_requests_user ON leave_requests(user_id);
CREATE INDEX idx_leave_requests_status ON leave_requests(status);
CREATE INDEX idx_leave_requests_dates ON leave_requests(start_date, end_date);
CREATE INDEX idx_leave_requests_type ON leave_requests(leave_type_id);

-- ============================================================
-- 10. 审批记录表 (approvals)
-- ============================================================
CREATE TABLE approvals (
    id BIGSERIAL PRIMARY KEY,
    leave_request_id BIGINT NOT NULL REFERENCES leave_requests(id) ON DELETE CASCADE,
    approver_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    approval_level INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'approved', 'rejected')),
    comment TEXT,
    action_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(leave_request_id, approval_level)
);

CREATE INDEX idx_approvals_request ON approvals(leave_request_id);
CREATE INDEX idx_approvals_approver ON approvals(approver_id);
CREATE INDEX idx_approvals_status ON approvals(status);

-- ============================================================
-- 11. 节假日表 (holidays)
-- ============================================================
CREATE TABLE holidays (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    holiday_date DATE NOT NULL,
    is_recurring BOOLEAN DEFAULT FALSE,
    holiday_type VARCHAR(20) DEFAULT 'public' 
        CHECK (holiday_type IN ('public', 'company', 'custom')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(holiday_date, holiday_type)
);

CREATE INDEX idx_holidays_date ON holidays(holiday_date);
CREATE INDEX idx_holidays_recurring ON holidays(is_recurring);

-- ============================================================
-- 12. 通知表 (notifications)
-- ============================================================
CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(30) NOT NULL 
        CHECK (notification_type IN ('reminder', 'approval', 'summary', 'alert', 'system')),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    channel VARCHAR(20) DEFAULT 'telegram' 
        CHECK (channel IN ('telegram', 'email', 'push', 'sms')),
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);
CREATE INDEX idx_notifications_type ON notifications(notification_type);
CREATE INDEX idx_notifications_sent ON notifications(sent_at);

-- ============================================================
-- 13. 审计日志表 (audit_logs)
-- ============================================================
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);

-- ============================================================
-- 14. 考勤汇总表 (attendance_summaries)
-- ============================================================
CREATE TABLE attendance_summaries (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    total_working_days INTEGER DEFAULT 0,
    present_days INTEGER DEFAULT 0,
    late_days INTEGER DEFAULT 0,
    early_leave_days INTEGER DEFAULT 0,
    absent_days INTEGER DEFAULT 0,
    field_work_days INTEGER DEFAULT 0,
    overtime_hours DECIMAL(8, 2) DEFAULT 0,
    leave_days DECIMAL(5, 2) DEFAULT 0,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, year, month)
);

CREATE INDEX idx_summaries_user ON attendance_summaries(user_id);
CREATE INDEX idx_summaries_period ON attendance_summaries(year, month);

-- ============================================================
-- 15. 审批流程配置表 (approval_flows)
-- ============================================================
CREATE TABLE approval_flows (
    id SERIAL PRIMARY KEY,
    leave_type_id INTEGER REFERENCES leave_types(id) ON DELETE CASCADE,
    department_id INTEGER REFERENCES departments(id) ON DELETE CASCADE,
    approval_level INTEGER NOT NULL DEFAULT 1,
    approver_role VARCHAR(20) NOT NULL 
        CHECK (approver_role IN ('manager', 'admin', 'super_admin')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(leave_type_id, department_id, approval_level)
);

-- ============================================================
-- 16. 系统配置表 (system_settings)
-- ============================================================
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================
-- 触发器: 自动更新 updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_departments_updated_at BEFORE UPDATE ON departments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_shifts_updated_at BEFORE UPDATE ON shifts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leave_requests_updated_at BEFORE UPDATE ON leave_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 初始数据
-- ============================================================

-- 默认部门
INSERT INTO departments (name, code, description) VALUES 
    ('总经办', 'CEO', '总经理办公室'),
    ('人力资源部', 'HR', '人力资源管理部门'),
    ('技术部', 'TECH', '技术研发部门'),
    ('财务部', 'FIN', '财务管理部门'),
    ('市场部', 'MKT', '市场营销部门');

-- 默认班次
INSERT INTO shifts (name, type, start_time, end_time, break_duration, gps_required) VALUES 
    ('标准班 (9:00-18:00)', 'fixed', '09:00:00', '18:00:00', 60, TRUE),
    ('早班 (8:00-17:00)', 'fixed', '08:00:00', '17:00:00', 60, TRUE),
    ('晚班 (14:00-23:00)', 'fixed', '14:00:00', '23:00:00', 60, TRUE);

-- 默认请假类型
INSERT INTO leave_types (name, code, default_days, requires_approval, approval_levels, is_paid) VALUES 
    ('年假', 'annual_leave', 10, TRUE, 2, TRUE),
    ('病假', 'sick_leave', 0, TRUE, 1, TRUE),
    ('事假', 'personal_leave', 0, TRUE, 2, FALSE),
    ('产假', 'maternity_leave', 98, TRUE, 2, TRUE),
    ('婚假', 'marriage_leave', 3, TRUE, 1, TRUE),
    ('丧假', 'bereavement_leave', 3, TRUE, 1, TRUE),
    ('调休', 'compensatory_leave', 0, TRUE, 1, TRUE);

-- 默认审批流程
INSERT INTO approval_flows (leave_type_id, department_id, approval_level, approver_role) VALUES 
    (1, NULL, 1, 'manager'),
    (1, NULL, 2, 'admin'),
    (2, NULL, 1, 'manager'),
    (3, NULL, 1, 'manager'),
    (3, NULL, 2, 'admin');

-- 默认系统设置
INSERT INTO system_settings (setting_key, setting_value, description) VALUES 
    ('company_name', '科技有限公司', '公司名称'),
    ('late_threshold_minutes', '15', '迟到阈值（分钟）'),
    ('early_leave_threshold_minutes', '15', '早退阈值（分钟）'),
    ('work_start_reminder_time', '08:30', '上班提醒时间'),
    ('work_end_reminder_time', '17:30', '下班提醒时间'),
    ('timezone', 'Asia/Shanghai', '系统时区'),
    ('max_daily_clock_in', '3', '每日最大打卡次数'),
    ('gps_tolerance_meters', '500', 'GPS 定位容差（米）');

-- 创建超级管理员（密码需要在应用中设置）
INSERT INTO users (employee_number, username, email, full_name, role, status, department_id) 
VALUES ('ADMIN001', 'admin', 'admin@company.com', '系统管理员', 'super_admin', 'active', 1);

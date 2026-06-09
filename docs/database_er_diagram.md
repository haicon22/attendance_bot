# 数据库 ER 图

## ER 图 (Mermaid)

```mermaid
erDiagram
    USERS ||--o{ ATTENDANCE_LOGS : "records"
    USERS ||--o{ LEAVE_REQUESTS : "submits"
    USERS }o--|| DEPARTMENTS : "belongs_to"
    USERS }o--|| SHIFTS : "assigned_to"
    USERS ||--o{ APPROVALS : "approves"
    USERS ||--o{ NOTIFICATIONS : "receives"
    USERS ||--o{ AUDIT_LOGS : "performs"
    USERS ||--o{ USER_TELEGRAM_BINDINGS : "binds"

    DEPARTMENTS ||--o{ USERS : "has"
    DEPARTMENTS ||--o{ SHIFTS : "uses"

    SHIFTS ||--o{ SHIFT_EXCEPTIONS : "has"
    SHIFTS ||--o{ USER_SHIFTS : "assigned"

    LEAVE_REQUESTS ||--o{ APPROVALS : "requires"
    LEAVE_REQUESTS }o--|| LEAVE_TYPES : "is_type"

    HOLIDAYS ||--o{ SHIFT_EXCEPTIONS : "affects"

    USERS {
        bigint id PK
        string employee_number UK
        string username UK
        string email UK
        string password_hash
        string full_name
        string phone
        int department_id FK
        int shift_id FK
        enum role "super_admin, admin, manager, employee"
        enum status "active, inactive, suspended"
        timestamp created_at
        timestamp updated_at
        timestamp last_login
    }

    USER_TELEGRAM_BINDINGS {
        bigint id PK
        bigint user_id FK
        bigint telegram_id UK
        string telegram_username
        string first_name
        string last_name
        bool is_active
        timestamp bound_at
        timestamp last_interaction
    }

    DEPARTMENTS {
        int id PK
        string name UK
        string code UK
        string description
        int manager_id FK
        int parent_id FK
        timestamp created_at
    }

    SHIFTS {
        int id PK
        string name
        enum type "fixed, rotating, custom"
        time start_time
        time end_time
        int break_duration
        float latitude
        float longitude
        int allowed_radius
        bool gps_required
        bool is_active
        timestamp created_at
    }

    SHIFT_EXCEPTIONS {
        int id PK
        int shift_id FK
        date exception_date
        time custom_start_time
        time custom_end_time
        bool is_working_day
        string reason
    }

    USER_SHIFTS {
        bigint id PK
        bigint user_id FK
        int shift_id FK
        date effective_from
        date effective_to
        bool is_active
    }

    ATTENDANCE_LOGS {
        bigint id PK
        bigint user_id FK
        enum type "check_in, check_out, field_work"
        timestamp log_time
        float latitude
        float longitude
        string location_address
        float distance_from_office
        enum status "normal, late, early_leave, overtime, field_work"
        string device_info
        string ip_address
        string photo_url
        string notes
        timestamp created_at
    }

    LEAVE_TYPES {
        int id PK
        string name
        string code UK
        int default_days
        bool requires_approval
        int approval_levels
        bool is_paid
        bool is_active
    }

    LEAVE_REQUESTS {
        bigint id PK
        bigint user_id FK
        int leave_type_id FK
        date start_date
        date end_date
        float total_days
        string reason
        string attachment_url
        enum status "pending, approved, rejected, cancelled"
        int current_approval_level
        timestamp submitted_at
        timestamp resolved_at
    }

    APPROVALS {
        bigint id PK
        bigint leave_request_id FK
        bigint approver_id FK
        int approval_level
        enum status "pending, approved, rejected"
        string comment
        timestamp action_at
    }

    HOLIDAYS {
        int id PK
        string name
        date holiday_date
        bool is_recurring
        enum type "public, company, custom"
    }

    NOTIFICATIONS {
        bigint id PK
        bigint user_id FK
        enum type "reminder, approval, summary, alert"
        string title
        string content
        bool is_read
        enum channel "telegram, email, push"
        timestamp sent_at
        timestamp read_at
    }

    AUDIT_LOGS {
        bigint id PK
        bigint user_id FK
        string action
        string entity_type
        bigint entity_id
        json old_values
        json new_values
        string ip_address
        string user_agent
        timestamp created_at
    }

    ATTENDANCE_SUMMARIES {
        bigint id PK
        bigint user_id FK
        int year
        int month
        int total_working_days
        int present_days
        int late_days
        int early_leave_days
        int absent_days
        int field_work_days
        float overtime_hours
        float leave_days
        timestamp generated_at
    }
```

## 表关系说明

| 关系 | 类型 | 说明 |
|------|------|------|
| users → departments | N:1 | 员工属于一个部门 |
| users → shifts | N:1 | 员工默认分配一个班次 |
| users → attendance_logs | 1:N | 员工有多条考勤记录 |
| users → leave_requests | 1:N | 员工可提交多条请假申请 |
| leave_requests → leave_types | N:1 | 请假申请属于一种请假类型 |
| leave_requests → approvals | 1:N | 请假申请需要多级审批 |
| shifts → shift_exceptions | 1:N | 班次有多个例外日期 |
| users → user_telegram_bindings | 1:N | 员工可绑定多个 Telegram 账号（历史记录） |

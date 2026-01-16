-- Admin 操作日志表
-- 记录管理员的所有操作，用于审计

CREATE TABLE admin_operation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id UUID NOT NULL REFERENCES admin_users(id),
    operation VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_admin_operation_logs_admin_user ON admin_operation_logs(admin_user_id);
CREATE INDEX idx_admin_operation_logs_operation ON admin_operation_logs(operation);
CREATE INDEX idx_admin_operation_logs_resource ON admin_operation_logs(resource_type, resource_id);
CREATE INDEX idx_admin_operation_logs_created_at ON admin_operation_logs(created_at DESC);

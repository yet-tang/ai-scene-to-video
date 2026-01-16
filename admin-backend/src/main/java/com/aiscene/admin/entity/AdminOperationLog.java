package com.aiscene.admin.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * 管理员操作日志实体
 *
 * @author aiscene
 * @since 2026-01-16
 */
@Data
@Entity
@Table(name = "admin_operation_logs")
public class AdminOperationLog {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "admin_user_id", nullable = false)
    private AdminUser adminUser;

    @Column(nullable = false, length = 50)
    private String operation;

    @Column(name = "resource_type", length = 50)
    private String resourceType;

    @Column(name = "resource_id")
    private String resourceId;

    @Column(columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    private Object details;

    @Column(name = "ip_address", length = 45)
    private String ipAddress;

    @Column(name = "user_agent", columnDefinition = "text")
    private String userAgent;

    @Column(nullable = false, length = 20)
    private String status;

    @Column(name = "error_message", columnDefinition = "text")
    private String errorMessage;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    /**
     * 操作类型常量
     */
    public static final String OP_LOGIN = "LOGIN";
    public static final String OP_LOGOUT = "LOGOUT";
    public static final String OP_VIEW_PROJECT = "VIEW_PROJECT";
    public static final String OP_RETRY_PROJECT = "RETRY_PROJECT";
    public static final String OP_TEST_MODEL = "TEST_MODEL";
    public static final String OP_CREATE_USER = "CREATE_USER";
    public static final String OP_UPDATE_USER = "UPDATE_USER";
    public static final String OP_DELETE_USER = "DELETE_USER";

    /**
     * 资源类型常量
     */
    public static final String RES_PROJECT = "PROJECT";
    public static final String RES_MODEL = "MODEL";
    public static final String RES_USER = "USER";
    public static final String RES_SYSTEM = "SYSTEM";

    /**
     * 状态常量
     */
    public static final String STATUS_SUCCESS = "SUCCESS";
    public static final String STATUS_FAILED = "FAILED";
}

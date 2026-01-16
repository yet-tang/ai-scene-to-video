package com.aiscene.admin.entity;

/**
 * 项目状态枚举
 *
 * @author aiscene
 * @since 2026-01-16
 */
public enum ProjectStatus {

    /** 初稿 */
    DRAFT,
    /** 上传中 */
    UPLOADING,
    /** AI 分析中 */
    ANALYZING,
    /** 待确认 */
    REVIEW,
    /** 脚本生成中 */
    SCRIPT_GENERATING,
    /** 脚本已生成 */
    SCRIPT_GENERATED,
    /** 音频生成中 */
    AUDIO_GENERATING,
    /** 音频已生成 */
    AUDIO_GENERATED,
    /** 视频渲染中 */
    RENDERING,
    /** 已完成 */
    COMPLETED,
    /** 失败 */
    FAILED
}

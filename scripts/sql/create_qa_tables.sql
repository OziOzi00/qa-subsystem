-- Knowledge QA subsystem business tables.
-- Target database: seitem
-- MySQL version checked in shared environment: 8.4.3
-- This script only creates the 7 qa_ tables. It does not modify public base tables.

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS qa_session (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '会话记录内部主键',
    session_id VARCHAR(100) NOT NULL COMMENT '接口层会话 ID，对应 API sessionId',
    conversation_id VARCHAR(100) NULL COMMENT '客户端对话 ID，对应 API conversationId',
    user_id INT UNSIGNED NULL COMMENT '用户 ID，关联 users.id，未登录可为空',
    current_artifact_id INT UNSIGNED NULL COMMENT '当前上下文文物内部 ID，关联 artifacts.id',
    current_object_id VARCHAR(100) NULL COMMENT '当前上下文文物 object_id',
    last_intent VARCHAR(80) NULL COMMENT '最近一次识别到的意图编码',
    recent_context_json JSON NULL COMMENT '最近上下文摘要，建议保存最近 5 轮问答',
    source_client VARCHAR(50) NULL COMMENT '调用来源，如 web、app、demo',
    status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '会话状态：active/closed/expired',
    last_active_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '最近活跃时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_qa_session_session_id (session_id),
    KEY idx_qa_session_user (user_id),
    KEY idx_qa_session_object (current_object_id),
    KEY idx_qa_session_last_active (last_active_at),
    CONSTRAINT fk_qa_session_user FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_qa_session_artifact FOREIGN KEY (current_artifact_id) REFERENCES artifacts (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_qa_session_status CHECK (status IN ('active', 'closed', 'expired'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识问答会话上下文表';

CREATE TABLE IF NOT EXISTS qa_log (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '问答日志内部主键',
    qa_log_uuid CHAR(36) NOT NULL COMMENT '对外问答日志 ID，对应 API qaLogId',
    session_pk BIGINT UNSIGNED NULL COMMENT '会话表内部主键，关联 qa_session.id',
    session_id VARCHAR(100) NULL COMMENT '接口层会话 ID，冗余保存便于查询',
    conversation_id VARCHAR(100) NULL COMMENT '客户端对话 ID',
    user_id INT UNSIGNED NULL COMMENT '提问用户 ID，关联 users.id，未登录可为空',
    request_object_id VARCHAR(100) NULL COMMENT '请求体或 URL 原始传入的 objectId',
    question TEXT NOT NULL COMMENT '用户原始问题',
    normalized_question VARCHAR(1000) NULL COMMENT '规范化后的问题文本',
    intent VARCHAR(80) NULL COMMENT '识别到的意图编码',
    intent_confidence DECIMAL(5,4) NULL COMMENT '意图识别置信度，建议 0 到 1',
    intent_detail_json JSON NULL COMMENT '意图识别和实体抽取调试信息，如 matchedKeywords、entities、confidence',
    status VARCHAR(30) NOT NULL COMMENT '回答状态：answered/no_data/need_clarification/unsupported/error',
    answer TEXT NULL COMMENT '返回给用户的自然语言答案',
    fact_content TEXT NULL COMMENT '事实内容，来自 MySQL、Neo4j 或确认数据源',
    supplemental_content TEXT NULL COMMENT '模板或大模型生成的补充性描述',
    artifact_id INT UNSIGNED NULL COMMENT '关联文物内部 ID，关联 artifacts.id',
    object_id VARCHAR(100) NULL COMMENT '关联文物 object_id，对应 API objectId',
    resolve_source VARCHAR(50) NULL COMMENT '文物解析来源，如 question_entity/request_object_id/session_context',
    candidates_json JSON NULL COMMENT '多候选文物列表，need_clarification 时使用',
    source_client VARCHAR(50) NULL COMMENT '调用来源，如 web、app、demo',
    retrieval_raw_json JSON NULL COMMENT '检索原始调试数据摘要',
    error_message TEXT NULL COMMENT '错误信息，error 状态时使用',
    latency_ms INT UNSIGNED NULL COMMENT '本次问答处理耗时，单位毫秒',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '问答发生时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_qa_log_uuid (qa_log_uuid),
    KEY idx_qa_log_session_pk (session_pk),
    KEY idx_qa_log_session (session_id),
    KEY idx_qa_log_user_created (user_id, created_at),
    KEY idx_qa_log_request_object (request_object_id),
    KEY idx_qa_log_object (object_id),
    KEY idx_qa_log_intent_status (intent, status),
    KEY idx_qa_log_created (created_at),
    CONSTRAINT fk_qa_log_session FOREIGN KEY (session_pk) REFERENCES qa_session (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_qa_log_user FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_qa_log_artifact FOREIGN KEY (artifact_id) REFERENCES artifacts (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_qa_log_status CHECK (status IN ('answered', 'no_data', 'need_clarification', 'unsupported', 'error')),
    CONSTRAINT chk_qa_log_intent_confidence CHECK (intent_confidence IS NULL OR (intent_confidence >= 0 AND intent_confidence <= 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识问答主日志表';

CREATE TABLE IF NOT EXISTS qa_source_record (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '答案来源记录主键',
    qa_log_id BIGINT UNSIGNED NOT NULL COMMENT '问答日志 ID，关联 qa_log.id',
    source_type VARCHAR(30) NOT NULL COMMENT '来源类型：mysql/neo4j/llm/template',
    source_name VARCHAR(200) NOT NULL COMMENT '来源名称，如博物馆名称、Neo4j 知识图谱、模板名称',
    source_table VARCHAR(100) NULL COMMENT 'MySQL 来源表名，如 artifacts、artists',
    source_record_id VARCHAR(100) NULL COMMENT '来源记录 ID，可保存 MySQL 主键或 Neo4j 节点 ID',
    artifact_id INT UNSIGNED NULL COMMENT '关联文物内部 ID，关联 artifacts.id',
    object_id VARCHAR(100) NULL COMMENT '关联文物 object_id',
    detail_url VARCHAR(500) NULL COMMENT '原始详情页链接',
    fact_text TEXT NULL COMMENT '来源事实文本，对应 API sources[].factText',
    source_payload_json JSON NULL COMMENT '来源原始摘要，如查询字段、节点关系等',
    confidence DECIMAL(5,4) NULL COMMENT '来源置信度，建议 0 到 1',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_qa_source_log (qa_log_id),
    KEY idx_qa_source_type (source_type),
    KEY idx_qa_source_object (object_id),
    KEY idx_qa_source_artifact (artifact_id),
    CONSTRAINT fk_qa_source_log FOREIGN KEY (qa_log_id) REFERENCES qa_log (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_qa_source_artifact FOREIGN KEY (artifact_id) REFERENCES artifacts (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_qa_source_type CHECK (source_type IN ('mysql', 'neo4j', 'llm', 'template')),
    CONSTRAINT chk_qa_source_confidence CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识问答答案来源记录表';

CREATE TABLE IF NOT EXISTS qa_feedback (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户反馈记录主键',
    qa_log_id BIGINT UNSIGNED NOT NULL COMMENT '问答日志 ID，关联 qa_log.id',
    user_id INT UNSIGNED NULL COMMENT '反馈用户 ID，关联 users.id，未登录可为空',
    feedback_type VARCHAR(30) NOT NULL COMMENT '反馈类型：helpful/inaccurate',
    comment TEXT NULL COMMENT '用户补充说明',
    source_client VARCHAR(50) NULL COMMENT '调用来源，如 web、app、demo',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_qa_feedback_log (qa_log_id),
    KEY idx_qa_feedback_user (user_id),
    UNIQUE KEY uk_qa_feedback_log_user_type (qa_log_id, user_id, feedback_type),
    KEY idx_qa_feedback_type_created (feedback_type, created_at),
    CONSTRAINT fk_qa_feedback_log FOREIGN KEY (qa_log_id) REFERENCES qa_log (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_qa_feedback_user FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_qa_feedback_type CHECK (feedback_type IN ('helpful', 'inaccurate'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识问答用户反馈表';

CREATE TABLE IF NOT EXISTS qa_review_task (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '人工审核任务主键',
    feedback_id BIGINT UNSIGNED NOT NULL COMMENT '反馈记录 ID，关联 qa_feedback.id',
    qa_log_id BIGINT UNSIGNED NOT NULL COMMENT '问答日志 ID，关联 qa_log.id',
    task_status VARCHAR(30) NOT NULL DEFAULT 'pending' COMMENT '任务状态：pending/processing/done/closed',
    review_result VARCHAR(30) NULL COMMENT '审核结果：approved/rejected/fixed',
    priority TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '优先级：1 低、2 中、3 高',
    assigned_admin_id INT NULL COMMENT '分配给的管理员 ID，关联 admin_users.id',
    reviewer_admin_id INT NULL COMMENT '实际审核管理员 ID，关联 admin_users.id',
    review_comment TEXT NULL COMMENT '审核意见',
    corrected_answer TEXT NULL COMMENT '修正后的答案',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    reviewed_at DATETIME NULL COMMENT '审核完成时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_qa_review_feedback (feedback_id),
    KEY idx_qa_review_log (qa_log_id),
    KEY idx_qa_review_status_created (task_status, created_at),
    KEY idx_qa_review_assigned_admin (assigned_admin_id),
    KEY idx_qa_review_reviewer_admin (reviewer_admin_id),
    CONSTRAINT fk_qa_review_feedback FOREIGN KEY (feedback_id) REFERENCES qa_feedback (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_qa_review_log FOREIGN KEY (qa_log_id) REFERENCES qa_log (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_qa_review_assigned_admin FOREIGN KEY (assigned_admin_id) REFERENCES admin_users (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_qa_review_reviewer_admin FOREIGN KEY (reviewer_admin_id) REFERENCES admin_users (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_qa_review_status CHECK (task_status IN ('pending', 'processing', 'done', 'closed')),
    CONSTRAINT chk_qa_review_result CHECK (review_result IS NULL OR review_result IN ('approved', 'rejected', 'fixed')),
    CONSTRAINT chk_qa_review_priority CHECK (priority BETWEEN 1 AND 3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识问答不准确反馈人工审核任务表';

CREATE TABLE IF NOT EXISTS qa_failed_question (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '失败问题记录主键',
    qa_log_id BIGINT UNSIGNED NULL COMMENT '问答日志 ID，关联 qa_log.id，日志写入失败时可为空',
    session_id VARCHAR(100) NULL COMMENT '会话 ID，便于追溯上下文',
    user_id INT UNSIGNED NULL COMMENT '用户 ID，关联 users.id，未登录可为空',
    question TEXT NOT NULL COMMENT '用户原始问题',
    normalized_question VARCHAR(1000) NULL COMMENT '规范化后的问题文本',
    question_hash CHAR(64) NULL COMMENT '问题哈希，建议 SHA-256，用于统计重复失败问题',
    intent VARCHAR(80) NULL COMMENT '识别到的意图编码',
    failure_type VARCHAR(40) NOT NULL COMMENT '失败类型：no_data/need_clarification/unsupported/retrieval_error/generation_error，对应 API status 映射见设计文档',
    artifact_id INT UNSIGNED NULL COMMENT '关联文物内部 ID，关联 artifacts.id',
    object_id VARCHAR(100) NULL COMMENT '关联文物 object_id',
    error_detail TEXT NULL COMMENT '错误详情或无数据原因',
    status VARCHAR(30) NOT NULL DEFAULT 'open' COMMENT '处理状态：open/ignored/resolved',
    handled_by INT UNSIGNED NULL COMMENT '处理人 ID，关联 users.id',
    handled_at DATETIME NULL COMMENT '处理时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_qa_failed_log (qa_log_id),
    KEY idx_qa_failed_session (session_id),
    KEY idx_qa_failed_user (user_id),
    KEY idx_qa_failed_hash (question_hash),
    KEY idx_qa_failed_intent (intent),
    KEY idx_qa_failed_type_created (failure_type, created_at),
    KEY idx_qa_failed_object (object_id),
    KEY idx_qa_failed_status (status),
    KEY idx_qa_failed_artifact (artifact_id),
    KEY idx_qa_failed_handled_by (handled_by),
    CONSTRAINT fk_qa_failed_log FOREIGN KEY (qa_log_id) REFERENCES qa_log (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_qa_failed_user FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_qa_failed_artifact FOREIGN KEY (artifact_id) REFERENCES artifacts (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_qa_failed_handled_by FOREIGN KEY (handled_by) REFERENCES users (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_qa_failed_type CHECK (failure_type IN ('no_data', 'need_clarification', 'unsupported', 'retrieval_error', 'generation_error')),
    CONSTRAINT chk_qa_failed_status CHECK (status IN ('open', 'ignored', 'resolved'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识问答失败问题记录表';

CREATE TABLE IF NOT EXISTS qa_intent_template (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '意图模板主键',
    intent_code VARCHAR(80) NOT NULL COMMENT '意图编码，如 artifact_material',
    intent_name VARCHAR(100) NOT NULL COMMENT '意图中文名称，如文物材质',
    description TEXT NULL COMMENT '意图说明',
    data_source VARCHAR(50) NOT NULL COMMENT '主要数据源：mysql/neo4j/mixed/template',
    question_patterns_json JSON NULL COMMENT '常见问法模板 JSON',
    mysql_query_template TEXT NULL COMMENT 'MySQL 查询模板，仅作配置参考，不直接动态执行',
    neo4j_query_template TEXT NULL COMMENT 'Neo4j 查询模板，仅作配置参考，不直接动态执行',
    answer_template TEXT NULL COMMENT '回答模板',
    no_data_template TEXT NULL COMMENT '暂无数据兜底模板',
    enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用：1 启用，0 停用',
    version VARCHAR(30) NOT NULL DEFAULT 'v1' COMMENT '模板版本',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_qa_intent_code (intent_code),
    KEY idx_qa_intent_enabled (enabled),
    KEY idx_qa_intent_source (data_source),
    CONSTRAINT chk_qa_intent_source CHECK (data_source IN ('mysql', 'neo4j', 'mixed', 'template')),
    CONSTRAINT chk_qa_intent_enabled CHECK (enabled IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识问答意图与回答模板表';

SET FOREIGN_KEY_CHECKS = 1;

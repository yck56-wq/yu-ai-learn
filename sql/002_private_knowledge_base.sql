USE `yu_ai_learn`;

SET @add_sources_json = IF(
  EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'quiz_sessions' AND COLUMN_NAME = 'sources_json'),
  'SELECT 1',
  'ALTER TABLE quiz_sessions ADD COLUMN sources_json JSON NULL');
PREPARE stmt_sources_json FROM @add_sources_json;
EXECUTE stmt_sources_json;
DEALLOCATE PREPARE stmt_sources_json;
SET @add_grounding_status = IF(
  EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'quiz_sessions' AND COLUMN_NAME = 'grounding_status'),
  'SELECT 1',
  'ALTER TABLE quiz_sessions ADD COLUMN grounding_status VARCHAR(16) NOT NULL DEFAULT ''fallback''');
PREPARE stmt_grounding_status FROM @add_grounding_status;
EXECUTE stmt_grounding_status;
DEALLOCATE PREPARE stmt_grounding_status;

CREATE TABLE IF NOT EXISTS `knowledge_documents` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `document_id` VARCHAR(64) NOT NULL,
  `user_id` BIGINT NOT NULL,
  `original_name` VARCHAR(255) NOT NULL,
  `extension` VARCHAR(16) NOT NULL,
  `file_size` BIGINT NOT NULL,
  `storage_key` VARCHAR(512) NOT NULL,
  `chunk_count` INT NOT NULL DEFAULT 0,
  `status` VARCHAR(16) NOT NULL DEFAULT 'processing',
  `error_code` VARCHAR(64) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_knowledge_documents_document_id` (`document_id`),
  KEY `idx_knowledge_documents_user_created` (`user_id`, `created_at`),
  CONSTRAINT `fk_knowledge_documents_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

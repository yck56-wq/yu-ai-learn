CREATE DATABASE IF NOT EXISTS `yu_ai_learn`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `yu_ai_learn`;

CREATE TABLE IF NOT EXISTS `users` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `openid` VARCHAR(64) NOT NULL,
  `nickname` VARCHAR(100) NOT NULL,
  `avatar_url` VARCHAR(500) NOT NULL,
  `total_xp` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_openid` (`openid`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `quiz_sessions` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `quiz_id` VARCHAR(64) NOT NULL,
  `user_id` BIGINT NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `summary` TEXT NOT NULL,
  `user_input` TEXT NOT NULL,
  `questions_json` JSON NOT NULL,
  `sources_json` JSON NULL,
  `grounding_status` VARCHAR(16) NOT NULL DEFAULT 'fallback',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_quiz_sessions_quiz_id` (`quiz_id`),
  KEY `idx_quiz_sessions_user_created` (`user_id`, `created_at`),
  CONSTRAINT `fk_quiz_sessions_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `answer_records` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `quiz_id` VARCHAR(64) NOT NULL,
  `user_id` BIGINT NOT NULL,
  `records_json` JSON NOT NULL,
  `total_questions` INT NOT NULL,
  `correct_count` INT NOT NULL DEFAULT 0,
  `accuracy` DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_answer_records_quiz_id` (`quiz_id`),
  KEY `idx_answer_records_user_created` (`user_id`, `created_at`),
  CONSTRAINT `fk_answer_records_quiz`
    FOREIGN KEY (`quiz_id`) REFERENCES `quiz_sessions` (`quiz_id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT `fk_answer_records_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `reports` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `quiz_id` VARCHAR(64) NOT NULL,
  `user_id` BIGINT NOT NULL,
  `report_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_reports_quiz_id` (`quiz_id`),
  KEY `idx_reports_user_created` (`user_id`, `created_at`),
  CONSTRAINT `fk_reports_quiz`
    FOREIGN KEY (`quiz_id`) REFERENCES `quiz_sessions` (`quiz_id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT `fk_reports_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

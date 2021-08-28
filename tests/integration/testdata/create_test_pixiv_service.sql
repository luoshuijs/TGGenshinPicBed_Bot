DROP VIEW IF EXISTS `pixiv_approved_artist`;
DROP VIEW IF EXISTS `genshin_pixiv_audit_r18`;
DROP VIEW IF EXISTS `genshin_pixiv_audit_nsfw`;
DROP VIEW IF EXISTS `genshin_pixiv_audit_sfw`;
DROP VIEW IF EXISTS `genshin_pixiv_audit`;

DROP TABLE IF EXISTS `pixiv_artist`;
DROP TABLE IF EXISTS `examine`;
DROP TABLE IF EXISTS `genshin_pixiv`;

CREATE TABLE `genshin_pixiv` (
  `id` bigint(11) unsigned NOT NULL AUTO_INCREMENT,
  `illusts_id` bigint(11) unsigned NOT NULL COMMENT 'Pixiv artwork id',
  `title` varchar(255) DEFAULT NULL COMMENT 'Pixiv artwork title',
  `tags` varchar(255) DEFAULT NULL COMMENT 'Pixiv artwork tags',
  `view_count` bigint(11) unsigned DEFAULT NULL COMMENT 'Pixiv artwork views',
  `like_count` bigint(11) unsigned DEFAULT NULL COMMENT 'Pixiv artwork likes',
  `love_count` bigint(11) unsigned DEFAULT NULL COMMENT 'Pixiv artwork loves',
  `user_id` bigint(11) unsigned DEFAULT NULL COMMENT 'Pixiv artwork author id',
  `upload_timestamp` bigint(11) unsigned DEFAULT NULL COMMENT 'Pixiv artwork upload time',
  PRIMARY KEY (`id`,`illusts_id`) USING BTREE,
  UNIQUE KEY `illusts_id` (`illusts_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `examine` (
  `illusts_id` bigint(11) unsigned NOT NULL COMMENT 'Pixiv artwork id',
  `type` VARCHAR(255) DEFAULT NULL COMMENT '审核类型(Audit type): SFW, NSFW, R18',
  `data` varchar(255) DEFAULT NULL,
  `reason` varchar(255) DEFAULT NULL COMMENT '审核违规原因(Audit comment)',
  `status` int(11) DEFAULT NULL COMMENT '审核状态(Audit status): 0 未审核, 1 通过, 2 违规, 3 已推送',
  PRIMARY KEY (`illusts_id`),
  CONSTRAINT `examine_ibfk_1` FOREIGN KEY (`illusts_id`) REFERENCES `genshin_pixiv` (`illusts_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `pixiv_artist` (
  `user_id` bigint(11) unsigned NOT NULL COMMENT 'Pixiv user id',
  `last_art_id` bigint(11) unsigned DEFAULT NULL COMMENT 'Last crawled art id',
  `last_crawled_at` datetime DEFAULT NOW() COMMENT 'Last crawled time',
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE OR REPLACE VIEW `genshin_pixiv_audit`
AS SELECT gp.id, gp.illusts_id, gp.title, gp.tags, gp.view_count,
          gp.like_count, gp.love_count, gp.user_id, gp.upload_timestamp,
          ad.type, ad.status, ad.reason
FROM `genshin_pixiv` AS gp
LEFT OUTER JOIN `examine` AS ad
    ON gp.illusts_id = ad.illusts_id;

CREATE OR REPLACE VIEW genshin_pixiv_audit_sfw
AS SELECT *
FROM `genshin_pixiv_audit`
WHERE type LIKE 'SFW' OR (tags NOT LIKE '%R-18%' AND type IS NULL);

CREATE OR REPLACE VIEW genshin_pixiv_audit_nsfw
AS SELECT *
FROM `genshin_pixiv_audit`
WHERE type LIKE 'NSFW';

CREATE OR REPLACE VIEW genshin_pixiv_audit_r18
AS SELECT *
FROM `genshin_pixiv_audit`
WHERE type LIKE 'R18' OR (tags LIKE '%R-18%' AND type IS NULL);

CREATE OR REPLACE VIEW `pixiv_approved_artist` AS
SELECT gp.user_id, pa.last_art_id, pa.last_crawled_at, COUNT(gp.user_id) AS approved_art_count
FROM `genshin_pixiv` AS gp
    INNER JOIN `examine` AS ex
    ON gp.illusts_id = ex.illusts_id
    LEFT OUTER JOIN `pixiv_artist` AS pa
    ON gp.user_id = pa.user_id
WHERE ex.status = 1 OR ex.status = 3
GROUP BY gp.user_id
ORDER BY approved_art_count DESC;

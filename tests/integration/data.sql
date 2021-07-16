DROP VIEW IF EXISTS `genshin_pixiv_audit_r18`;
DROP VIEW IF EXISTS `genshin_pixiv_audit_nsfw`;
DROP VIEW IF EXISTS `genshin_pixiv_audit_sfw`;
DROP VIEW IF EXISTS `genshin_pixiv_audit`;

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

INSERT INTO `genshin_pixiv` VALUES (
  226,90829805,'バーバラ水着','#原神#バーバラ#バーバラ(原神)#サマータイムスパークル#原神1000users入り',3530,783,1165,6649124,1624716761
),(
  426,90912717,'胡桃','#GenshinImpact#原神#胡桃(原神)#胡桃#HuTao',3521,535,1110,8333579,1625037074
),(
  3038,91160535,'Raiden Shogun','#R-18#Baal#GenshinImpact#バアル#雷電将軍,#raidenshogun#原神#雷電将軍(原神)',8377,921,2049,70617660,1625948170
);

CREATE TABLE `examine` (
  `illusts_id` bigint(11) unsigned NOT NULL COMMENT 'Pixiv artwork id',
  `type` VARCHAR(255) DEFAULT NULL COMMENT '审核类型(Audit type): SFW, NSFW, R18',
  `data` varchar(255) DEFAULT NULL,
  `reason` varchar(255) DEFAULT NULL COMMENT '审核违规原因(Audit comment)',
  `status` int(11) DEFAULT NULL COMMENT '审核状态(Audit status): 0 未审核, 1 通过, 2 违规, 3 已推送',
  PRIMARY KEY (`illusts_id`),
  CONSTRAINT `examine_ibfk_1` FOREIGN KEY (`illusts_id`) REFERENCES `genshin_pixiv` (`illusts_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `examine` VALUES (
  90829805,'SFW',NULL,NULL,0
),(
  90912717,'NSFW',NULL,'NSFW',0
),(
  91160535,'R18',NULL,'R18',0
);

CREATE VIEW `genshin_pixiv_audit`
AS SELECT gp.id, gp.illusts_id, gp.title, gp.tags, gp.view_count,
          gp.like_count, gp.love_count, gp.user_id, gp.upload_timestamp,
          ad.type, ad.status, ad.reason
FROM `genshin_pixiv` AS gp
LEFT OUTER JOIN `examine` AS ad
    ON gp.illusts_id = ad.illusts_id;

CREATE VIEW genshin_pixiv_audit_sfw
AS SELECT *
FROM `genshin_pixiv_audit`
WHERE tags NOT LIKE '%R-18%' AND (type LIKE 'SFW' OR type IS NULL);

CREATE VIEW genshin_pixiv_audit_nsfw
AS SELECT *
FROM `genshin_pixiv_audit`
WHERE tags NOT LIKE '%R-18%' AND type LIKE 'NSFW';

CREATE VIEW genshin_pixiv_audit_r18
AS SELECT *
FROM `genshin_pixiv_audit`
WHERE tags LIKE '%R-18%' OR type LIKE 'R18';

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
    1,90751154,'甘雨','#甘雨(原神)#甘雨#原神#GenshinImpact#チャイナドレス#尻神様#原神5000users入り#可愛い女の子',25505,5476,8929,25447095,1624417521
),(
    258,90880870,'ジン','#R-18#原神#ジン#尻神様#後背位#ジン・グンヒルド#金髪#ジン(原神)#蒸れ',125219,13121,20180,464063,1624892412
),(
    310,90901859,'甘雨','#R-18#GenshinImpact#原神#甘雨(原神)#魅惑のふともも#sex',10458,1486,2557,62776999,1624978812
);

CREATE TABLE `examine` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `gp_id` bigint(11) unsigned DEFAULT NULL COMMENT 'Foreign table id',
  `gp_illusts_id` bigint(11) unsigned DEFAULT NULL COMMENT 'Pixiv artwork id',
  `type` varchar(255) DEFAULT NULL COMMENT '审核类型(Audit type): SFW, NSFW, R18',
  `data` varchar(255) DEFAULT NULL,
  `reason` varchar(255) DEFAULT NULL COMMENT '审核违规原因(Audit comment)',
  `status` int(11) DEFAULT NULL COMMENT '审核状态(Audit status): 0 未审核, 1 通过, 2 违规, 3 已推送',
  PRIMARY KEY (`id`),
  UNIQUE KEY `gp_id` (`gp_id`,`gp_illusts_id`),
  KEY `examine_ibfk_1` (`gp_id`,`gp_illusts_id`),
  CONSTRAINT `examine_ibfk_1` FOREIGN KEY (`gp_id`, `gp_illusts_id`) REFERENCES `genshin_pixiv` (`id`, `illusts_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE VIEW `genshin_pixiv_audit`
AS SELECT gp.id, gp.illusts_id, gp.title, gp.tags, gp.view_count,
          gp.like_count, gp.love_count, gp.user_id, gp.upload_timestamp,
          ad.type, ad.status, ad.reason
FROM `genshin_pixiv` AS gp
LEFT OUTER JOIN `examine` AS ad
    ON gp.id = ad.gp_id AND gp.illusts_id = ad.gp_illusts_id;

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

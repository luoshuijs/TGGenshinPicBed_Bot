/*
 Navicat Premium Data Transfer

 Source Server         : 本地服务器 MySQL
 Source Server Type    : MySQL
 Source Server Version : 80023 (8.0.23)
 Source Host           : localhost:3306
 Source Schema         : paihub

 Target Server Type    : MySQL
 Target Server Version : 80023 (8.0.23)
 File Encoding         : 65001

 Date: 14/10/2023 17:48:16
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for artwork
-- ----------------------------
DROP TABLE IF EXISTS `artwork`;
CREATE TABLE `artwork`  (
  `id` bigint UNSIGNED NOT NULL COMMENT '唯一ID',
  `web_id` bigint UNSIGNED NULL DEFAULT NULL COMMENT '网站ID',
  `original_id` bigint UNSIGNED NULL DEFAULT NULL COMMENT '作品原始ID',
  `artist_id` bigint UNSIGNED NULL DEFAULT NULL COMMENT '画师ID'
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for artist
-- ----------------------------
DROP TABLE IF EXISTS `artist`;
CREATE TABLE `artist`  (
  `id` bigint UNSIGNED NOT NULL COMMENT 'id',
  `web_id` bigint UNSIGNED NOT NULL COMMENT '网站ID',
  `artist_id` bigint UNSIGNED NULL DEFAULT NULL COMMENT '画师ID',
  `status` tinyint NULL DEFAULT NULL COMMENT '如果选择了whitelist或blacklist，这将成为审核的主要依据',
  `remark` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for auto_review_rules
-- ----------------------------
DROP TABLE IF EXISTS `auto_review_rules`;
CREATE TABLE `auto_review_rules`  (
  `id` bigint UNSIGNED NOT NULL COMMENT '自动审核表 主键',
  `work_id` bigint UNSIGNED NULL DEFAULT NULL COMMENT '对那个作品类型进行匹配',
  `name` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '自动审核名称',
  `description` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '自动审核描述',
  `action` tinyint NULL DEFAULT NULL COMMENT '规则匹配时的操作 0拒绝 1通过',
  `status` tinyint NULL DEFAULT NULL COMMENT '规则是否启用',
  `rules` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL COMMENT '包含多个正则表达式或规则的JSON结构',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for pixiv
-- ----------------------------
DROP TABLE IF EXISTS `pixiv`;
CREATE TABLE `pixiv`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'Pixiv artwork title',
  `tags` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'Pixiv artwork tags',
  `view_count` bigint UNSIGNED NULL DEFAULT NULL COMMENT 'Pixiv artwork views',
  `like_count` bigint UNSIGNED NULL DEFAULT NULL COMMENT 'Pixiv artwork likes',
  `love_count` bigint UNSIGNED NULL DEFAULT NULL COMMENT 'Pixiv artwork loves',
  `artist_id` bigint UNSIGNED NULL DEFAULT NULL COMMENT 'Pixiv artwork artist id',
  `create_by` int NOT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `update_by` int NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for push
-- ----------------------------
DROP TABLE IF EXISTS `push`;
CREATE TABLE `push`  (
  `id` bigint UNSIGNED NOT NULL COMMENT '唯一ID',
  `review_id` bigint UNSIGNED NULL DEFAULT NULL COMMENT '关联review表',
  `channel_id` bigint UNSIGNED NULL DEFAULT NULL COMMENT '推送到的频道名称或ID',
  `date` datetime NULL DEFAULT NULL COMMENT '推送日期',
  `status` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '推送状态（例如：“已推送”，“失败”等）',
  `create_by` int NOT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `update_by` int NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for review
-- ----------------------------
DROP TABLE IF EXISTS `review`;
CREATE TABLE `review`  (
  `id` bigint UNSIGNED NOT NULL COMMENT '审核ID',
  `artwork_id` bigint UNSIGNED NOT NULL COMMENT '数据库中的作品ID',
  `work_id` bigint UNSIGNED NULL DEFAULT NULL COMMENT '工作类型',
  `status` tinyint NOT NULL COMMENT '审核状态 如拒绝或者通过',
  `auto` tinyint NULL DEFAULT NULL COMMENT '是否为自动审核',
  `reviewer_notes` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '审核信息',
  `create_by` int NOT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `update_by` int NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for web
-- ----------------------------
DROP TABLE IF EXISTS `web`;
CREATE TABLE `web`  (
  `id` bigint UNSIGNED NOT NULL COMMENT '网站ID',
  `web_name` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '网站名称',
  `web_key` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '网站标识字符串',
  `create_by` int NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `update_by` int NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  `remark` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for work
-- ----------------------------
DROP TABLE IF EXISTS `work`;
CREATE TABLE `work`  (
  `id` bigint UNSIGNED NOT NULL COMMENT '作品归类表 主键',
  `name` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  `description` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for work_channel
-- ----------------------------
DROP TABLE IF EXISTS `work_channel`;
CREATE TABLE `work_channel`  (
  `id` bigint UNSIGNED NOT NULL,
  `work_id` bigint UNSIGNED NULL DEFAULT NULL,
  `channel_id` bigint UNSIGNED NULL DEFAULT NULL COMMENT '频道ID',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for work_rules
-- ----------------------------
DROP TABLE IF EXISTS `work_rules`;
CREATE TABLE `work_rules`  (
  `id` bigint UNSIGNED NOT NULL COMMENT '作品区分规则表 主键ID',
  `work_id` bigint UNSIGNED NULL DEFAULT NULL COMMENT '绑定的作品类型',
  `order_num` int NULL DEFAULT NULL COMMENT '执行循序',
  `name` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '作品名称类型',
  `description` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '作品类型描述',
  `pattern` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '作品模式',
  `status` tinyint NULL DEFAULT NULL COMMENT '表达式匹配成功操作是拒绝还是通过',
  `action` tinyint NULL DEFAULT NULL COMMENT '规则匹配时的操作 0拒绝 1通过',
  `rules` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL COMMENT '包含多个正则表达式或规则的JSON结构',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;

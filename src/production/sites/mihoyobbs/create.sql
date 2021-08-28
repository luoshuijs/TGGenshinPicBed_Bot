CREATE TABLE `mihoyobbs` (
    id BIGINT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
    post_id BIGINT(20) UNSIGNED NOT NULL,
    title VARCHAR(256) DEFAULT NULL,
    tags VARCHAR(256) DEFAULT NULL,
    views INT DEFAULT 0 COMMENT 'Views',
    likes INT DEFAULT 0 COMMENT 'Likes',
    replies INT DEFAULT 0 COMMENT 'Replies',
    forwards INT DEFAULT 0 COMMENT 'Forwards',
    bookmarks INT DEFAULT 0 COMMENT 'Bookmarks',
    created_at BIGINT(11) UNSIGNED DEFAULT NULL COMMENT 'Upload time',
    user_id BIGINT(11) DEFAULT NULL COMMENT 'User id',
    PRIMARY KEY (id),
    UNIQUE KEY (post_id)
);

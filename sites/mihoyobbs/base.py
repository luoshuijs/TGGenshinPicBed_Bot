from model.artwork import ArtworkInfo, AuditInfo, AuditType, AuditStatus


class MStat:
    def __init__(self, view_num: int = 0, reply_num: int = 0, like_num: int = 0, bookmark_num: int = 0,
                 forward_num: int = 0):
        self.forward_num = forward_num  # 关注数
        self.bookmark_num = bookmark_num  # 收藏数
        self.like_num = like_num  # 喜欢数
        self.reply_num = reply_num  # 回复数
        self.view_num = view_num  # 观看数


class MArtworkInfo:
    def __init__(self, database_id: int = 0, post_id: int = 0, subject: str = "", tags=None,
                 image_url_list=None, stat: MStat = None, uid: int = 0, created_at: int = 0):
        if tags is None:
            self.tags = []
        else:
            self.tags = tags
        if image_url_list is None:
            self.image_url_list = []
        else:
            self.image_url_list = image_url_list
        self.database_id = database_id
        self.Stat = stat
        self.created_at = created_at
        self.uid = uid
        self.subject = subject
        self.post_id = post_id

    def GetStringTags(self) -> str:
        tags_str: str = ""
        if len(self.tags) == 0:
            return ""
        for tag in self.tags:  # 之前考虑过使用 string.join(seq) 但是还是算了
            temp_tag = "#%s" % tag
            tags_str += temp_tag
        return tags_str

    def SetStringTags(self, tags: str):
        tags_list = tags.split("#")
        tags_list.remove("")
        self.tags = tags_list

    def GetArtworkInfo(self):
        artwork_info = ArtworkInfo()
        artwork_info.origin_url = f"https://bbs.mihoyo.com/ys/article/{self.post_id}"
        artwork_info.site_name = "MiHoYoBBS"
        artwork_info.site = "mihoyobbs"
        artwork_info.info = self
        artwork_info.title = self.subject
        artwork_info.tags = self.tags
        artwork_info.artwork_id = self.post_id
        artwork_info.stat = self.Stat
        artwork_info.create_timestamp = self.created_at
        return artwork_info


def CreateMArtworkFromSQLData(data: tuple) -> MArtworkInfo:
    (database_id, post_id, title, tags, view_num, reply_num, like_num, bookmark_num, forward_num, uid,
     created_at) = data
    stat: MStat = MStat(view_num=view_num, reply_num=reply_num, like_num=like_num, bookmark_num=bookmark_num,
                        forward_num=forward_num)
    data = MArtworkInfo(database_id=database_id, post_id=post_id, subject=title, stat=stat,
                        uid=uid, created_at=created_at)
    data.SetStringTags(tags)
    return data


def CreateArtworkListFromAPIResponse(response: dict) -> list:
    try:
        retcode = response["retcode"]
        if retcode != 0:
            return None
        data_list = response["data"]["list"]
    except (AttributeError, TypeError):
        return None
    temp_list = []
    for data in data_list:
        temp_list.append(CreatePostInfoFromAPIResponse(data))
    return temp_list


def CreateArtworkInfoFromAPIResponse(response: dict) -> MArtworkInfo:
    try:
        retcode = response["retcode"]
        if retcode != 0:
            return None
        data_post = response["data"]["post"]
    except (AttributeError, TypeError):
        return None
    return CreatePostInfoFromAPIResponse(data_post)


def CreatePostInfoFromAPIResponse(data_post: dict) -> MArtworkInfo:
    try:
        post = data_post["post"]  # 投稿信息
        post_id = post["post_id"]
        subject = post["subject"]  # 介绍，类似title标题
        created_at = post["created_at"]  # 创建时间
        user = data_post["user"]  # 用户数据
        uid = user["uid"]  # 用户ID
        topics = data_post["topics"]  # 存放 Tag
        image_list = data_post["image_list"]  # image_list
    except (AttributeError, TypeError):
        return None
    topics_list = []
    images_list = []
    for topic in topics:
        topics_list.append(topic["name"])
    for image in image_list:
        images_list.append(image["url"])
    stat = MStat(view_num=data_post["stat"]["view_num"],
                 reply_num=data_post["stat"]["reply_num"],
                 like_num=data_post["stat"]["like_num"],
                 bookmark_num=data_post["stat"]["bookmark_num"],
                 forward_num=data_post["stat"]["forward_num"],
                 )
    return MArtworkInfo(
        subject=subject,
        created_at=created_at,
        uid=uid,
        stat=stat,
        tags=topics_list,
        post_id=post_id,
        image_url_list=images_list
    )


class MiHoYoBBSResponse:
    def __init__(self, response=None, error_message: str = ""):
        if response is None:
            self.error: bool = True
            self.message: str = error_message
            return
        self.response: dict = response
        self.code = response["retcode"]
        if self.code == 0:
            self.error = False
        else:
            if self.code == 1102:
                self.message = "作品不存在"
            self.error = True
            return
        if response["data"] is None:
            self.error = True
        self.message: str = response["message"]
        if self.error:
            return
        try:
            self._data_post = response["data"]["post"]
            post = self._data_post["post"]  # 投稿信息
            post_id = post["post_id"]
            subject = post["subject"]  # 介绍，类似title标题
            created_at = post["created_at"]  # 创建时间
            user = self._data_post["user"]  # 用户数据
            uid = user["uid"]  # 用户ID
            topics = self._data_post["topics"]  # 存放 Tag
            image_list = self._data_post["image_list"]  # image_list
        except (AttributeError, TypeError) as err:
            self.error: bool = True
            self.message: str = err
            return
        topics_list = []
        image_url_list = []
        for topic in topics:
            topics_list.append(topic["name"])
        for image in image_list:
            image_url_list.append(image["url"])
        self.post_id = post["post_id"]
        self.user_id = user["uid"]
        self.created_at = post["created_at"]
        stat = MStat(view_num=self._data_post["stat"]["view_num"],
                     reply_num=self._data_post["stat"]["reply_num"],
                     like_num=self._data_post["stat"]["like_num"],
                     bookmark_num=self._data_post["stat"]["bookmark_num"],
                     forward_num=self._data_post["stat"]["forward_num"],
                     )
        self.results = MArtworkInfo(
            subject=subject,
            created_at=created_at,
            uid=uid,
            stat=stat,
            tags=topics_list,
            post_id=post_id,
            image_url_list=image_url_list
        )

    def __bool__(self):
        return self.error

    def __len__(self):
        return len(self.results.image_url_list)


def CreateArtworkAuditInfoFromSQLData(data: tuple) -> AuditInfo:
    (post_id, type_status, status, reason) = data
    return AuditInfo(site='mihoyobbs',
                     connection_id=post_id,
                     type_status=AuditType(type_status),
                     status=AuditStatus(status),
                     reason=reason
                     )

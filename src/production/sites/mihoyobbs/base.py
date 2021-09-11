class MStat:
    def __init__(self, view_num: int = 0, reply_num: int = 0, like_num: int = 0, bookmark_num: int = 0,
                 forward_num: int = 0):
        self.forward_num = forward_num  # 关注数
        self.bookmark_num = bookmark_num  # 收藏数
        self.like_num = like_num  # 喜欢数
        self.reply_num = reply_num  # 回复数
        self.view_num = view_num  # 观看数


class MArtworkInfo:
    def __init__(self, database_id: int = 0, post_id: int = 0, subject: str = "", tags: list = [], stat: MStat = None,
                 image_list: list = [], Stat: MStat = None, uid: int = 0, created_at: int = 0):
        self.database_id = database_id
        self.Stat = Stat
        self.image_list = image_list
        self.created_at = created_at
        self.uid = uid
        self.subject = subject
        self.post_id = post_id
        self.tags = tags

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
        post_id=post_id
    )

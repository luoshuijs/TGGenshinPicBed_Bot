class MStat:
    # 我在想以后统一是使用这个
    def __init__(self, view_num: int = 0, reply_num=0, like_num: int = 0, bookmark_num: int = 0, forward_num: int = 0):
        self.forward_num = forward_num  # 关注数
        self.bookmark_num = bookmark_num  # 收藏数
        self.like_num = like_num  # 喜欢数
        self.reply_num = reply_num  # 回复数
        self.view_num = view_num  # 观看数


class MArtworkInfo:
    def __init__(self, post_id: int = 0, subject: str = "", tags: list = [], image_list: list = [], Stat: MStat = None,
                 height: int = 0, width: int = 0, uid: int = 0, created_at: int = 0):
        self.Stat = Stat
        self.image_list = image_list
        self.width = width
        self.height = height
        self.created_at = created_at
        self.uid = uid
        self.subject = subject
        self.post_id = post_id
        self.tags = tags


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
        subject = post["subject"]  # 介绍，类似title标题
        created_at = post["created_at"]  # 创建时间
        user = data_post["user"]  # 用户数据
        uid = user["uid"]  # 用户ID
        topics = data_post["topics"]  # 存放 Tag
        image_list = data_post["image_list"]  # image_list
        height = image_list[0]["height"]
        width = image_list[0]["width"]
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
        height=height,
        width=width
    )

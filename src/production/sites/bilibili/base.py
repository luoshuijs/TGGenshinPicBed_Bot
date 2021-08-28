import ujson


class BStat:
    def __init__(self, view: int = 0, like: int = 0, repos: int = 0, comment: int = 0):
        self.comment = comment  # 评论数
        self.repos = repos  # 转发数
        self.like = like  # 喜欢数
        self.view = view  # 观看数


class BArtworkInfo:
    def __init__(self, database_id: int = 0, dynamic_id: int = 0, description: str = "", tags: list = [],
                 image_list: list = [], Stat: BStat = None, height: int = 0, width: int = 0, uid: int = 0,
                 timestamp: int = 0):
        self.database_id = database_id
        self.Stat = Stat
        self.image_list = image_list
        self.width = width
        self.height = height
        self.created_at = timestamp  # 创建时间
        self.uid = uid
        self.description = description  # 描述
        self.dynamic_id = dynamic_id
        self.tags = tags


def CreateArtworkInfoFromAPIResponse(response: dict) -> BArtworkInfo:
    try:
        if response["code"] != 0:
            return None
    except (AttributeError, TypeError):
        return None
    cards = response['data']['card']['card']
    desc = response['data']['card']['desc']
    display = response['data']['card']['display']
    card = ujson.loads(cards)  # 套娃JSON解析
    pictures = card['item']['pictures']
    dynamic_id = desc["dynamic_id"]
    uid = desc["uid"]
    view = desc["view"]
    repos = desc["repos"]
    comment = desc["comment"]
    like = desc["like"]
    timestamp = desc["timestamp"]
    description = card['item']["description"]
    topic_details = display["topic_info"]["topic_details"]
    height = pictures[0]["img_height"]
    width = pictures[0]["img_width"]
    tag_list = []
    url_list = []
    stat = BStat(view=view,
                 repos=repos,
                 comment=comment,
                 like=like
                 )
    for topic_detail in topic_details:
        tag_list.append(topic_detail["topic_name"])
    for picture in pictures:
        url_list.append(picture['img_src'])
    return BArtworkInfo(
        dynamic_id=dynamic_id,
        description=description,
        timestamp=timestamp,
        stat=stat,
        height=height,
        width=width,
        uid=uid,
        tags=tag_list,
        image_list=url_list
    )


def CreateTArtworkFromSQLData(data) -> BArtworkInfo:
    (id, dynamic_id, description, tags, view, like, comment, repos, height,
     width, uid, timestamp) = data
    stat: BStat = BStat(view=view, like=like, comment=comment, repos=repos)
    data = BArtworkInfo(database_id=id, dynamic_id=dynamic_id, description=description,
                        stat=stat, uid=uid, height=height, width=width, timestamp=timestamp)
    data.SetStringTags(tags)
    return data

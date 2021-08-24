def CreateArtworkListFromAPIResponse(response: dict) -> list:
    try:
        retcode = response["retcode"]
        if retcode != 0:
            return None
        data_list = response["list"]
    except (AttributeError, TypeError):
        return None
    for data in data_list:
        # 果然还是米哈游的API数据最全
        user = data["user"]  # 用户数据
        post = data["post"]  # 投稿信息
        stat = data["stat"]  # stat为图片具体数据，如收藏，点赞，观看
        user = data["topics"]  # 存放 Tag
        subject = data["subject"]  # 介绍，类似title标题
        image_list = data["image_list"]  # 图片list

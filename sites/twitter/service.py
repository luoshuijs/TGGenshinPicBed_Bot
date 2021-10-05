from typing import Tuple, Iterable, Optional

from model.artwork import ArtworkInfo, ArtworkImage
from model.containers import ArtworkData
from sites.twitter.api import TwitterDownloader
from sites.twitter.repository import TwitterRepository


class TwitterService:
    def __init__(self, sql_config=None):
        self.TwitterRepository = TwitterRepository(**sql_config)
        self.TwitterDownloader = TwitterDownloader()

    def get_info_and_image(self, art_id: int) -> Optional[Tuple[ArtworkInfo, Iterable[ArtworkImage]]]:
        temp_artwork_info = self.TwitterDownloader.TwitterApi.get_artwork_info(art_id)
        if temp_artwork_info is None:
            return None
        artwork_image = self.TwitterDownloader.get_images_by_artid(art_id)
        artwork_info = ArtworkInfo(data=temp_artwork_info)
        return artwork_info, artwork_image

    def contribute_start(self, art_id: int) -> ArtworkData:
        artwork_data = ArtworkData()
        temp_artwork_info = self.TwitterRepository.get_art_by_artid(art_id)
        if temp_artwork_info is not None:
            artwork_data.SetError("已经存在数据库")
            return artwork_data
        temp_artwork_info = self.TwitterDownloader.TwitterApi.get_artwork_info(art_id)
        if temp_artwork_info is None:
            artwork_data.SetError("已经存在数据库")
            return artwork_data
        artwork_image = self.TwitterDownloader.get_images_by_artid(art_id)
        artwork_info = ArtworkInfo(data=temp_artwork_info)
        artwork_data.artwork_image = artwork_image
        artwork_data.artwork_info = artwork_info
        return artwork_data

    def contribute_confirm(self, artwork_info: ArtworkInfo):
        # Save to database
        self.TwitterRepository.save_art_one(artwork_info.info)

from typing import Tuple, Iterable

from src.base.model.newartwork import ArtworkInfo, ArtworkImage
from src.production.sites.twitter.api import TwitterDownloader
from src.production.sites.twitter.repository import TwitterRepository


class TwitterService:
    def __init__(self, sql_config=None):
        self.TwitterRepository = TwitterRepository(**sql_config)
        self.TwitterDownloader = TwitterDownloader()

    def contribute_start(self, art_id: int) -> Tuple[ArtworkInfo, Iterable[ArtworkImage]]:
        # 1. Check database
        temp_artwork_info = self.TwitterRepository.get_art_by_artid(art_id)
        if temp_artwork_info is not None:
            return None
        artwork_image = self.TwitterDownloader.get_images_by_artid(art_id)
        artwork_info = ArtworkInfo(data=temp_artwork_info)
        return artwork_info, artwork_image

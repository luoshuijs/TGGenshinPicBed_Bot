import pathlib
from typing import Iterable, Tuple
from contextlib import contextmanager


from src.model.artwork import AuditType, ArtworkInfo, AuditInfo, AuditStatus, ArtworkFactory
from src.production.namemap import NameMap
from src.production.pixiv.repository import PixivRepository, Transformer
from src.production.pixiv.downloader import PixivDownloader, ArtworkImage
from src.production.pixiv.cache import PixivCache
from src.production.redisaction import RedisUpdate
from src.production import auditor


class PixivService:

    def __init__(self, sql_config=None, redis_config=None, px_config=None):
        self.pixivrepo = PixivRepository(**sql_config)
        self.pixivcache = PixivCache(**redis_config)
        self.pixivdownloader = PixivDownloader(**px_config)
        name_map_file = pathlib.Path(__file__).parent.joinpath("../../../data/namemap.json").resolve()
        self.name_map = NameMap(name_map_file)

    def contribute_start(self, art_id: int) -> Tuple[ArtworkInfo, Iterable[ArtworkImage]]:
        # 1. Check database
        data = self.pixivrepo.get_art_by_artid(art_id)
        artwork_list = ArtworkFactory.create_from_sql_no_id(data)
        if len(artwork_list) > 0:
            return None     # Exists in database
        # 2. Get artwork info
        artwork_info = self.pixivdownloader.get_artwork_info(art_id)
        if artwork_info is None:
            return None     # Artwork does not exist
        art_id = artwork_info.art_id
        images = self.pixivcache.get_images_by_artid(art_id)
        if images is None:
            images = self.pixivdownloader.download_images(art_id)
            self.pixivcache.save_images_by_artid(art_id, images)
        return artwork_info, images

    def contribute_confirm(self, art_id: int):
        # 1. Get artwork info
        result = self.contribute_start(art_id)
        if result is None:
            return None
        artwork_info, images = result
        # 2. Save to database
        self.pixivrepo.save_art_one(artwork_info)

    def audit_start(self, audit_type: AuditType) -> int:
        # 1. Get from database
        data = self.pixivrepo.get_art_for_audit(audit_type)
        artwork_audit_list = ArtworkFactory.create_from_sql_no_id(data)
        # 2. Save to redis
        update = RedisUpdate.add_audit(audit_type, artwork_audit_list)
        return self.pixivcache.apply_update(update)

    def audit_next(self, audit_type: AuditType):
        # 1. Get from redis
        update = RedisUpdate.get_audit_one(audit_type)
        data = self.pixivcache.apply_update(update)
        if data is None:
            return None
        artwork_info = ArtworkInfo.create_from_json(data)
        tags = self.name_map.filter_character_tags(artwork_info.tags)
        artwork_info.tags = tags
        # 2. Download image(s)
        art_id = artwork_info.art_id
        images = self.pixivcache.get_images_by_artid(art_id)
        if images is None:
            images = self.pixivdownloader.download_images(art_id)
            self.pixivcache.save_images_by_artid(art_id, images)
        return artwork_info, images

    def audit_approve(self, audit_type: AuditType, art_id: int):
        # 1. Remove redis cache
        update = RedisUpdate.remove_pending(audit_type, art_id)
        self.pixivcache.apply_update(update)
        # 2. Get from database
        transformer = Transformer.combine(Transformer.audit_type(audit_type), Transformer.r18_type())
        data = self.pixivrepo.get_art_by_artid(art_id, transformer)
        artwork_audit_list = ArtworkFactory.create_from_sql_no_id(data)
        if len(artwork_audit_list) == 0:
            raise ValueError(f"art not found: art id {art_id} when approving artwork")
        # 3. Audit
        art = artwork_audit_list[0]
        update = auditor.approve(art.audit_info)
        # 4. Save to database
        self.pixivrepo.apply_update(update)

    def audit_reject(self, audit_type: AuditType, art_id: int, reason: str):
        # 1. Remove redis cache
        update = RedisUpdate.remove_pending(audit_type, art_id)
        self.pixivcache.apply_update(update)
        # 2. Get from database
        transformer = Transformer.combine(Transformer.audit_type(audit_type), Transformer.r18_type())
        data = self.pixivrepo.get_art_by_artid(art_id, transformer)
        artwork_audit_list = ArtworkFactory.create_from_sql_no_id(data)
        if len(artwork_audit_list) == 0:
            raise ValueError(f"art not found: art id {art_id} when rejecting artwork")
        # 3. Audit
        art = artwork_audit_list[0]
        update = auditor.reject(art.audit_info, reason=reason)
        # 4. Save to database
        self.pixivrepo.apply_update(update)

    def audit_cancel(self, audit_type: AuditType, art_id: int):
        # 1. Putback audit
        update = RedisUpdate.putback_audit(audit_type, art_id)
        self.pixivcache.apply_update(update)

    def push_start(self, audit_type: AuditType) -> int:
        # 1. Get from database
        data = self.pixivrepo.get_art_for_push(audit_type)
        artwork_audit_list = ArtworkFactory.create_from_sql_no_id(data)
        # 2. Save to redis
        update = RedisUpdate.add_push(audit_type, artwork_audit_list)
        return self.pixivcache.apply_update(update)

    def push_next(self, audit_type: AuditType) -> Tuple[ArtworkInfo, Iterable[ArtworkImage], int]:
        # 1. Get from redis
        update = RedisUpdate.get_push_one(audit_type)
        data, count = self.pixivcache.apply_update(update)
        if data is None:
            return None
        artwork_info = ArtworkInfo.create_from_json(data)
        tags = self.name_map.filter_character_tags(artwork_info.tags)
        artwork_info.tags = tags
        # 2. Download image(s)
        art_id = artwork_info.art_id
        images = self.pixivcache.get_images_by_artid(art_id)
        if images is None:
            images = self.pixivdownloader.download_images(art_id)
            self.pixivcache.save_images_by_artid(art_id, images)
        return artwork_info, images, count

    @contextmanager
    def push_manager(self, artwork_info):
        yield
        update = auditor.push(artwork_info.audit_info)
        self.pixivrepo.apply_update(update)

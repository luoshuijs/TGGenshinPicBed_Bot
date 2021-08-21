import pathlib
from typing import Iterable, Tuple
from contextlib import contextmanager


from src.base.model.artwork import AuditStatus, AuditType, ArtworkInfo
from src.base.utils.namemap import NameMap
from src.production.pixiv.repository import PixivRepository, Transformer
from src.production.pixiv.downloader import PixivDownloader, ArtworkImage
from src.production.pixiv.cache import PixivCache
from src.production.pixiv import auditor
from src.base.utils.redisaction import RedisUpdate


class PixivService:

    def __init__(self, sql_config=None, redis_config=None, px_config=None):
        self.pixivrepo = PixivRepository(**sql_config)
        self.pixivcache = PixivCache(**redis_config)
        self.pixivdownloader = PixivDownloader(**px_config)
        name_map_file = pathlib.Path(__file__).parent.joinpath("../../../data/namemap.json").resolve()
        self.name_map = NameMap(name_map_file)

    def contribute_start(self, art_id: int) -> Tuple[ArtworkInfo, Iterable[ArtworkImage]]:
        # 1. Check database
        artwork_info = self.pixivrepo.get_art_by_artid(art_id)
        if artwork_info is not None:
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
        artwork_audit_list = self.pixivrepo.get_art_for_audit(audit_type)
        # 2. Save to redis
        update = RedisUpdate.add_audit(audit_type, artwork_audit_list)
        return self.pixivcache.apply_update(update)

    def audit_next(self, audit_type: AuditType, approve_threshold: int = -1):
        # 1. Get from redis
        def get_audit():
            update = RedisUpdate.get_audit_one(audit_type)
            data = self.pixivcache.apply_update(update)
            return data
        data = get_audit()
        if data is None:
            if self.pixivcache.audit_size(audit_type) == 0:
                return None
            self.audit_start(audit_type)
            data = get_audit()
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
        # 3. Auto approve
        if approve_threshold > -1:
            approved_art_count = self.pixivrepo.get_approved_art_count_by_artistid(artwork_info.author_id)
            if approved_art_count >= approve_threshold:
                self.audit_approve(audit_type, artwork_info.art_id)
                artwork_info = self.pixivrepo.get_art_by_artid(artwork_info.art_id)
        return artwork_info, images

    def audit_approve(self, audit_type: AuditType, art_id: int):
        # 1. Remove redis cache
        update = RedisUpdate.remove_pending(audit_type, art_id)
        self.pixivcache.apply_update(update)
        # 2. Get from database
        art = self.pixivrepo.get_art_by_artid(art_id)
        if art is None:
            raise ValueError(f"art not found: art id {art_id} when approving artwork")
        # 3. Audit
        update = auditor.approve(art.audit_info)
        # 4. Save to database
        self.pixivrepo.apply_update(update)

    def audit_reject(self, audit_type: AuditType, art_id: int, reason: str):
        # 1. Remove redis cache
        update = RedisUpdate.remove_pending(audit_type, art_id)
        self.pixivcache.apply_update(update)
        # 2. Get from database
        art = self.pixivrepo.get_art_by_artid(art_id)
        if art is None:
            raise ValueError(f"art not found: art id {art_id} when rejecting artwork")
        # 3. Audit
        update = auditor.reject(art.audit_info, reason=reason)
        # 4. Save to database
        self.pixivrepo.apply_update(update)

    def audit_cancel(self, audit_type: AuditType, art_id: int):
        # 1. Putback audit
        update = RedisUpdate.putback_audit(audit_type, art_id)
        self.pixivcache.apply_update(update)

    def push_start(self, audit_type: AuditType) -> int:
        # 1. Get from database
        artwork_audit_list = self.pixivrepo.get_art_for_push(audit_type)
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

    def cache_size(self, audit_type: AuditType):
        # 1. Get from redis
        return self.pixivcache.audit_size(audit_type)

    def get_artwork_image_by_art_id(self, art_id: int) -> Tuple[ArtworkInfo, Iterable[ArtworkImage]]:
        """
        Find the info and artwork images by art_id for confirmation
        """
        # 1. Check database
        artwork_info = self.pixivrepo.get_art_by_artid(art_id)
        if artwork_info is None:
            return None     # Does not exists in database
        # 2. Get artwork info
        artwork_exists = self.pixivdownloader.get_artwork_info(art_id)
        if artwork_exists is None:
            return None     # Artwork does not exist
        art_id = artwork_info.art_id
        images = self.pixivcache.get_images_by_artid(art_id)
        if images is None:
            images = self.pixivdownloader.download_images(art_id)
            self.pixivcache.save_images_by_artid(art_id, images)
        return artwork_info, images

    def set_art_audit_info(self, art_id: int, info_type: str, data, d_reason=None):
        """
        Set art audit status by art_id
        """
        if info_type not in ["status", "type"]:
            raise ValueError(f"Unknown operation for set_art_audit_info: {info_type}")
        # 1. Get artwork info
        artwork_info = self.pixivrepo.get_art_by_artid(art_id)
        if artwork_info is None:
            return None     # Does not exists in database
        # 2. Update status
        audit_info = artwork_info.audit_info
        audit_status = audit_info.audit_status
        audit_type = audit_info.audit_type
        audit_reason = audit_info.audit_reason
        if info_type == "status":
            audit_status = AuditStatus(data)
        elif info_type == "type":
            audit_type = AuditType(data)
            if d_reason is not None:
                audit_reason = str(d_reason)
        update = auditor.ArtworkStatusUpdate(
                audit_info=audit_info, status=audit_status, type=audit_type, reason=audit_reason)
        self.pixivrepo.apply_update(update)

    @contextmanager
    def push_manager(self, artwork_info):
        yield
        update = auditor.push(artwork_info.audit_info)
        self.pixivrepo.apply_update(update)

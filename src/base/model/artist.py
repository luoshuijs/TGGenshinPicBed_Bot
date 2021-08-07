class ArtistCrawlInfo:

    def __init__(self, user_id: int, last_art_id: int = None, last_crawled_at = None, approved_art_count: int = 0):
        self.user_id = user_id
        self.last_art_id = last_art_id
        self.last_crawled_at = last_crawled_at
        self.approved_art_count = approved_art_count

from typing import List

from model.artwork import ArtworkInfo, ArtworkImage


class BasicData:
    def __init__(self):
        self.message: str = ""
        self.status_code: int = -1
        self.is_error: bool = False

    def SetError(self, message: str):
        self.message = message
        self.is_error = True


class ArtworkData(BasicData):
    def __init__(self, artwork_info: ArtworkInfo = None, artwork_image: List[ArtworkImage] = None):
        super().__init__()
        self.artwork_info: ArtworkInfo = artwork_info
        self.artwork_image: List[ArtworkImage] = artwork_image





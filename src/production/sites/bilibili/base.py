import os


def CreateArtworkInfoFromAPIResponse(response: dict):
    try:
        if response["code"] != 0:
            return None
    except (AttributeError, TypeError):
        return None
    card = response['data']['card']['card']
    pics = card['item']['pictures']
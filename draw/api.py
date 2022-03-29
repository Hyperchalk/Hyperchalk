from ninja import NinjaAPI

from collab.api import collab_router

api = NinjaAPI(version="1", csrf=True)

api.add_router('collab', collab_router)

from sanic import response
from sanic.response import json

from bot import bp


@bp.route('/', methods=['GET'])
async def root(request):
    return response.json({'test': 'ok'})

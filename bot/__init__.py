from sanic import Sanic, Blueprint
import config

app = Sanic(__name__)

sanic_cfg = config.SERVER
bp = Blueprint(sanic_cfg['location'], url_prefix="/{0}".format(sanic_cfg['location']))

import bot.routes.root
import bot.routes.event
import bot.routes.action

app.blueprint(bp)


@app.listener('before_server_start')
async def create_sessions_dict(app, loop):
    app.sessions_dict = {}

app.run(host=sanic_cfg['host'],
        port=sanic_cfg['port'],
        workers=sanic_cfg['workers'],
        debug=sanic_cfg['debug'],
        auto_reload=sanic_cfg['auto_reload'])

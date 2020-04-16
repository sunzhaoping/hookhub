import os
import asyncio
# setup uvloop for asyncio
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
import zmq
import zmq.asyncio
import click
import logging
import signal
from aiohttp import web
from multiprocessing import cpu_count


async def handler(request):
    # read webhook name
    hook = request.match_info.get('hook', "")
    if not hook:
        return web.Response(text="OK")
    payload = await request.read()

    # send payload to client
    zsock = request.app["zsock"]
    await zsock.send_multipart([hook.encode(), payload])

    # send respone
    return web.json_response({"result":"OK"})


async def _server(router, log, host, port):
    # setup  logging 
    LOG_FORMAT = '[%(asctime)s] %(levelname)s %(message)s'
    numeric_level = getattr(logging, log.upper(), None)
    logging.basicConfig(format=LOG_FORMAT, level=numeric_level)

    loop = asyncio.get_running_loop()

    # start zmq endpoint
    cpu_cores = cpu_count()
    zmq_ctx = zmq.asyncio.Context.instance(cpu_cores)
    socket = zmq_ctx.socket(zmq.PUB, io_loop=loop)
    socket.bind(router)

    # start http server
    app = web.Application()
    app["zsock"] = socket
    app.add_routes([web.post('/{hook}', handler)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logging.info(f"server start at {host}:{port} pub endpoint: {router}")

    # watch close signal
    close_waiter = asyncio.Future()
    loop.add_signal_handler(signal.SIGTERM, close_waiter.set_result, None)
    loop.add_signal_handler(signal.SIGINT, close_waiter.set_result, None)
    await asyncio.shield(close_waiter)


@click.command()
@click.option('--router',\
                '-r',\
                envvar='HH_ROUTER',\
                default='tcp://0.0.0.0:10090',\
                show_default=True,\
                type=str)
@click.option('--log',\
                '-l',\
                envvar='HH_LOG',\
                default='INFO',\
                show_default=True,\
                type=click.Choice(['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']))
@click.option('--host',\
                '-H',\
                envvar='HH_HOST',\
                default='0.0.0.0',\
                show_default=True,\
                type=str)
@click.option('--port',\
                '-p',\
                envvar='HH_PORT',\
                default=10080,\
                show_default=True,\
                type=int)
def main(router, log, host, port):
    asyncio.run(_server(router, log, host, port))
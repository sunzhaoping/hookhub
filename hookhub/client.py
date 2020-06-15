import os
import asyncio
# setup uvloop for asyncio
#import uvloop
#asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
import zmq
import zmq.asyncio
import click
import logging
import signal
from aiohttp import web


async def run(cmd, payload):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate(payload)
    if stdout:
        logging.info(f'{stdout.decode()}')
    if stderr:
        logging.error(f'{stderr.decode()}')


async def scheduler(socket, queue):
    while True:
        try:
            [hook, payload] = await socket.recv_multipart()
            await queue.put(payload)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logging.error(str(e))


async def worker(script, queue):
    while True:
        try:
            payload = await queue.get()
            await run(script, payload)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logging.error(str(e))


async def _client(router, hook, script, log):
    # setup  logging 
    LOG_FORMAT = '[%(asctime)s] %(levelname)s %(message)s'
    numeric_level = getattr(logging, log.upper(), None)
    logging.basicConfig(format=LOG_FORMAT, level=numeric_level)

    loop = asyncio.get_running_loop()

    # start zmq client
    zmq_ctx = zmq.asyncio.Context.instance()
    socket = zmq_ctx.socket(zmq.SUB, io_loop=loop)
    socket.setsockopt(zmq.TCP_KEEPALIVE, 1)
    socket.setsockopt(zmq.TCP_KEEPALIVE_IDLE, 120)
    socket.setsockopt(zmq.TCP_KEEPALIVE_INTVL, 1) 
    socket.connect(router)
    socket.subscribe(hook.encode())

    queue = asyncio.Queue()
    logging.info(f"server start endpoint:[{router}] key:[{hook}]")
    scheduler_task = asyncio.create_task(scheduler(socket, queue))
    worker_task = asyncio.create_task(worker(script, queue))

    # watch close signal
    close_waiter = asyncio.Future()
    loop.add_signal_handler(signal.SIGTERM, close_waiter.set_result, None)
    loop.add_signal_handler(signal.SIGINT, close_waiter.set_result, None)
    await asyncio.shield(close_waiter)


@click.command()
@click.option('--router',\
                '-r',\
                envvar='HH_ROUTER',\
                type=str)
@click.option('--hook',\
                '-k',\
                envvar='HH_HOOK',\
                type=str)
@click.option('--log',\
                '-l',\
                envvar='HH_LOG',\
                default='INFO',\
                show_default=True,\
                type=click.Choice(['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']))
@click.argument('script')
def main(router, hook, script, log):
    asyncio.run(_client(router.strip(), hook.strip(), script, log))

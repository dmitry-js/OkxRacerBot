import os
import glob
import asyncio
import argparse
from itertools import cycle
from random import randint

from pyrogram import Client
from better_proxy import Proxy

from bot.config import settings
from bot.utils import logger
from bot.core.tapper import run_tapper
from bot.core.registrator import register_sessions


start_text = """

░█████╗░██╗░░██╗██╗░░██╗██████╗░░█████╗░████████╗
██╔══██╗██║░██╔╝╚██╗██╔╝██╔══██╗██╔══██╗╚══██╔══╝
██║░░██║█████═╝░░╚███╔╝░██████╦╝██║░░██║░░░██║░░░
██║░░██║██╔═██╗░░██╔██╗░██╔══██╗██║░░██║░░░██║░░░
╚█████╔╝██║░╚██╗██╔╝╚██╗██████╦╝╚█████╔╝░░░██║░░░
░╚════╝░╚═╝░░╚═╝╚═╝░░╚═╝╚═════╝░░╚════╝░░░░╚═╝░░░                                                                               
                                                                   
                                                                   
Select an action:

    1. Run clicker
    2. Create session
"""

global tg_clients

def get_session_names() -> list[str]:
    session_names = sorted(glob.glob("sessions/*.session"))
    session_names = [
        os.path.splitext(os.path.basename(file))[0] for file in session_names
    ]

    return session_names


def get_proxies() -> dict[str, Proxy]:
    proxies = {}

    if settings.USE_PROXY_FROM_FILE:
        with open(file="bot/config/proxies.txt", encoding="utf-8-sig") as file:
            for row in file:
                row = row.strip()
                if row:
                    session_name, proxy_str = row.split(':', 1)
                    session_name = session_name.strip()
                    proxy_str = proxy_str.strip()

                    proxy = Proxy.from_str(proxy=proxy_str).as_url
                    proxies[session_name] = proxy
    return proxies

async def get_tg_clients() -> list[Client]:
    global tg_clients

    session_names = get_session_names()

    if not session_names:
        raise FileNotFoundError("Not found session files")

    if not settings.API_ID or not settings.API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    tg_clients = [
        Client(
            name=session_name,
            api_id=settings.API_ID,
            api_hash=settings.API_HASH,
            workdir="sessions/",
            plugins=dict(root="bot/plugins"),
        )
        for session_name in session_names
    ]

    return tg_clients


async def process() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--action", type=int, help="Action to perform")

    logger.info(f"Detected {len(get_session_names())} sessions | {len(get_proxies())} proxies")

    action = parser.parse_args().action

    if not action:
        print(start_text)

        while True:
            action = input("> ")

            if not action.isdigit():
                logger.warning("Action must be number")
            elif action not in ["1", "2"]:
                logger.warning("Action must be 1 or 2")
            else:
                action = int(action)
                break

    if action == 2:
        await register_sessions()
    elif action == 1:
        tg_clients = await get_tg_clients()

        await run_tasks(tg_clients=tg_clients)


async def run_tasks(tg_clients: list[Client]):
    proxies = get_proxies()

    tasks = []
    for tg_client in tg_clients:
        tasks.append(asyncio.create_task(run_tapper(tg_client=tg_client, proxy=proxies.get(tg_client.name))))
        await asyncio.sleep(delay=randint(settings.START_DELAY[0], settings.START_DELAY[1]))

    await asyncio.gather(*tasks)

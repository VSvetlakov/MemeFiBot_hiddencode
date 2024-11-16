import typing
from urllib.parse import parse_qs
from better_proxy import Proxy

from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView
from pyrogram.errors import (
    Unauthorized,
    UserDeactivated,
    AuthKeyUnregistered,
    UserDeactivatedBan,
    AuthKeyDuplicated,
    SessionRevoked,
    SessionExpired
)

class TelegramInvalidSessionException(Exception):
    pass

class TelegramProxyError(Exception):
    pass

from bot.utils.logger import logger

_log = logger.opt(colors=True).bind(name=__name__)

def set_proxy_for_tg_client(client: Client, proxy: typing.Union[Proxy, typing.Text, None]):
    if proxy is None:
        return
    elif isinstance(proxy, str):
        proxy = Proxy.from_str(proxy)
    elif not isinstance(proxy, Proxy):
        raise ValueError("Proxy must be either a string or a Proxy")
    proxy_dict = dict(
        scheme=proxy.protocol,
        hostname=proxy.host,
        port=proxy.port,
        username=proxy.login,
        password=proxy.password
    )
    _log.trace(f"set proxy {proxy.protocol}-{proxy.login}@{proxy.host} to {client.name}")
    client.proxy = proxy_dict


async def get_tg_web_data(client: Client) -> dict:
    is_already_connected = client.is_connected
    try:
        if not client.is_connected:
            await client.connect()
        acc = await client.get_me()
        _log.trace(f"TG Account Login: {acc.username} ({acc.first_name}) {acc.last_name})")

        peer = await client.resolve_peer('memefi_coin_bot')
        web_view = await client.invoke(RequestWebView(
            peer=peer,
            bot=peer,
            platform='android',
            from_bot_menu=False,
            url="https://tg-app.memefi.club/game"
        ))
        return parse_qs(web_view.url)

    except (Unauthorized, UserDeactivated, AuthKeyUnregistered, UserDeactivatedBan, AuthKeyDuplicated,
            SessionExpired, SessionRevoked):
        raise TelegramInvalidSessionException(f"Telegram session is invalid. Client: {client.name}")
    except AttributeError as e:
        raise TelegramProxyError(e)
    finally:
        if not is_already_connected and client.is_connected:
            await client.disconnect()
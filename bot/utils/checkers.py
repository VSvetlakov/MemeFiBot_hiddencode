import typing
from asyncio import CancelledError

from aiohttp import ClientSession, ClientTimeout, ClientProxyConnectionError
from better_proxy import Proxy

from python_socks import ProxyTimeoutError, ProxyError

from bot.utils.connector import get_connector
from bot.utils.logger import logger

_log = logger.opt(colors=True).bind(name=__name__)


async def check_proxy(proxy: typing.Union[typing.Text, Proxy]) -> typing.Optional[typing.Text]:
    if isinstance(proxy, typing.Text):
        proxy = Proxy.from_str(proxy)
    elif not isinstance(proxy, Proxy):
        raise ValueError("proxy must be type of Proxy or str")
    async with ClientSession(connector=get_connector(proxy.as_url)) as session:
        try:
            response = await session.get(url='https://api.ipify.org?format=json', timeout=ClientTimeout(5))
            data = await response.json()
            if data and data.get('ip'):
                return data.get('ip')
        except (ConnectionRefusedError, ClientProxyConnectionError, CancelledError, TimeoutError, ProxyTimeoutError):
            _log.trace(f"Proxy not available")
        except ProxyError as e:
            _log.error(f"The proxy type may be incorrect! Error: {e}")
        except Exception as e:
            _log.opt(exception=e).error(f"Unknown error")

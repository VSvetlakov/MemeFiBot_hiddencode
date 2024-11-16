import asyncio
import random
import json

from aiocfscrape import CloudflareScraper
from loguru._logger import Logger
from pyrogram import Client

from bot.config import settings
from bot.config.config import USER_AGENTS_FILE
from bot.core.telegram import get_tg_web_data, set_proxy_for_tg_client
from bot.utils.checkers import check_proxy
from bot.core.headers import headers
from bot.core.agents import generate_random_user_agent

from bot.exceptions import InvalidSession, InvalidProtocol
from bot.core.memefi_api import MemeFiApi
from bot.utils.connector import get_connector
from bot.utils.logger import logger



class Tapper:

    _api: MemeFiApi
    _web_data: dict = None

    def __init__(self, tg_client: Client, session_logger: Logger):
        self.tg_client = tg_client
        self.log = session_logger
        self.session_ug_dict = self.load_user_agents() or []
        headers['User-Agent'] = self.check_user_agent()

    def save_user_agent(self):

        if not any(session['session_name'] == self.tg_client.name for session in self.session_ug_dict):
            user_agent_str = generate_random_user_agent()

            self.session_ug_dict.append({
                'session_name': self.tg_client.name,
                'user_agent': user_agent_str})

            with open(USER_AGENTS_FILE, 'w') as user_agents:
                json.dump(self.session_ug_dict, user_agents, indent=4)

            self.log.info("User agent saved successfully")

            return user_agent_str

    def load_user_agents(self):
        try:
            with open(USER_AGENTS_FILE, 'r') as user_agents:
                session_data = json.load(user_agents)
                if isinstance(session_data, list):
                    return session_data

        except FileNotFoundError:
            self.log.warning("User agents file not found, creating...")

        except json.JSONDecodeError:
            self.log.warning("User agents file is empty or corrupted.")

        return []

    def check_user_agent(self):
        load = next(
            (session['user_agent'] for session in self.session_ug_dict if session['session_name'] == self.tg_client.name),
            None)

        if load is None:
            return self.save_user_agent()

        return load

    async def delay_before_start(self):
        if settings.USE_RANDOM_DELAY_IN_RUN:
            random_delay = random.uniform(settings.RANDOM_DELAY_IN_RUN[0], settings.RANDOM_DELAY_IN_RUN[1])
            self.log.info(f"Bot will start in <y>{random_delay}s</y>")
            await asyncio.sleep(random_delay)


    async def roll_casino(self, spins: int):
        if not settings.ROLL_CASINO:
            return
        while spins > settings.VALUE_SPIN:
            await asyncio.sleep(delay=2)
            play_data = await self._api.play_slotmachine(spin_value=settings.VALUE_SPIN)
            reward_amount = play_data.get('spinResults', [{}])[0].get('rewardAmount', 0)
            reward_type = play_data.get('spinResults', [{}])[0].get('rewardType', 'NO')
            spins = play_data.get('gameConfig', {}).get('spinEnergyTotal', 0)
            balance = play_data.get('gameConfig', {}).get('coinsAmount', 0)
            if play_data.get('ethLotteryConfig', {}) is None:
                eth_lottery_status = '-'
                eth_lottery_ticket = '-'
            else:
                eth_lottery_status = play_data.get('ethLotteryConfig', {}).get('isCompleted', 0)
                eth_lottery_ticket = play_data.get('ethLotteryConfig', {}).get('ticketNumber', 0)
            self.log.info(f"🎰 Casino game | "
                          f"Balance: <lc>{balance:,}</lc> (<lg>+{reward_amount:,}</lg> "
                          f"<lm>{reward_type}</lm>) "
                          f"| Spins: <le>{spins:,}</le> ")
            if settings.LOTTERY_INFO:
                self.log.info(f"🎟 ETH Lottery status: {eth_lottery_status} |"
                              f" 🎫 Ticket number: <yellow>{eth_lottery_ticket}</yellow>")
            await asyncio.sleep(delay=5)


    async def set_new_boss_level(self, level):
        self.log.info(f"👉 Setting next boss: <m>{level}</m> lvl")
        self.log.info(f"😴 Sleep 10s")
        await asyncio.sleep(delay=10)

        status = await self._api.set_next_boss()
        if status is True:
            self.log.success(f"✅ Successful setting next boss: <m>{level}</m>")

    async def get_web_data(self):
        if not self._web_data:
            await self.load_web_data()
        return self._web_data

    async def load_web_data(self):
        self._web_data = await get_tg_web_data(self.tg_client)
        self.log.debug("Got")
        return self._web_data

    async def show_airdrop_checklist(self, airdrop_checklist: dict):
        if not airdrop_checklist:
            return self.log.warning("airdrop checklist was not received")
        def show_item(text: str, item: dict):
            status = "<g>Completed</g>" if item.get("done") else "<r>Uncompleted</r>"
            if item.get("currentAmount") and item.get("requiredAmount"):
                status = f'{status} ({item.get("currentAmount")}/{item.get("requiredAmount")})'
            return self.log.info(f'{text} -> {status}')
        if airdrop_checklist.get("coins"):
            show_item("Earn at least 50M Stars", airdrop_checklist.get("coins"))
        if airdrop_checklist.get("premium"):
            show_item("Upgrade to MemeFi Premium", airdrop_checklist.get("premium"))
        if airdrop_checklist.get("tonTransactions"):
            show_item("Complete 1+ on-chain transactions", airdrop_checklist.get("tonTransactions"))
        if airdrop_checklist.get("starTransactions"):
            show_item("Make at least 1 transaction in Telegram Stars", airdrop_checklist.get("starTransactions"))
        if airdrop_checklist.get("ethLotteryTickets"):
            show_item("Participate in at least 1 Daily Giveaway", airdrop_checklist.get("ethLotteryTickets"))
        if airdrop_checklist.get("campaigns"):
            show_item("Complete at least 10 Earn campaigns", airdrop_checklist.get("campaigns"))


    async def show_account_info(self, info):
        if not info:
            return self.log.warning("account info was not received")
        self.log.info(f'Use cheats -> {"<r>Detected</r>" if info.get("isCheatDetected") else "<g>Not Detected</g>"}')
        allocation = info.get("allocationNano")
        if allocation and allocation.isdigit():
            number_of_coins = round(int(allocation)/1e9, 2)
            self.log.info(f'Allocated airdrop -> {f"<g>{number_of_coins}</g>" if number_of_coins else number_of_coins} MEMEFI Coins')
        if info.get("okxSuiTask"):
            self.log.info(f'Sui Web3 wallet -> <g>{info.get("okxSuiTask", {}).get("okxSuiWallet")}</g>')

        pass




    async def run(self, proxy: str | None):

        if proxy:
            ip = await check_proxy(proxy)
            if not ip:
                return self.log.error("Proxy not available, skip session...")
            set_proxy_for_tg_client(self.tg_client, proxy)
            self.log.info(f"Proxy IP: {ip}")

        await self.delay_before_start()

        if not self._web_data:
            await self.load_web_data()


        async with CloudflareScraper(headers=headers, connector=get_connector(proxy)) as session:
            self._api = MemeFiApi(session=session)
            await self._api.auth_with_web_data(self._web_data)


            response = await self._api.airdrop_check()
            for result in response:
                data = result.get("data")
                airdrop_to_do = data.get("airdropTodoTasks", {})
                if airdrop_to_do:
                    await self.show_airdrop_checklist(airdrop_to_do)
                    continue
                claim_wallet = data.get("airdropOkxOffChainClaimWalletConfig", {})

                if claim_wallet and claim_wallet.get("wallet"):
                    wallet = claim_wallet.get("wallet")
                    okx_id = claim_wallet.get("okxId", "Not set")
                    self.log.info(f"Claim Airdrop Early via OKX. Wallet: </g>{wallet}</g>, OKX ID: {okx_id}")
                    continue
                me = data.get("telegramUserMe", {})
                if me:
                    await self.show_account_info(me)



async def run_tapper(tg_client: Client, proxy: str | None):
    session_logger = logger.opt(colors=True).bind(name=f"{tg_client.name}")
    try:
        await Tapper(tg_client=tg_client, session_logger=session_logger).run(proxy=proxy)
    except InvalidSession:
        session_logger.error(f"❗️Invalid Session")
    except InvalidProtocol as error:
        session_logger.opt(exception=error).error(f"❗️Invalid protocol detected at {error}")

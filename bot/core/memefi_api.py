from json import loads
from random import randint
from urllib.parse import parse_qs

from aiohttp import ClientSession, ContentTypeError

from bot.utils.logger import logger
from .graphql import Query, OperationName


_log = logger.opt(colors=True).bind(name=__package__)


class MemeFiApiError(Exception):
    pass


class MemeFiApi:
    _session: ClientSession
    _refresh_token: str | None

    _api_url = "https://api-gw-tg.memefi.club/graphql"
    _linea_url = "https://api.lineascan.build/"

    def __init__(self, session: ClientSession):
        self._session = session

    @staticmethod
    def error_wrapper(method):
        async def wrapper(self, *arg, **kwargs):
            try:
                return await method(self, *arg, **kwargs)
            except Exception as e:
                _log.opt(exception=e).error(f"Error on {type(self).__name__}.{method.__name__} | {type(e).__name__}: {e}")
        return wrapper

    async def _send_request(self, request_data: list | dict) -> dict | list:
        request = await self._session.post(url=self._api_url, json=request_data)
        request.raise_for_status()
        try:
            response = await request.json()
        except ContentTypeError as e:
            _log.opt(exception=e).error(f"API return unknown data type. status code: {request.status}")
            _log.error(f"API return data: {await request.text()}")
            raise MemeFiApiError
        if isinstance(response, dict):
            if response.get("errors"):
                raise MemeFiApiError(response.get("errors"))
            return response.get("data")
        if isinstance(response, list):
            for response_data in response:
                if response_data.get("errors"):
                    raise MemeFiApiError(response_data.get("errors"))
            return response
        raise ValueError("unknown data type")

    async def auth_with_web_data(self, web_data: dict):
        query = parse_qs(web_data.get("https://tg-app.memefi.club/game#tgWebAppData")[0])
        user_string = query.get("user", ['{}'])[0]
        user = loads(user_string)
        query_id = query.get("query_id")[0]
        hash_ = query.get("hash")[0]
        auth_date = query.get("auth_date")[0]

        json_data = {
            'operationName': OperationName.MutationTelegramUserLogin,
            'variables': {
                'webAppData': {
                    'auth_date': int(auth_date),
                    'hash': hash_,
                    'query_id': query_id,
                    'checkDataString': f'auth_date={auth_date}\nquery_id={query_id}\nuser={user_string}',
                    'user': {
                        'id': user.get("id"),
                        'allows_write_to_pm': True,
                        'first_name': user.get("first_name"),
                        'last_name': user.get("last_name"),
                        'username': user.get("username", ""),
                        'language_code': user.get("language_code", "en"),
                    },
                },
            },
            'query': Query.MutationTelegramUserLogin,
        }
        for _ in range(2):
            response_json = await self._send_request(json_data)

            if 'errors' in response_json:
                raise Exception(f'get_access_token msg: {response_json["errors"][0]["message"]}')

            access_token = response_json.get('telegramUserLogin', {}).get('access_token', '')
            self._session.headers["Authorization"] = f"Bearer {access_token}"

    @error_wrapper
    async def get_profile_data(self):
        json_data = {
            'operationName': OperationName.QUERY_GAME_CONFIG,
            'query': Query.QUERY_GAME_CONFIG,
            'variables': {}
        }
        response_json = await self._send_request(json_data)

        profile_data = response_json['telegramGameGetConfig']

        return profile_data

    @error_wrapper
    async def get_linea_walled_address(self):
        json_data = {
            'operationName': OperationName.TelegramMemefiWallet,
            'query': Query.TelegramMemefiWallet,
            'variables': {}
        }

        response_json = await self._send_request(json_data)
        response = response_json.get("telegramMemefiWallet", {}).get("walletAddress")
        return response

    @error_wrapper
    async def set_new_linea_wallet(self, address, signature) -> bool:
        json_data = {
            'operationName': OperationName.TelegramWalletLink,
            'query': Query.TelegramWalletLink,
            'variables': {
                "input": {
                    "signature": signature,
                    "walletAddress": address
                }
            }
        }
        response_json = await self._send_request(json_data)
        return response_json.get("telegramWalletLink") == True

    @error_wrapper
    async def get_sui_wallet_address(self):
        json_data = {
            'operationName': OperationName.OkxStatuses,
            'query': Query.OkxStatuses,
            'variables': {}
        }
        response = await self._send_request(json_data)
        return response.get("telegramUserMe", {}).get("okxSuiTask", {}).get("okxSuiWallet", {})


    @error_wrapper
    async def get_airdrop_to_do_task(self):
        json_data = {
            'operationName': OperationName.AirdropTodoTasks,
            'query': Query.AirdropTodoTasks,
            'variables': {}
        }
        response = await self._send_request(json_data)
        return response.get("airdropTodoTasks", {})




    @error_wrapper
    async def set_next_boss(self):
        json_data = {
            'operationName': OperationName.telegramGameSetNextBoss,
            'query': Query.telegramGameSetNextBoss,
            'variables': {}
        }
        return await self._send_request(json_data)

    async def get_telegram_me(self):
        json_data = {
            'operationName': OperationName.QueryTelegramUserMe,
            'query': Query.QueryTelegramUserMe,
            'variables': {}
        }
        response_json = await self._send_request(json_data)
        return response_json.get('telegramUserMe', {})

    async def airdrop_check(self):
        json_data = [
            {
                'operationName': OperationName.AirdropTodoTasks,
                'query': Query.AirdropTodoTasks,
                'variables': {}
            }, {
                'operationName': OperationName.AirdropOkxOffChainClaimWalletConfig,
                'query': Query.AirdropOkxOffChainClaimWalletConfig,
                'variables': {}
            }, {
                'operationName': OperationName.QueryTelegramUserMe,
                'query': Query.QueryTelegramUserMe,
                'variables': {}
            }
        ]
        response_json = await self._send_request(json_data)
        return response_json


    # async def apply_boost(self, boost_type: FreeBoostType):
    #     json_data = {
    #         'operationName': OperationName.telegramGameActivateBooster,
    #         'query': Query.telegramGameActivateBooster,
    #         'variables': {
    #             'boosterType': boost_type
    #         }
    #     }
    #     return await self._send_request(json_data)
    #
    # async def upgrade_boost(self, boost_type: UpgradableBoostType):
    #     json_data = {
    #         'operationName': OperationName.telegramGamePurchaseUpgrade,
    #         'query': Query.telegramGamePurchaseUpgrade,
    #         'variables': {
    #             'upgradeType': boost_type
    #         }
    #     }
    #     return await self._send_request(json_data)

    async def send_taps(self, nonce: str, taps: int):
        vector_array = []
        for tap in range(taps):
            """ check if tap is greater than 4 or less than 1 and set tap to random number between 1 and 4"""
            if tap > 4 or tap < 1:
                tap = randint(1, 4)
            vector_array.append(tap)
        vector = ",".join(str(x) for x in vector_array)
        json_data = {
            'operationName': OperationName.MutationGameProcessTapsBatch,
            'query': Query.MutationGameProcessTapsBatch,
            'variables': {
                'payload': {
                    'nonce': nonce,
                    'tapsCount': taps,
                    'vector': vector
                },
            }
        }
        return await self._send_request(json_data)


    async def get_campaigns(self):
        json_data = {
            'operationName': "CampaignLists",
            'query': Query.CampaignLists,
            'variables': {}
        }

        response_json = await self._send_request(json_data)
        campaigns = response_json.get('data', {}).get('campaignLists', {}).get('normal', [])
        return [campaign for campaign in campaigns if 'youtube' in campaign.get('description', '').lower()]

    async def verify_campaign(self, task_id: str):
        json_data = {
            'operationName': "CampaignTaskToVerification",
            'query': Query.CampaignTaskToVerification,
            'variables': {'taskConfigId': task_id}
        }

        response_json = await self._send_request(json_data)
        return response_json.get('data', {}).get('campaignTaskMoveToVerificationV2')


    async def complete_task(self, user_task_id: str, code: str = None):
        json_data = {
            'operationName': "CampaignTaskMarkAsCompleted",
            'query': Query.CampaignTaskMarkAsCompleted,
            'variables': {'userTaskId': user_task_id, 'verificationCode': str(code)} if code \
                else {'userTaskId': user_task_id}
        }

        response_json = await self._send_request(json_data)
        data = response_json.get('data') if isinstance(response_json.get('data'), dict) else {}
        if data.get('campaignTaskMarkAsCompleted', {}).get("status") == "Completed":
            return True
        raise Exception(f"unknown struct. status: {response_json}")

    async def get_tasks_list(self, campaigns_id: str):
        json_data = {
            'operationName': "GetTasksList",
            'query': Query.GetTasksList,
            'variables': {'campaignId': campaigns_id}
        }
        response_json = await self._send_request(json_data)
        return response_json.get('data', {}).get('campaignTasks', [])

    async def get_task_by_id(self, task_id: str):
        json_data = {
            'operationName': "GetTaskById",
            'query': Query.GetTaskById,
            'variables': {'taskId': task_id}
        }

        response_json = await self._send_request(json_data)
        return response_json.get('data', {}).get('campaignTaskGetConfig')

    async def get_clan(self):
        json_data = {
            'operationName': OperationName.ClanMy,
            'query': Query.ClanMy,
            'variables': {}
        }

        response_json = await self._send_request(json_data)

        data = response_json['data']['clanMy']
        if data and data['id']:
            return data['id']
        return False

    async def leave_clan(self):
        json_data = {
            'operationName': OperationName.Leave,
            'query': Query.Leave,
            'variables': {}
        }

        response_json = await self._send_request(json_data)

        if response_json['data']:
            if response_json['data']['clanActionLeaveClan']:
                return True

    async def join_clan(self):
        json_data = {
            'operationName': OperationName.Join,
            'query': Query.Join,
            'variables': {
                'clanId': '71886d3b-1186-452d-8ac6-dcc5081ab204'
            }
        }
        response = await self._send_request(json_data)
        response_json = await response.json()
        if response_json['data']:
            if response_json['data']['clanActionJoinClan']:
                return True


    async def start_bot(self):
        json_data = {
            'operationName': OperationName.TapbotStart,
            'query': Query.TapbotStart,
            'variables': {}
        }

        response = await self._send_request(json_data)
        return await response.json()

    async def get_bot_config(self):
        json_data = {
            'operationName': OperationName.TapbotConfig,
            'query': Query.TapbotConfig,
            'variables': {}
        }
        response_json = await self._send_request(json_data)
        return response_json['data']['telegramGameTapbotGetConfig']

    async def claim_bot(self):
        json_data = {
            'operationName': OperationName.TapbotClaim,
            'query': Query.TapbotClaim,
            'variables': {}
        }
        response_json = await self._send_request(json_data)

        return {"isClaimed": False, "data": response_json['data']["telegramGameTapbotClaim"]}

    async def claim_referral_bonus(self):
        json_data = {
            'operationName': OperationName.Mutation,
            'query': Query.Mutation,
            'variables': {}
        }
        response = await self._send_request(json_data)
        return await response.json()

    async def play_slotmachine(self, spin_value: int):
        json_data = {
            'operationName': OperationName.SpinSlotMachine,
            'query': Query.SpinSlotMachine,
            'variables': {
                'payload': {
                    'spinsCount': spin_value
                }
            }
        }
        response_json = await self._send_request(json_data)
        return response_json.get('data', {}).get('slotMachineSpinV2', {})
import typing

import jwt
from jwt import InvalidTokenError, ExpiredSignatureError

from extentions import cache_template
from schema.token_schema import TokenData
from schema.user_schemas import TokenRestrictionStrategyModeEnum
from settings import setting


class TokenSessionError(Exception):
    def __init__(self, trace_msg):
        super().__init__(trace_msg)
        self.message = trace_msg


class TokenRestrictionStrategyError(Exception):
    def __init__(self, trace_msg, strategy, force_offline_tokens=None):
        super().__init__(trace_msg)
        self.message = trace_msg
        if force_offline_tokens is None:
            self.force_offline_tokens = []
        else:
            self.force_offline_tokens = force_offline_tokens
        self.strategy = strategy

    def __str__(self):
        return f"TokenRestrictionStrategyError[RestrictionStrategyMode={setting.user_login_restriction_strategy_mode},"\
               f"Error: {self.message}],"


class TokenSession:
    USER_TOKENS_CACHE_PREFIX = "User:Tokens:"
    TOKEN_SESSION_CACHE_PREFIX = "User:TokenSession:"
    cache_template = cache_template

    def __init__(self, token):
        self.token = token
        self.token_data: typing.Optional[TokenData] = None

    @classmethod
    def get_instance(cls, token):
        try:
            payload = jwt.decode(token, setting.SECRET_KEY, algorithms=[setting.JWT_ENCODE_ALGORITHM])
            sub: str = payload.get("sub")
            _id: str = payload.get("id")
            adm: bool = payload.get("adm", False)
            if sub is None or _id is None:
                raise InvalidTokenError

            token_data = TokenData(sub=sub, id=_id, access_token=token, token_type="bearer", adm=adm)
            instance = cls(token)
            instance.token_data = token_data
            return instance
        except (InvalidTokenError, ExpiredSignatureError):
            token_data_dict = cls.cache_template.hget(cls.TOKEN_SESSION_CACHE_PREFIX + token, "token_data")
            if token_data_dict is not None:
                account: str = token_data_dict["account"]
                cls.cache_template.lrem(cls.USER_TOKENS_CACHE_PREFIX + account, token)
                cls.cache_template.delete(cls.TOKEN_SESSION_CACHE_PREFIX + token)
            raise

    @property
    def token_session_key(self):
        return self.TOKEN_SESSION_CACHE_PREFIX + self.token

    def validate(self):
        user_logged_tokens = self.cache_template.lall(self.USER_TOKENS_CACHE_PREFIX + self.token_data.account)
        user_logged_tokens = [i.decode() for i in user_logged_tokens]
        if self.token in user_logged_tokens and self.cache_template.has(self.token_session_key):
            return True
        token_data_dict = self.cache_template.hget(self.token_session_key, "token_data")
        if token_data_dict is not None:
            account: str = self.token_data.account
            self.cache_template.lrem(self.USER_TOKENS_CACHE_PREFIX + account, self.token)
        self.cache_template.delete(self.token_session_key)
        return False

    def create(self, expires):
        """
        This method will be called when user login and create a new token in the cache.
        At the same time, user login restriction strategy should be considered，
        if `settings.user_login_restriction_strategy` sets to 'False', There will be no limit to
        the number of people online at the same time for a single user. If the value sets to an integer greater than 0,
        Only the number of valid tokens for this value is allowed at the same time.
        :param expires: token's expiration time
        :return:
        """
        restriction_strategy = setting.user_login_restriction_strategy_enable
        if restriction_strategy:
            user_logged_tokens = self.cache_template.lall(self.USER_TOKENS_CACHE_PREFIX + self.token_data.account)
            user_logged_tokens = [i.decode() for i in user_logged_tokens]
            if setting.user_login_restriction_strategy_mode == TokenRestrictionStrategyModeEnum.FORCED_OFFLINE:
                r = 0
                force_offline_tokens = []
                for token in user_logged_tokens:
                    if self.cache_template.delete(self.TOKEN_SESSION_CACHE_PREFIX + token):
                        print(f"Account: {self.token_data.account}, Token: {token}已被强制禁用")
                        force_offline_tokens.append(token)
                        r += 1
                r += self.cache_template.delete(self.USER_TOKENS_CACHE_PREFIX + self.token_data.account)
                if len(user_logged_tokens) > 0 and r != len(user_logged_tokens) + 1:
                    raise TokenRestrictionStrategyError(
                        "[Mode: FORCED_OFFLINE]Token restriction strategy occur error, clear tokens error.",
                        strategy=TokenRestrictionStrategyModeEnum.FORCED_OFFLINE,
                        force_offline_tokens=force_offline_tokens
                    )
            if setting.user_login_restriction_strategy_mode == TokenRestrictionStrategyModeEnum.LIMIT_NUMBER_ONLINE:
                limit_number_online = setting.user_login_restriction_number_online
                for token in user_logged_tokens:
                    # 如果当前token已经失效的情况下, 清除用户名下在线的这个token，然后重新获取在线有效的token
                    if not self.cache_template.has(self.TOKEN_SESSION_CACHE_PREFIX + token):
                        self.cache_template.lrem(self.USER_TOKENS_CACHE_PREFIX + self.token_data.account, token)
                user_logged_tokens = self.cache_template.lall(self.USER_TOKENS_CACHE_PREFIX + self.token_data.account)
                if 0 < limit_number_online <= len(user_logged_tokens):
                    raise TokenRestrictionStrategyError(
                        "[Mode: LIMIT_NUMBER_ONLINE]Token restriction strategy occur error, "
                        "Exceeded maximum number of logged in users, current online tokens number: "
                        f"{len(user_logged_tokens)}",
                        strategy=TokenRestrictionStrategyModeEnum.LIMIT_NUMBER_ONLINE
                    )

        if not self.token_data:
            raise TokenSessionError("Token session instance has not been created")

        hset_data = {
            "access_token": self.token_data.access_token,
            "token_type": self.token_data.token_type,
            "account": self.token_data.account,
            "id": self.token_data.id,
            "adm": self.token_data.adm
        }
        if not self.cache_template.hset(self.token_session_key, "token_data", hset_data, expires):
            raise TokenSessionError("Set token data error")
        k = self.USER_TOKENS_CACHE_PREFIX + self.token_data.account
        if not self.cache_template.lpush(k, self.token_data.access_token) or not self.cache_template.expire(k, expires):
            self.cache_template.delete(self.token_session_key)
            raise TokenSessionError("Set token data error")
        return True

    def set(self, key, value):
        if self.cache_template.hset(self.token_session_key, key, value):
            return True
        return False

    def get(self, key):
        return self.cache_template.hget(self.token_session_key, key)

    def disable_token(self):
        user_logged_tokens = self.cache_template.lall(self.USER_TOKENS_CACHE_PREFIX + self.token_data.account)
        user_logged_tokens = [i.decode() for i in user_logged_tokens]
        if self.token in user_logged_tokens:
            if not self.cache_template.lrem(self.USER_TOKENS_CACHE_PREFIX + self.token_data.account, self.token):
                return False

        return self.cache_template.delete(self.token_session_key)

    def disable_login_user(self):
        r, _ = self.disable_user(self.token_data.account)
        return r

    @staticmethod
    def disable_user(user_account):
        user_logged_tokens = cache_template.lall(TokenSession.USER_TOKENS_CACHE_PREFIX + user_account)
        user_logged_tokens = [i.decode() for i in user_logged_tokens]
        r = 0
        r_ = 0
        for token in user_logged_tokens:
            if cache_template.delete(TokenSession.TOKEN_SESSION_CACHE_PREFIX + token):
                r += 1
                r_ += 1
        r += cache_template.delete(TokenSession.USER_TOKENS_CACHE_PREFIX + user_account)
        if len(user_logged_tokens) > 0 and r == len(user_logged_tokens) + 1:
            return True, r_
        return False, r_

    @staticmethod
    def get_user_tokens(account):
        user_logged_tokens = cache_template.lall(TokenSession.USER_TOKENS_CACHE_PREFIX + account)
        user_logged_tokens = [i.decode() for i in user_logged_tokens]
        return user_logged_tokens



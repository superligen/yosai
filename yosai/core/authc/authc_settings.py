from yosai.core import (
    maybe_resolve,
)

class AuthenticationSettings:
    """
    AuthenticationSettings is a settings proxy.  It is new for Yosai.
    It obtains the authc configuration from Yosai's global settings.
    """
    def __init__(self, settings):
        self.authc_config = settings.AUTHC_CONFIG
        self.algorithms = self.init_algorithms()

        self.preferred_algorithm = self.authc_config.get('preferred_algorithm')
        self.preferred_algorithm_context = self.algorithms.get(self.preferred_algorithm, {})

        self.account_lock_threshold = self.authc_config.get('account_lock_threshold')

        totp_settings = self.authc_config.get('totp')
        self.totp_context = totp_settings.get('context')

        self.mfa_challenger = maybe_resolve(self.authc_config.get('mfa_challenger'))

    def init_algorithms(self):
        algorithms = self.authc_config.get('hash_algorithms', None)
        if algorithms:
            return {alg: {"{0}__{1}".format(alg, key): value
                          for key, value in vals.items()}
                    for alg, vals in algorithms.items()}
        return None

    def get_config(self, algo):
        """
        obtains a dict of the underlying authc_config for an algorithm
        """
        if self.algorithms:
            return self.algorithms.get(algo, {})
        return {}

    def __repr__(self):
        return ("AuthenticationSettings(preferred_algorithm={0}, algorithms={1},"
                "authc_config={2}".format(self.preferred_algorithm,
                                          self.algorithms, self.authc_config))

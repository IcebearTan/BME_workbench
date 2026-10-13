"""Proposed training-platform adapter; these endpoints do NOT exist upstream yet.

No mode can turn central roles into workbench permissions. HTTP transport requires
an explicit dedicated client, HTTPS, PKCE and the contract in README.md.
"""
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit
import requests
from .errors import ApiError, unavailable
from .transport import lan_url


@dataclass(frozen=True)
class Identity:
    issuer: str
    subject: str
    person_id: str
    display_name: str
    security_version: str
    account_active: bool
    person_active: bool
    community_active: bool
    directory: dict | None = None

    @property
    def admitted(self):
        return self.account_active and self.person_active and self.community_active


class DisabledProvider:
    configured = False

    def authorize(self, **kwargs):
        raise unavailable()

    def exchange(self, **kwargs):
        raise unavailable()

    def inspect(self, **kwargs):
        raise unavailable()


class HttpIdentityProvider:
    configured = True

    def __init__(self, config):
        self.config = config
        names = ("IDENTITY_ISSUER", "IDENTITY_CLIENT_ID", "IDENTITY_CLIENT_SECRET",
                 "IDENTITY_AUTHORIZE_URL", "IDENTITY_EXCHANGE_URL", "IDENTITY_STATUS_URL")
        if not all(config.get(name) for name in names):
            raise ValueError("HTTP identity provider requires every dedicated client setting")
        for name in ("IDENTITY_AUTHORIZE_URL", "IDENTITY_EXCHANGE_URL", "IDENTITY_STATUS_URL"):
            parsed = urlsplit(config[name])
            allowed_lan = config.get('LAN_HTTP') and lan_url(config[name], loopback=name != 'IDENTITY_AUTHORIZE_URL')
            if ((parsed.scheme != "https" and not allowed_lan) or not parsed.netloc
                    or parsed.username or parsed.query or parsed.fragment):
                raise ValueError(f"{name} must be an HTTPS URL without credentials, query or fragment")

    def authorize(self, *, state, challenge, redirect_uri):
        return self.config["IDENTITY_AUTHORIZE_URL"] + "?" + urlencode({
            "client_id": self.config["IDENTITY_CLIENT_ID"], "response_type": "code",
            "redirect_uri": redirect_uri, "state": state, "code_challenge": challenge,
            "code_challenge_method": "S256", "scope": "workbench:access",
        })

    def _call(self, endpoint, payload):
        try:
            # Disable redirects so dedicated client credentials never follow a redirect.
            response = requests.post(self.config[endpoint], json=payload,
                auth=(self.config["IDENTITY_CLIENT_ID"], self.config["IDENTITY_CLIENT_SECRET"]),
                timeout=(3, 5), allow_redirects=False)
            # HTTP errors do not prove that the member lost admission. A missing
            # endpoint or bad client credential is an integration outage.
            if (endpoint == "IDENTITY_EXCHANGE_URL" and response.status_code == 400
                    and response.json() == {"error": "INVALID_CODE"}):
                raise ApiError("ADMISSION_DENIED", "登录票据无效，请重新登录", 403)
            if response.status_code != 200 or len(response.content) > 1024 * 1024:
                raise unavailable()
            data = response.json()
            if not isinstance(data, dict) or data.get("audience") != self.config["IDENTITY_CLIENT_ID"]:
                raise unavailable()
            strings = {key: data.get(key) for key in ("issuer", "subject", "person_id", "display_name", "security_version")}
            limits = {"issuer": 255, "subject": 128, "person_id": 128, "display_name": 100, "security_version": 64}
            if any(not isinstance(value, str) or not value or len(value) > limits[key]
                   or value != value.strip() for key, value in strings.items()):
                raise unavailable()
            if strings["issuer"] != self.config["IDENTITY_ISSUER"]:
                raise unavailable()
            flags = {key: data.get(key) for key in ("account_active", "person_active", "community_active")}
            if any(type(value) is not bool for value in flags.values()):
                raise unavailable()
            directory = data.get('directory')
            if directory is not None and not isinstance(directory, dict):
                raise unavailable()
            return Identity(**strings, **flags, directory=directory)
        except (requests.RequestException, ValueError, TypeError):
            raise unavailable() from None

    def exchange(self, *, code, verifier, redirect_uri):
        return self._call("IDENTITY_EXCHANGE_URL", {
            "grant_type": "authorization_code", "code": code, "code_verifier": verifier,
            "redirect_uri": redirect_uri, "audience": self.config["IDENTITY_CLIENT_ID"],
        })

    def inspect(self, *, issuer, subject):
        return self._call("IDENTITY_STATUS_URL", {"issuer": issuer, "subject": subject,
            "audience": self.config["IDENTITY_CLIENT_ID"]})

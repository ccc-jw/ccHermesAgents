import base64
import hashlib
import hmac


class FeishuSecurity:
    def __init__(self, app_secret: str):
        self.app_secret = app_secret

    def sign(self, timestamp: str, nonce: str, body: bytes) -> str:
        message = f"{timestamp}{nonce}".encode("utf-8") + body
        digest = hmac.new(self.app_secret.encode("utf-8"), message, hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")

    def verify(self, timestamp: str, nonce: str, body: bytes, signature: str) -> bool:
        expected = self.sign(timestamp=timestamp, nonce=nonce, body=body)
        return hmac.compare_digest(expected, signature)

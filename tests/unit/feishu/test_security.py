from app.feishu.security import FeishuSecurity


def test_feishu_security_rejects_wrong_signature():
    security = FeishuSecurity(app_secret="secret")
    assert security.verify(timestamp="1", nonce="n", body=b"{}", signature="bad") is False


def test_feishu_security_accepts_generated_signature():
    security = FeishuSecurity(app_secret="secret")
    signature = security.sign(timestamp="1", nonce="n", body=b"{}")
    assert security.verify(timestamp="1", nonce="n", body=b"{}", signature=signature) is True

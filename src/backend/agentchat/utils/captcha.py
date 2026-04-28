from agentchat.services.redis import redis_client

# async 异步函数，使用 await 等待异步操作完成。
# 做验证码的校验
async def verify_captcha(captcha: str, captcha_key: str):
    # check captcha
    captcha_value = redis_client.get(captcha_key)
    if captcha_value:
        redis_client.delete(captcha_key)
        return captcha_value.lower() == captcha.lower()
    else:
        return False

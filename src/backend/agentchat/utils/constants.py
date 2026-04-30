from typing import Any, Dict, List

# 用来记录 preset questions, dict: key 为作用对象的id
PRESET_QUESTION = 'preset_question'

# redis key
# 存储验证码，key为captcha_id
CAPTCHA_PREFIX = 'cap_'
# 存储RSA加密的密钥，key为rsa_key
RSA_KEY = 'rsa_'
# 存储用户的密码错误次数，key为username
USER_PASSWORD_ERROR = 'user_password_error:{}'
# 存储当前用户登录的cookie, key为用户id
USER_CURRENT_SESSION = 'user_current_session:{}'

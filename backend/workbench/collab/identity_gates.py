from flask import current_app


def verify_reject_reason(target, _operation):
    if target.lifecycle != 'active' or target.status != 'active':
        return '账号不可用'
    if current_app.config.get('VERIFY_APPOINTMENTS') and target.verification_status != 'verified':
        return '此操作要求目标成员完成身份核验'
    return None

class ApiError(Exception):
    def __init__(self, code, message, status):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


def unavailable():
    return ApiError("IDENTITY_PROVIDER_UNAVAILABLE", "训练营身份服务尚未接通或暂不可用，请稍后再试", 503)


def denied():
    return ApiError("ADMISSION_DENIED", "当前账号或人员不具备有效工作台准入资格", 403)

from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class RegisterRateThrottle(AnonRateThrottle):
    scope = "register"


class ForgotPasswordRateThrottle(AnonRateThrottle):
    scope = "forgot_password"

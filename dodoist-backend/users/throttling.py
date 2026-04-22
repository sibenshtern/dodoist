from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class RegisterRateThrottle(AnonRateThrottle):
    scope = "register"


class ForgotPasswordRateThrottle(AnonRateThrottle):
    scope = "forgot_password"


class ResetPasswordRateThrottle(AnonRateThrottle):
    scope = "reset_password"


class VerifyEmailRateThrottle(AnonRateThrottle):
    scope = "verify_email"


class ResendVerificationRateThrottle(UserRateThrottle):
    scope = "resend_verification"


class CommentWriteRateThrottle(UserRateThrottle):
    scope = "comment_write"


class ReactionWriteRateThrottle(UserRateThrottle):
    scope = "reaction_write"


class AttachmentUploadRateThrottle(UserRateThrottle):
    scope = "attachment_upload"

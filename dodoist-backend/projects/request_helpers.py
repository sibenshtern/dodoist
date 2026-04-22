def _active_ws(request):
    """
    Returns the active workspace for the request user.
    Falls back to the user's personal workspace if active_workspace is not set.
    """
    ws = getattr(request.user, "active_workspace", None)
    if ws is not None:
        return ws
    from .models import Workspace
    return Workspace.objects.filter(owner=request.user, is_personal=True).first()

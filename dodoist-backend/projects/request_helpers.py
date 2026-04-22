from projects.models import Workspace


def get_active_workspace(request) -> Workspace | None:
    """Return the authenticated user's active workspace, falling back to their personal workspace."""
    user = request.user
    ws = user.active_workspace
    if ws is not None:
        return ws
    return Workspace.objects.filter(owner=user, is_personal=True).first()

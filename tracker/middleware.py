from django.shortcuts import redirect


class RegularUserTimesheetOnlyMiddleware:
    """Non-admin users may only use the timesheet pages."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and not user.is_staff:
            path = request.path
            if not (
                path.startswith('/timesheets')
                or path.startswith('/logout')
                or path.startswith('/account/')
                or path.startswith('/static/')
                or path.startswith('/media/')
            ):
                return redirect('timesheets')
        return self.get_response(request)


class ForcePasswordChangeMiddleware:
    """Send users with temporary passwords to the change-password page."""

    ALLOWED_PREFIXES = (
        '/account/password/',
        '/logout',
        '/login',
        '/static/',
        '/media/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            profile = getattr(user, 'profile', None)
            if profile is None:
                from .models import UserProfile
                profile = UserProfile.for_user(user)
            if profile.must_change_password:
                path = request.path
                if not any(path.startswith(prefix) for prefix in self.ALLOWED_PREFIXES):
                    return redirect('change_password')
        return self.get_response(request)

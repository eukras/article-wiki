from lib.data import Data, load_env_config
from fastapi import HTTPException, Request, status


class Login:
    """
    FastApi Dependency Injector
    """

    def __init__(self, request: Request):
        """
        Return a logged-in user account, or trigger a 401.
        """
        data = Data(load_env_config())
        token = request.cookies.get("token", "")
        if token:
            user = data.login_get(token)
            self.username = user["username"] if user else None
            self.is_admin = user["is_admin"] if user else None
        else:
            self.username = None
            self.is_admin = None

    def __bool__(self):
        """
        Is there a login?
        """
        return self.username is not None

    def require(self):
        """
        Require a valid login, or raise HTTP_401_UNAUTHORIZED
        """
        if not bool(self):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required"
            )

    def require_admin(self):
        """
        Require a valid login and an admin login, or raise 403
        """
        self.require()
        if not self.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin login required"
            )

    def controls(self, user_slug: str):
        """
        Check the logged-in user has authority for the specified user.
        """
        return any(
            [
                self.username == user_slug,
                self.is_admin == 1,
            ]
        )

    def require_control(self, user_slug: str):
        """
        If no authority over user_slug, raise 403.
        """
        self.require()
        if not self.controls(user_slug):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for user '{user_slug}'",
            )

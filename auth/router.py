# auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from auth.models    import Token, User
from auth.security  import authenticate_user, create_access_token, get_current_user

router = APIRouter()


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Receives username + password.
    Returns JWT token if credentials are valid.

    Note: OAuth2PasswordRequestForm expects form data not JSON:
    Content-Type: application/x-www-form-urlencoded
    Swagger UI handles this automatically.
    """

    # AUTHENTICATION — verify identity
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Incorrect username or password",
            headers     = {"WWW-Authenticate": "Bearer"},
        )

    # create JWT with user info inside
    access_token = create_access_token(data={
        "sub":  user.username,   # subject — who this token is for
        "role": user.role,       # custom claim — their role
    })

    return Token(access_token=access_token)


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns info about the currently logged in user.
    Good for testing — confirms your token is working.
    """
    return {
        "username": current_user.username,
        "role":     current_user.role,
        "message":  "token is valid"
    }

<<<<<<< HEAD
import shutil

from fastapi import BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.routing import APIRouter
from mealie.core import security
from mealie.core.config import app_dirs, settings
from mealie.core.security import get_password_hash, verify_password
from mealie.db.database import db
from mealie.db.db_setup import generate_session
from mealie.routes.deps import get_current_user
from mealie.routes.routers import AdminAPIRouter, UserAPIRouter
from mealie.schema.user import ChangePassword, UserBase, UserFavorites, UserIn, UserInDB, UserOut
from mealie.services.events import create_user_event
from sqlalchemy.orm.session import Session

public_router = APIRouter(prefix="/api/users", tags=["Users"])
user_router = UserAPIRouter(prefix="/api/users", tags=["Users"])
admin_router = AdminAPIRouter(prefix="/api/users", tags=["Users"])


async def assert_user_change_allowed(
    id: int,
    current_user: UserInDB = Depends(get_current_user),
):
    if current_user.id != id and not current_user.admin:
        # only admins can edit other users
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="NOT_AN_ADMIN")


@admin_router.post("", response_model=UserOut, status_code=201)
async def create_user(
    background_tasks: BackgroundTasks,
    new_user: UserIn,
    current_user: UserInDB = Depends(get_current_user),
    session: Session = Depends(generate_session),
):

    new_user.password = get_password_hash(new_user.password)
    background_tasks.add_task(
        create_user_event, "User Created", f"Created by {current_user.full_name}", session=session
    )
    return db.users.create(session, new_user.dict())


@admin_router.get("", response_model=list[UserOut])
async def get_all_users(session: Session = Depends(generate_session)):
    return db.users.get_all(session)


@user_router.get("/self", response_model=UserOut)
async def get_logged_in_user(
    current_user: UserInDB = Depends(get_current_user),
):
    return current_user.dict()


@admin_router.get("/{id}", response_model=UserOut)
async def get_user_by_id(
    id: int,
    session: Session = Depends(generate_session),
):
    return db.users.get(session, id)


@user_router.put("/{id}/reset-password")
async def reset_user_password(
    id: int,
    session: Session = Depends(generate_session),
):

    new_password = get_password_hash(settings.DEFAULT_PASSWORD)
    db.users.update_password(session, id, new_password)


@user_router.put("/{id}")
async def update_user(
    id: int,
    new_data: UserBase,
    current_user: UserInDB = Depends(get_current_user),
    session: Session = Depends(generate_session),
):

    assert_user_change_allowed(id)

    if not current_user.admin and (new_data.admin or current_user.group != new_data.group):
        # prevent a regular user from doing admin tasks on themself
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    if current_user.id == id and current_user.admin and not new_data.admin:
        # prevent an admin from demoting themself
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    db.users.update(session, id, new_data.dict())
    if current_user.id == id:
        access_token = security.create_access_token(data=dict(sub=new_data.email))
        token = {"access_token": access_token, "token_type": "bearer"}
        return token


@public_router.get("/{id}/image")
async def get_user_image(id: str):
    """ Returns a users profile picture """
    user_dir = app_dirs.USER_DIR.joinpath(id)
    for recipe_image in user_dir.glob("profile_image.*"):
        return FileResponse(recipe_image)

    raise HTTPException(status.HTTP_404_NOT_FOUND)


@user_router.post("/{id}/image")
async def update_user_image(
    id: str,
    profile_image: UploadFile = File(...),
):
    """ Updates a User Image """

    assert_user_change_allowed(id)

    extension = profile_image.filename.split(".")[-1]

    app_dirs.USER_DIR.joinpath(id).mkdir(parents=True, exist_ok=True)

    [x.unlink() for x in app_dirs.USER_DIR.joinpath(id).glob("profile_image.*")]

    dest = app_dirs.USER_DIR.joinpath(id, f"profile_image.{extension}")

    with dest.open("wb") as buffer:
        shutil.copyfileobj(profile_image.file, buffer)

    if not dest.is_file:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR)


@user_router.put("/{id}/password")
async def update_password(
    id: int,
    password_change: ChangePassword,
    current_user: UserInDB = Depends(get_current_user),
    session: Session = Depends(generate_session),
):
    """ Resets the User Password"""

    assert_user_change_allowed(id)
    match_passwords = verify_password(password_change.current_password, current_user.password)

    if not (match_passwords):
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    new_password = get_password_hash(password_change.new_password)
    db.users.update_password(session, id, new_password)


@user_router.get("/{id}/favorites", response_model=UserFavorites)
async def get_favorites(id: str, session: Session = Depends(generate_session)):
    """ Get user's favorite recipes """

    return db.users.get(session, id, override_schema=UserFavorites)


@user_router.post("/{id}/favorites/{slug}")
async def add_favorite(
    slug: str,
    current_user: UserInDB = Depends(get_current_user),
    session: Session = Depends(generate_session),
):
    """ Adds a Recipe to the users favorites """

    assert_user_change_allowed(id)
    current_user.favorite_recipes.append(slug)

    db.users.update(session, current_user.id, current_user)

    db.users.update(session, current_user.id, current_user)

@user_router.delete("/{id}/favorites/{slug}")
async def remove_favorite(
    slug: str,
    current_user: UserInDB = Depends(get_current_user),
    session: Session = Depends(generate_session),
):
    """ Adds a Recipe to the users favorites """

    assert_user_change_allowed(id)
    current_user.favorite_recipes = [x for x in current_user.favorite_recipes if x != slug]

    db.users.update(session, current_user.id, current_user)

    return


@admin_router.delete("/{id}")
async def delete_user(
    background_tasks: BackgroundTasks,
    id: int,
    session: Session = Depends(generate_session),
):
    """ Removes a user from the database. Must be the current user or a super user"""

    assert_user_change_allowed(id)

    if id == 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SUPER_USER")

    try:
        db.users.delete(session, id)
        background_tasks.add_task(create_user_event, "User Deleted", f"User ID: {id}", session=session)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
=======
from fastapi import HTTPException, status
from pydantic import UUID4

from mealie.core.security import hash_password, verify_password
from mealie.routes._base import BaseAdminController, controller
from mealie.routes._base.base_controllers import BaseUserController
from mealie.routes._base.mixins import HttpRepo
from mealie.routes._base.routers import AdminAPIRouter, UserAPIRouter
from mealie.routes.users._helpers import assert_user_change_allowed
from mealie.schema.response import ErrorResponse, SuccessResponse
from mealie.schema.user import ChangePassword, UserBase, UserIn, UserOut

user_router = UserAPIRouter(prefix="/users", tags=["Users: CRUD"])
admin_router = AdminAPIRouter(prefix="/users", tags=["Users: Admin CRUD"])


@controller(admin_router)
class AdminUserController(BaseAdminController):
    @property
    def mixins(self) -> HttpRepo:
        return HttpRepo[UserIn, UserOut, UserBase](self.repos.users, self.deps.logger)

    @admin_router.get("", response_model=list[UserOut])
    def get_all_users(self):
        return self.repos.users.get_all()

    @admin_router.post("", response_model=UserOut, status_code=201)
    def create_user(self, new_user: UserIn):
        new_user.password = hash_password(new_user.password)
        return self.mixins.create_one(new_user)

    @admin_router.get("/{item_id}", response_model=UserOut)
    def get_user(self, item_id: UUID4):
        return self.mixins.get_one(item_id)

    @admin_router.delete("/{item_id}")
    def delete_user(self, item_id: UUID4):
        """Removes a user from the database. Must be the current user or a super user"""

        assert_user_change_allowed(item_id, self.user)

        if item_id == 1:  # TODO: identify super_user
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SUPER_USER")

        self.mixins.delete_one(item_id)


@controller(user_router)
class UserController(BaseUserController):
    @user_router.get("/self", response_model=UserOut)
    def get_logged_in_user(self):
        return self.user

    @user_router.put("/{item_id}")
    def update_user(self, item_id: UUID4, new_data: UserBase):
        assert_user_change_allowed(item_id, self.user)

        if not self.user.admin and (new_data.admin or self.user.group != new_data.group):
            # prevent a regular user from doing admin tasks on themself
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, ErrorResponse.respond("User doesn't have permission to change group")
            )

        if self.user.id == item_id and self.user.admin and not new_data.admin:
            # prevent an admin from demoting themself
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, ErrorResponse.respond("User doesn't have permission to change group")
            )

        try:
            self.repos.users.update(item_id, new_data.dict())
        except Exception as e:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                ErrorResponse.respond("Failed to update user"),
            ) from e

        return SuccessResponse.respond("User updated")

    @user_router.put("/{item_id}/password")
    def update_password(self, password_change: ChangePassword):
        """Resets the User Password"""
        if not verify_password(password_change.current_password, self.user.password):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, ErrorResponse.respond("Invalid current password"))

        self.user.password = hash_password(password_change.new_password)
        try:
            self.repos.users.update_password(self.user.id, self.user.password)
        except Exception as e:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                ErrorResponse.respond("Failed to update password"),
            ) from e

        return SuccessResponse.respond("Password updated")
>>>>>>> v1.0.0-beta-1

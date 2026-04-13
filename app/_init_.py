from .auth import auth_router
main_router.include_router(auth_router)
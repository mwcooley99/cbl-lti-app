from flask import Blueprint

blueprint = Blueprint(
    "account", __name__, url_prefix="/account", static_folder="../static"
)
from app.account import views, admin
 
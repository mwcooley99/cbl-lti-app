from flask import render_template, Response, current_app, Blueprint
from pylti.flask import lti

blueprint = Blueprint("public", __name__, static_folder="../static")


def return_error(msg):
    return render_template("error.html", msg=msg)


def error(exception=None):
    current_app.logger.error("PyLTI error: {}".format(exception))
    return return_error(
        """Authentication error,
        please refresh and try again. If this error persists,
        please contact support."""
    )


# Home page
@blueprint.route("/", methods=["GET"])
# @lti(error=error, request='any', app=current_app)
def index(lti=lti):
    return render_template("public/index.html")


# LTI XML Configuration
@blueprint.route("/xml/", methods=["GET"])
def xml():
    """
    Returns the lti.xml file for the app.
    XML can be built at https://www.eduappcenter.com/
    """
    try:
        return Response(
            render_template("public/lti.xml.j2"), mimetype="application/xml"
        )
    except Exception as ex:
        print(ex)
        current_app.logger.error("Error with XML.")
        return return_error(
            """Error with XML. Please refresh and try again. If this error persists,
            please contact support."""
        )

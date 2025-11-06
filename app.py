from flask import Flask, render_template
from flask_cors import CORS
from flasgger import Swagger
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from blueprints.auth.auth import auth_bp
from blueprints.patients.patients import patients_bp
from blueprints.appointments.appointments import appointments_bp
from blueprints.prescriptions.prescriptions import prescriptions_bp
from blueprints.careplans.careplans import careplans_bp
from blueprints.analytics.analytics import analytics_bp
from utils import response

# app setup
app = Flask(__name__)
CORS(app)
Swagger(app)
limiter = Limiter(app=app, key_func=get_remote_address)

# register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(patients_bp)
app.register_blueprint(appointments_bp)
app.register_blueprint(prescriptions_bp)
app.register_blueprint(careplans_bp)
app.register_blueprint(analytics_bp)

# get index
@app.route("/")
def index():
    return render_template("index1.html")

# get health check
@app.route("/health", methods=["GET"])
def health_check():
    return response(True, message="API running and healthy", data={"service": "Multimedia GP Portal"})

# error handler
@app.errorhandler(Exception)
def handle_exception(e):
    print(f"[ERROR] {type(e).__name__}: {e}") 
    return response(False, message=str(e), status=500)

# main entry point
if __name__ == "__main__":
    app.run(debug=True)

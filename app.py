# ----------------------------------------------------------
# COM682 Coursework 1 – Multimedia GP Portal
# Modular Flask App using Blueprints
# Author: Paul Johnston (B00888517)
# ----------------------------------------------------------

from flask import Flask, render_template
from flask_cors import CORS
from flasgger import Swagger
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import Blueprints
from blueprints.auth.auth import auth_bp
from blueprints.patients.patients import patients_bp
from blueprints.appointments.appointments import appointments_bp
from blueprints.prescriptions.prescriptions import prescriptions_bp
from blueprints.careplans.careplans import careplans_bp
from blueprints.analytics.analytics import analytics_bp

# ----------------------------------------------------------
# App Setup
# ----------------------------------------------------------
app = Flask(__name__)
CORS(app)
Swagger(app)
limiter = Limiter(app=app, key_func=get_remote_address)

# ----------------------------------------------------------
# Register Blueprints
# ----------------------------------------------------------
app.register_blueprint(auth_bp)
app.register_blueprint(patients_bp)
app.register_blueprint(appointments_bp)
app.register_blueprint(prescriptions_bp)
app.register_blueprint(careplans_bp)
app.register_blueprint(analytics_bp)

# ----------------------------------------------------------
# Frontend route
# ----------------------------------------------------------
@app.route('/')
def index():
    return render_template('index1.html')

# ----------------------------------------------------------
# Run App
# ----------------------------------------------------------
if __name__ == "__main__":
    print("Multimedia GP Portal running with Flask Blueprints")
    app.run(debug=True)

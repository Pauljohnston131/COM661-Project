# COM661 CW1 Synthea - Healthcare Management Portal

A modular Flask-based web application for managing healthcare data, integrating synthetic patient data from Synthea. This portal provides a comprehensive system for patient management, appointments, prescriptions, care plans, and analytics with JWT-based authentication.

## Features

- **Patient Management**: CRUD operations for patient records with search and pagination
- **Appointment Scheduling**: Manage patient appointments with doctors
- **Prescription Tracking**: Handle medication prescriptions with status tracking
- **Care Plan Management**: Create and manage patient care plans
- **Analytics Dashboard**: Search patients and view statistics on appointments, prescriptions, and care plans
- **Authentication System**: JWT-based login/logout with admin and user roles
- **Rate Limiting**: Built-in request rate limiting for API protection
- **API Documentation**: Swagger UI for interactive API exploration
- **Data Seeding**: Automated loading of Synthea CSV data into MongoDB

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: MongoDB
- **Authentication**: JWT (JSON Web Tokens)
- **Security**: Flask-Bcrypt for password hashing
- **API Documentation**: Flasgger (Swagger)
- **Rate Limiting**: Flask-Limiter
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Data Source**: Synthea (synthetic healthcare data)

## Prerequisites

- Python 3.8+
- MongoDB 4.0+
- Git

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd COM661-CW1-Synthea
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start MongoDB:**
   Ensure MongoDB is running on `mongodb://127.0.0.1:27017`

## Setup

1. **Seed the database with Synthea data:**
   ```bash
   python seed_synthea_data.py
   ```

2. **Create default admin user:**
   ```bash
   python seed_users_synthea.py
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Access the application:**
   - Frontend: http://localhost:5000
   - API Documentation: http://localhost:5000/apidocs

## Usage

### Default Credentials
- **Username:** admin
- **Password:** admin123

### API Endpoints

#### Authentication
- `POST /api/v1.0/auth/login` - User login
- `GET /api/v1.0/auth/logout` - User logout
- `GET /api/v1.0/auth/verify` - Verify token

#### Patients
- `GET /api/v1.0/patients/` - List patients (paginated)
- `POST /api/v1.0/patients/` - Add new patient
- `GET /api/v1.0/patients/<id>` - Get patient details
- `PUT /api/v1.0/patients/<id>` - Update patient
- `DELETE /api/v1.0/patients/<id>` - Delete patient (admin only)

#### Appointments
- `POST /api/v1.0/appointments/<patient_id>` - Add appointment (admin only)
- `GET /api/v1.0/appointments/<patient_id>/<appointment_id>` - Get appointment
- `PUT /api/v1.0/appointments/<patient_id>/<appointment_id>` - Update appointment (admin only)
- `DELETE /api/v1.0/appointments/<patient_id>/<appointment_id>` - Delete appointment (admin only)

#### Prescriptions
- `GET /api/v1.0/prescriptions/<patient_id>` - List prescriptions
- `POST /api/v1.0/prescriptions/<patient_id>` - Add prescription
- `PUT /api/v1.0/prescriptions/<patient_id>/<prescription_id>` - Update prescription (admin only)
- `DELETE /api/v1.0/prescriptions/<patient_id>/<prescription_id>` - Delete prescription (admin only)

#### Care Plans
- `GET /api/v1.0/careplans/<patient_id>` - List care plans
- `POST /api/v1.0/careplans/<patient_id>` - Add care plan
- `PUT /api/v1.0/careplans/<patient_id>/<careplan_id>` - Update care plan (admin only)
- `DELETE /api/v1.0/careplans/<patient_id>/<careplan_id>` - Delete care plan (admin only)

#### Analytics
- `GET /api/v1.0/analytics/search?q=<query>` - Search patients
- `GET /api/v1.0/analytics/stats/appointments` - Appointment statistics
- `GET /api/v1.0/analytics/stats/prescriptions` - Prescription statistics
- `GET /api/v1.0/analytics/stats/careplans` - Care plan statistics

### Authentication Headers
Include the JWT token in requests:
```
Authorization: Bearer <your-jwt-token>
```

## Database Schema

### Patients Collection
```json
{
  "_id": "ObjectId",
  "name": "string",
  "age": "number",
  "gender": "string",
  "condition": "string",
  "image_url": "string",
  "appointments": [
    {
      "_id": "ObjectId",
      "doctor": "string",
      "date": "string",
      "notes": "string",
      "status": "string"
    }
  ],
  "prescriptions": [
    {
      "_id": "ObjectId",
      "name": "string",
      "start": "string",
      "stop": "string",
      "status": "string"
    }
  ],
  "careplans": [
    {
      "_id": "ObjectId",
      "description": "string",
      "start": "string",
      "stop": "string"
    }
  ]
}
```

### Users Collection
```json
{
  "_id": "ObjectId",
  "username": "string",
  "password": "string (hashed)",
  "admin": "boolean"
}
```

## Project Structure

```
COM661-CW1-Synthea/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── globals.py                  # Global database connection
├── decorators.py               # JWT and admin decorators
├── blueprints/
│   ├── auth/
│   │   └── auth.py            # Authentication endpoints
│   ├── patients/
│   │   └── patients.py        # Patient management
│   ├── appointments/
│   │   └── appointments.py    # Appointment management
│   ├── prescriptions/
│   │   └── prescriptions.py   # Prescription management
│   ├── careplans/
│   │   └── careplans.py       # Care plan management
│   └── analytics/
│       └── analytics.py       # Analytics and search
├── templates/
│   └── index1.html            # Frontend HTML
├── static/
│   ├── styles1.css            # Frontend styles
│   └── script.js              # Frontend JavaScript
├── data/
│   └── synthea_csv/           # Synthea CSV data files
├── seed_synthea_data.py       # Data seeding script
├── seed_users_synthea.py      # User seeding script
└── README.md                  # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Synthea](https://github.com/synthetichealth/synthea) - Synthetic patient data generator
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [MongoDB](https://www.mongodb.com/) - NoSQL database

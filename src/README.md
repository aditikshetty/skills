# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teacher-only student registration and unregistration
- Public activity and participant viewing
- Teacher sessions protected by signed, HTTP-only cookies

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   export TEACHER_AUTH_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
   python scripts/add_teacher.py
   uvicorn src.app:app --reload
   ```

   The setup helper asks for a teacher username and password, then stores a
   salted password hash in `src/teachers.json`. That local credentials file is
   ignored by Git. Keep `TEACHER_AUTH_SECRET` private and use HTTPS when
   deploying the app. The secret must be at least 32 characters. If using a
   custom credentials file, set `TEACHERS_FILE` to its path.

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| GET    | `/auth/me`                                                        | Check whether the current browser session is a teacher session       |
| POST   | `/auth/login`                                                     | Log in with a configured teacher username and password               |
| POST   | `/auth/logout`                                                    | Clear the current teacher session                                    |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher-only student registration                                    |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher-only student unregistration                                |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity and registration data are stored in memory and reset when the server
restarts. Teacher account password hashes are stored in the local
`src/teachers.json` file.

# Timeshit

A self-contained Django time-tracking app with local SQLite storage and a built-in frontend.

## Features

- **Local database** — SQLite stored in `data/timeshit.db` (created automatically)
- **Media storage** — uploads go to `data/media/`
- **Frontend** — Django templates with a dark-themed dashboard
- **Time tracking** — create projects, log hours, view recent entries

## Quick start

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run migrations (first time only)
python manage.py migrate

# Start the development server
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

## Project structure

```
Timeshit Project/
├── data/              # Local storage (database + media)
│   ├── timeshit.db
│   └── media/
├── static/css/        # Frontend styles
├── templates/         # HTML templates
├── tracker/           # Main Django app
├── timeshit/          # Project settings
├── manage.py
└── requirements.txt
```

## Admin

Create a superuser to access the Django admin at `/admin/`:

```powershell
python manage.py createsuperuser
```

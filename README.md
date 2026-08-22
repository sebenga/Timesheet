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

## Hosting

The app deploys from the GitHub `main` branch on [Render](https://render.com/) (free web service + free Postgres, HTTPS included). Pushes to `main` trigger a new deploy.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/sebenga/Timesheet)

1. Open the button above (or [this deploy link](https://render.com/deploy?repo=https://github.com/sebenga/Timesheet)).
2. Sign in to Render with the GitHub account that owns [sebenga/Timesheet](https://github.com/sebenga/Timesheet).
3. Apply the Blueprint (`render.yaml`) on the **free** plan.

The live URL is `https://<service-name>.onrender.com`. Free web services sleep after idle time and take about a minute to wake. Free Postgres on Render expires after 30 days unless upgraded.

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

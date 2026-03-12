# Volunteer Matching App (Single Project)

This project now uses a single app entrypoint: `app.py`.
It includes:
- student + NGO UI
- registration/login
- recommendations
- calendar slot viewing
- booking flow and booking history

## Main Files
- `app.py`
- `students.csv`
- `opportunities.csv`
- `interactions.csv`
- `time_slots.csv`
- `bookings.csv`
- `requirements.txt`
- `start.bat`

## Run
```bash
pip install -r requirements.txt
python app.py
```
Open: `http://localhost:5000`

## Notes
- LightFM is optional in `app.py`. If not installed, fallback recommendation logic is used.
# Gig Gazette API

The REST API backend for [Gig Gazette](https://github.com/jackgardner99/Gig-Gazette), a platform for discovering and managing live music events in Nashville.

Built with Django REST Framework, PostgreSQL, and deployed on Railway.

## Tech Stack

- **Framework:** Django REST Framework
- **Database:** PostgreSQL
- **Image Storage:** Cloudinary
- **Geocoding:** Mapbox
- **Authentication:** Token-based (DRF TokenAuthentication)
- **Deployment:** Railway

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL

### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Start the server
python manage.py runserver
```

The server runs on `http://localhost:8000` by default.

### Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Set to `True` for local development |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts |
| `DATABASE_URL` | PostgreSQL connection string |
| `CORS_ORIGIN_WHITELIST` | Comma-separated list of allowed frontend origins |
| `MAPBOX_ACCESS_TOKEN` | Mapbox API token for geocoding |
| `CLOUDINARY_URL` | Cloudinary connection string for image storage |

## API Endpoints

All endpoints are prefixed with the base URL. Authentication is required for write operations — include a token in the `Authorization: Token <token>` header.

### Auth

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/register` | Create a new user account |
| `POST` | `/login` | Authenticate and receive a token |

### Venues

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/venues` | List all venues |
| `GET` | `/venues/{id}` | Retrieve a venue |
| `POST` | `/venues` | Create a venue (geocodes address automatically) |
| `PUT` | `/venues/{id}` | Update a venue |
| `DELETE` | `/venues/{id}` | Delete a venue |

### Shows

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/shows` | List all shows (filter by `?userId=`) |
| `GET` | `/shows/{id}` | Retrieve a show |
| `POST` | `/shows` | Create a show |
| `PUT` | `/shows/{id}` | Update a show |
| `DELETE` | `/shows/{id}` | Delete a show |

### Open Mics

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/open_mics` | List all open mics |
| `GET` | `/open_mics/{id}` | Retrieve an open mic |
| `POST` | `/open_mics` | Create an open mic |
| `PUT` | `/open_mics/{id}` | Update an open mic |
| `DELETE` | `/open_mics/{id}` | Delete an open mic |

### Writers Rounds

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/writers_rounds` | List all writers rounds |
| `GET` | `/writers_rounds/{id}` | Retrieve a writers round |
| `POST` | `/writers_rounds` | Create a writers round |
| `PUT` | `/writers_rounds/{id}` | Update a writers round |
| `DELETE` | `/writers_rounds/{id}` | Delete a writers round |

### Artists

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/artists` | List all artists |
| `GET` | `/artists/{id}` | Retrieve an artist |

### Genres

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/genres` | List all genres |

### User Photos

Photos are scoped to their parent event and owned by the uploading user. Only the owner can delete their photo.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/show_photos` | List show photos (filter by `?show_id=`) |
| `POST` | `/show_photos` | Upload a photo for a show |
| `DELETE` | `/show_photos/{id}` | Delete a show photo |
| `GET` | `/open_mic_photos` | List open mic photos (filter by `?open_mic_id=`) |
| `POST` | `/open_mic_photos` | Upload a photo for an open mic |
| `DELETE` | `/open_mic_photos/{id}` | Delete an open mic photo |
| `GET` | `/writers_round_photos` | List writers round photos (filter by `?writers_round_id=`) |
| `POST` | `/writers_round_photos` | Upload a photo for a writers round |
| `DELETE` | `/writers_round_photos/{id}` | Delete a writers round photo |

## Related

- [Gig Gazette](https://github.com/jackgardner99/Gig-Gazette) — the frontend application

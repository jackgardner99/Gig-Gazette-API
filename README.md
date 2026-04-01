# Gig Gazette API

This is the back-end API for [Gig Gazette](https://github.com/jackgardner99/Gig-Gazette), a client-side application for managing and discovering live music gigs and open mic events.

## Overview

The API is powered by [json-server] and serves data from `database.json`. It provides RESTful endpoints for all resources used by the Gig Gazette client.

## Resources

| Resource | Description |
|---|---|
| `artists` | Musicians and bands, associated with a manager and genre |
| `venues` | Nashville-area venues with geolocation data |
| `genres` | Music genre classifications |
| `managers` | User accounts that manage artists and events |
| `artistShows` | Scheduled performances at venues |
| `openMics` | Recurring or one-time open mic events at venues |

## Getting Started

### Prerequisites

- Node.js

### Running the API

```bash
json-server -w database.json
```

The server will run on `http://localhost:3000` by default (check `package.json` for the configured port).

## Related

- [Gig Gazette](https://github.com/jackgardner99/Gig-Gazette) — the client-side application that consumes this API

# Thai 2D Stock Snapshot API

This FastAPI project fetches Thai 2D stock data from `https://api.thaistock2d.com/live` at **12:01 PM** and **16:30 PM** Myanmar time, saves it to SQLite, and provides REST API access.

## Endpoints

- `/records` : Returns all recorded snapshots.
- `/latest`  : Returns the latest snapshot.

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload

# 🛠 My Contributions — Storm Tracking and Analytics Platform

This folder contains the parts of the project that I personally implemented for the Storm Tracking and Analytics Platform.

This was a team-based project. For the full runnable platform, see the `storm_project` folder.

## 📂 Folder Structure
```
my_contributions/
├── sql/                # SQL scripts I wrote to populate the frontend database
├── frontend/           # Dash components and scripts I built
└── README.md           # This file
```

## 🗃 SQL Scripts (sql/)

These scripts were used to:

* Create tables in the frontend database

* Populate tables with meteorological data

* Ensure data is queryable efficiently by the frontend cache

Key points:

* Designed for large-scale data (~36,000 rows)

* Optimised queries for quick frontend response

* Fully compatible with SQLAlchemy abstraction layer in the main project

## 🖥 Frontend Components (frontend/)

This folder contains my contributions to the Dash-based frontend, including:

* Interactive tables with pagination and caching for performance

* Dash layout and components for storm maps, wind vectors, and atmospheric overlays

* Utility scripts for handling frontend data updates from the database

* The SQLAlchemy data-layer abstraction: `stormdatabase.py`

These components integrate seamlessly into the full `storm_project` folder.

## ⚡ Highlights & Technical Notes

* Implemented caching and pagination to optimise performance on large tables

* Ensured frontend code was modular and maintainable

* Worked closely with team members to integrate my components into Docker Compose

* Debugged service orchestration and database startup issues independently

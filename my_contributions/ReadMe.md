# 🛠 My Contributions — Storm Tracking and Analytics Platform

This folder contains the parts of the project that I personally implemented for the Storm Tracking and Analytics Platform.

This was a team-based project. For the full runnable platform, see the `storm_project` folder.

## 📂 Folder Structure
```
my_contributions/
├── sql/                # SQL scripts I wrote to populate the frontend database
├── frontend/           # Dash components and Docker scripts I wrote 
└── README.md           # This file
```

## 🗃 SQL Scripts — Frontend Database Initialisation

I implemented a set of SQL scripts to automate the setup and population of the frontend MySQL database. These scripts are executed during container startup as part of the database initialisation process.

They handle three main responsibilities:

* Database access configuration:
  Creates a dedicated loader user and assigns the required privileges, allowing the db_loader service to initialise and modify the frontend database safely.

* Schema definition:
  Defines the full frontend database schema, including tables, columns, and data types used by the dashboard and visualisation modules.

* Automated data loading:
  Loads preprocessed meteorological data from CSV files in the frontend data cache into the database, ensuring the frontend always reflects the latest cached dataset.

These scripts are designed to run automatically during startup, ensuring that any changes to the cached data are reflected in the frontend database without manual intervention. All query and business logic is handled separately in storm_database.py.

## 🐳 Docker Compose & db_loader Service

I integrated and configured a dedicated `db_loader` service within Docker Compose (`docker-compose.yml`) to automate frontend database initialisation.

The db_loader container performs the following steps at startup:

* Waits for the MySQL service to become available

* Connects as root to ensure required permissions exist

* Creates a loader user and grants privileges (as a safeguard)

* Executes the schema and data-loading SQL scripts to initialise the frontend database

This ensures the frontend database is always created and populated automatically, without manual setup, and reflects any updates to the cached CSV data.

I also worked on integrating this service into the existing Docker Compose workflow and debugging startup sequencing issues to ensure the database was fully ready before frontend services attempted to query it.

## 🗄️ storm_database.py — Data Abstraction & Integration Layer

I designed and implemented a central StormDatabase class to act as the frontend’s data access and integration layer.

This component encapsulates all interactions with the MySQL database and backend storm analytics APIs. Frontend services never issue raw SQL or call backend endpoints directly; instead, all data access flows through this class.

Key responsibilities include:

* Managing SQLAlchemy connections and parameterised queries

* Providing high-level data retrieval methods (storm profiles, radar imagery, aggregated storm metrics, environmental sensor data)

* Automatically switching between backend-populated tables (`*_be`) and frontend cached tables (`*_fe`) depending on availability

* Normalising schema differences between backend and frontend databases

* Populating frontend database tables by calling backend APIs and inserting cleaned, consistent datasets

This abstraction layer improves separation of concerns, reduces duplicated SQL, and insulates the frontend from backend schema changes. It also centralises query logic, improving maintainability and reducing security risks associated with client-constructed SQL.

This design reflects applied object-oriented principles from my computer science training, particularly encapsulation and separation of responsibilities, in a real data-driven system.

## ⚡ High-Volume Table Performance Optimisation (36,000+ rows)

When the real storm dataset was integrated (~36,000 rows with outlier labels), the data explorer page took up to 2 minutes to load and remained unresponsive. After moving outlier detection to backend precomputation, load time improved to ~40s, but the UI was still unusable. Profiling revealed that Dash AG Grid rendering was the primary bottleneck, not the database.

I implemented a custom client-side pagination system to resolve this issue, as the dashboard targets data scientists exploring large historical datasets. 

What I built

* Designed a manual pagination pipeline on top of Dash AG Grid instead of rendering the full dataset at once

* Cached queried results in browser memory using dcc.Store

* Implemented page controls (next/previous, direct page input, page indicator)

* Dynamically sliced pandas DataFrames per page and re-rendered AG Grid with only visible rows

* Decoupled data retrieval from UI rendering to avoid repeated database queries

Technical highlights

* Stack: Dash, Dash AG Grid, pandas

* Pagination logic handled in callbacks

* In-memory caching to eliminate redundant DB calls

* Preserved filtering and sorting support within paginated views

Impact

* Reduced table load time from ~40s to ~1–2s

* Eliminated browser freezing

* Enabled smooth exploration of high-volume storm datasets


## 🧠 Skills Demonstrated

- Data engineering & integration (SQL, schema design, ETL-style loading)
- Containerised systems (Docker Compose, service orchestration)
- Backend–frontend abstraction design
- Performance profiling and optimisation
- Scalable data visualisation
- Collaborative development in a multi-service codebase

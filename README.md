# Glowing Sniffle
## Overview
The Glowing Sniffle project is an ERPNext Mock API Server that mimics ERPNext API endpoints and persists data to a remote SQL database. It provides a generic document storage table and a counter for generating document names.
## Key Features
* Generic document storage table
* Counter for generating document names
* Supports PostgreSQL and MySQL databases
* Fallback in-memory storage for development purposes
## Tech Stack
* Flask for building the API server
* SQLAlchemy for database operations
* PostgreSQL and MySQL for database storage
## Installation
1. Clone the repository: `git clone https://github.com/your-username/glowing-sniffle.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables: `DATABASE_URL` (e.g., `postgresql://user:password@host:port/dbname` or `mysql+pymysql://user:password@host:port/dbname`)
## Usage
1. Run the API server: `python erpnext_mock_api.py`
2. Test the database connection: `python erpnext_test_script.py`
## Environment Variables
* `DATABASE_URL`: the URL of the database (required)
* `BASE_URL`: the base URL of the API (optional)
* `API_KEY` and `API_SECRET`: API credentials (optional)
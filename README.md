# Brief File Description
This section provides a detailed overview of the project's file structure and the role of each component.

## Root Files and Configuration
| File Name |	Path |	Description |
|-----:|-----------| ------------------------------------------- |
| app.py	| Root	| Main Application Entry Point. Initializes the Flask application, registers all Blueprints (handlers), and sets up the application's configuration.
| .env	| Root	| Environment variables file. Used to store configuration secrets like database credentials, host information, and SECRET_KEY. (Ignored by Git)
| .gitignore	| Root	| Specifies files and directories that should be excluded from Git version control.
| requirements.txt	| Root	| Lists all Python dependencies and their exact versions required for the project to run.

## Database Scripts (db_sql/)
| File Name |	Path |	Description |
|-----:|-----------| ------------------------------------------- |
| add_flight_capacity_trigger.sql | db_sql/ | SQL script defining a database trigger to update flight capacity upon booking. |
| basic_info.sql | db_sql/ | SQL script for creating table and inserting essential initial data. |

## Application Handlers (handlers/)
| File Name |	Path |	Description |
|-----:|-----------| ------------------------------------------- |
| agent.py | handlers/ | Booking Agent Logic. Handles agent routes (purchasing for customers, transactions, commission). |
| auth_handlers.py | handlers/ | Authentication Module. Manages user registration, login, and logout. |
| customer.py | handlers/ | Customer Logic. Handles customer routes (flight search, booking, viewing trips, spending). |
| public.py | handlers/ | Public Access Module. Manages routes accessible without authentication. |
| staff.py | handlers/ | Airline Staff Logic. Manages staff routes (flight/plane administration, analytics, reports). |
| utils.py | handlers/ | Utility Functions. Contains common helper functions and database wrappers. |

## Templates (templates/)
| File Name |	Path |	Description |
|-----:|-----------| ------------------------------------------- |
| base.html | templates/ | Master Layout Template. Provides the core structure and navigation. |
| index.html | templates/ | The landing page/welcome screen. |
| login.html | templates/ | User sign-in form page. |
| register.html | templates/ | User registration form page for all roles. |
| public_status.html | templates/ | Public flight status results page. |
| customer_*.html | templates/ | Customer's pages after signed in. |
| agent_*.html | templates/ | Booking agent's pages after signed in. |
| staff_*.html | templates/ | Airline staff's pages after signed in. |
| staff_admin_*.html | templates/ | Admin staff's special pages
| staff_operator_*.html | templates/ | Operator staff's page for monitoring operational statuses. |

# SQL Queries

# Contribution Summary

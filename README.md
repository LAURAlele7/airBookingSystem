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

## Register
1. Customer

   """
                    INSERT INTO customer
                    (email, password, name, building_number, street, city, state,
                     phone_number, passport_expiration_date, passport_country, date_of_birth)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (email_or_username, password_hash, name, building_number, street, city, state,
                     phone_number, passport_expiration_date, passport_country, date_of_birth)
                     
3. Staff

- Staff Account

  """
                    INSERT INTO staff
                    (username, password, first_name, last_name, date_of_birth, airline_name)
                    VALUES (%s, %s, %s, %s, '1990-01-01', %s)
                    """,
                    (email_or_username, password_hash, first_name, last_name, airline_name)

- Staff Permission: Admin/Operator

  "INSERT INTO permission (username, permission_type) VALUES (%s, %s)", (email_or_username, permission_type)
  
3. Agent

   "INSERT INTO booking_agent (email, password) VALUES (%s, %s)",
                    (email_or_username, password_hash)

## Login
1. Customer
   "SELECT * FROM customer WHERE email=%s", (email_or_username,)

2. Staff
- Get Password:   
   "SELECT * FROM staff WHERE username=%s", (email_or_username,)

- Get Permission:   
  "SELECT permission_type FROM permission WHERE username=%s", (username,)

3. Agent
   "SELECT * FROM booking_agent WHERE email=%s", (email_or_username,)

## Customer Extra
1. Upcoming Flight
  
   """
        SELECT f.*, t.ticket_ID, p.purchase_date,
               dep.city as dep_city, 
               arr.city as arr_city
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        LEFT JOIN airport dep ON f.departure_airport = dep.name
        LEFT JOIN airport arr ON f.arrival_airport = arr.name
        WHERE p.customer_email=%s AND f.status IN ('upcoming', 'Delayed')
        ORDER BY f.departure_time ASC
    """

2. Search Flight

   """
    SELECT f.*, 
           dep.city as dep_city, 
           arr.city as arr_city,
           ap.seat_capacity,
           (SELECT COUNT(*) FROM ticket t WHERE t.airline_name = f.airline_name AND t.flight_number = f.flight_number) as sold_cnt
        FROM flight f
        LEFT JOIN airport dep ON f.departure_airport = dep.name
        LEFT JOIN airport arr ON f.arrival_airport = arr.name
        LEFT JOIN airplane ap ON f.airplane_assigned = ap.airplane_id AND f.airline_name = ap.airline_name
        WHERE "f.status = 'upcoming' AND f.departure_time > NOW()" AND
               (f.departure_airport = %s OR dep.city LIKE %s) AND
               
        ORDER BY f.departure_time ASC
        LIMIT 50
    """
# Contribution Summary

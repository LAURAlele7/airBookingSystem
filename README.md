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
   ```
     INSERT INTO customer
     (email, password, name, building_number, street, city, state,
      phone_number, passport_expiration_date, passport_country, date_of_birth) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
   ```               
3. Staff
- Staff Account

  ```
     INSERT INTO staff
     (username, password, first_name, last_name, date_of_birth, airline_name)
     VALUES (%s, %s, %s, %s, '1990-01-01', %s)
  ```
- Staff Permission: Admin/Operator

   ```
     INSERT INTO permission (username, permission_type) VALUES (%s, %s)
   ```
3. Agent

   ```
      INSERT INTO booking_agent (email, password) VALUES (%s, %s)
   ```

## Login
1. Customer
   ```
      SELECT * FROM customer WHERE email=%s
   ```
2. Staff
- Get Password:   
   ```
      SELECT * FROM staff WHERE username=%s
   ```
- Get Permission:   
   ```
      SELECT permission_type FROM permission WHERE username=%s
   ```
3. Agent
   ```
      SELECT * FROM booking_agent WHERE email=%s
   ```

## Public
1. Search
   ```
      SELECT f.*, da.city AS dep_city, aa.city AS arr_city
      FROM flight f
      JOIN airport da ON f.departure_airport = da.name
      JOIN airport aa ON f.arrival_airport = aa.name
      WHERE f.status = 'upcoming' AND f.departure_time > NOW()
         AND (f.departure_airport LIKE %s OR da.city LIKE %s OR da.city IN (SELECT ca.city_name FROM city_alias ca WHERE ca.alias_name = %s)
         AND (f.arrival_airport LIKE %s OR aa.city LIKE %s OR aa.city IN (SELECT ca.city_name FROM city_alias ca WHERE ca.alias_name = %s)
         AND DATE(f.departure_time) = %s
         ORDER BY f.departure_time ASC LIMIT 50
   ```
2. Check Status
   ```
      SELECT f.*, da.city AS dep_city, aa.city AS arr_city
      FROM flight f
      JOIN airport da ON f.departure_airport = da.name
      JOIN airport aa ON f.arrival_airport = aa.name
      WHERE f.status IN ('in-progress', 'delayed')
## Customer Extra
1. Upcoming Flight
  
   ```
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
    ```
2. Search Flight
   ```
      SELECT f.*, dep.city as dep_city, arr.city as arr_city, ap.seat_capacity,
              (SELECT COUNT(*) FROM ticket t WHERE t.airline_name = f.airline_name AND t.flight_number = f.flight_number) as sold_cnt
      FROM flight f
      LEFT JOIN airport dep ON f.departure_airport = dep.name
      LEFT JOIN airport arr ON f.arrival_airport = arr.name
      LEFT JOIN airplane ap ON f.airplane_assigned = ap.airplane_id AND f.airline_name = ap.airline_name
      WHERE (f.status = 'upcoming' AND f.departure_time > NOW()) AND
            (f.departure_airport = %s OR dep.city LIKE %s  OR dep.city IN (select ca.city_name from city_alias ca where ca.alias_name= %s)) AND
            (f.arrival_airport = %s OR arr.city LIKE %s  OR dep.city IN (select ca.city_name from city_alias ca where ca.alias_name= %s)) AND
            (DATE(f.departure_time) = %s)
      ORDER BY f.departure_time ASC
   ```
3. Show Available Airports
   - Departure
      ```
         SELECT DISTINCT f.departure_airport as code, a.city
         FROM flight f
         JOIN airport a ON f.departure_airport = a.name
         WHERE f.status = 'upcoming' AND f.departure_time > NOW()
         ORDER BY a.city
      ```
   - Arrival
     ```
        SELECT DISTINCT f.arrival_airport as code, a.city
        FROM flight f
        JOIN airport a ON f.arrival_airport = a.name
        WHERE f.status = 'upcoming' AND f.departure_time > NOW()
        ORDER BY a.city
     ```
4. Show Purchased Filghts
   ```
      SELECT f.*, t.ticket_ID, p.purchase_date
      FROM purchases p
            JOIN ticket t ON p.ticket_ID = t.ticket_ID
            JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
      WHERE p.customer_email=%s AND
            DATE(f.departure_time) >= %s AND
            DATE(f.departure_time) <= %s AND
            f.departure_airport=%s AND
            f.arrival_airport=%s
      ORDER BY f.departure_time DESC
   ```
5. Book Ticket
   ```
      SELECT f.*, dep.city as dep_city, arr.city as arr_city
      FROM flight f
      LEFT JOIN airport dep ON f.departure_airport = dep.name
      LEFT JOIN airport arr ON f.arrival_airport = arr.name
      WHERE f.airline_name=%s AND f.flight_number=%s
   ```
6. Check Seat Capacity
   ```
      SELECT remaining_seats
      FROM flight
      WHERE airline_name=%s AND flight_number=%s
   ```
7. Purchase Ticket
   - Show Price
     ```
        SELECT price FROM flight WHERE airline_name=%s AND flight_number=%s
     ```
   - Insert Tikckets and Purchase History
     ```
        INSERT INTO ticket (ticket_ID, ticket_price, ticket_status, airline_name, flight_number) VALUES (%s, %s, 'Confirmed', %s, %s);
        INSERT INTO purchases (customer_email, agent_email, ticket_ID, purchase_date) VALUES (%s, NULL, %s, NOW());
     ```
   - Update Remaining Seats
     ```
        UPDATE flight
        SET remaining_seats = remaining_seats - 1
        WHERE airline_name=%s AND flight_number=%s AND remaining_seats > 0
     ```
8. Customer Spending
   - Total Spending
     ```
        SELECT COALESCE(SUM(t.ticket_price), 0) AS total
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        WHERE p.customer_email=%s AND DATE(p.purchase_date) BETWEEN %s AND %s
     ```
   - Monthly Spending
     ```
        SELECT DATE_FORMAT(p.purchase_date, '%%Y-%%m') AS month, COALESCE(SUM(t.ticket_price), 0) AS total
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        WHERE p.customer_email=%s AND DATE(p.purchase_date) BETWEEN %s AND %s
        GROUP BY month
        ORDER BY month
     ```

      
        
# Contribution Summary

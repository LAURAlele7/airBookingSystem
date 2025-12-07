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
   ```
   
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

## Agent Extra
1. Get Airlines Partnership
   ```
      SELECT airline_name FROM work_with WHERE agent_email=%s
   ```
2. View Transaction History
   ```   
      SELECT f.*, t.ticket_ID, p.customer_email, p.purchase_date,
            da.city AS dep_city, aa.city AS arr_city
      FROM purchases p
      JOIN ticket t ON p.ticket_ID = t.ticket_ID
      JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
      LEFT JOIN airport da ON f.departure_airport = da.name
      LEFT JOIN airport aa ON f.arrival_airport = aa.name
      WHERE p.agent_email=%s
            AND DATE(p.purchase_date) >= %s
            AND DATE(p.purchase_date) <= %s
            AND (f.departure_airport LIKE %s OR da.city LIKE %s OR da.city IN (SELECT ca.city_name FROM city_alias ca WHERE ca.alias_name = %s)
            AND (f.arrival_airport LIKE %s OR aa.city LIKE %s OR aa.city IN (SELECT ca.city_name FROM city_alias ca WHERE ca.alias_name = %s)
            AND p.customer_email LIKE %s
            ORDER BY p.purchase_date DESC LIMIT 50
   ```
3. View Available Airports
   - Origin
     ```
         SELECT DISTINCT f.departure_airport AS code, a.city
         FROM flight f
         JOIN airport a ON f.departure_airport = a.name
         WHERE f.airline_name IN ({placeholders})
            AND f.status IN ('upcoming', 'Delayed') 
            AND f.departure_time > NOW()
         ORDER BY a.city
     ```
   - Destination
     ```
        SELECT DISTINCT f.arrival_airport AS code, a.city
        FROM flight f
        JOIN airport a ON f.arrival_airport = a.name
        WHERE f.airline_name IN ({placeholders})
          AND f.status IN ('upcoming', 'Delayed') 
          AND f.departure_time > NOW()
        ORDER BY a.city
     ```
4. View Customers
   ```
      SELECT DISTINCT customer_email FROM purchases WHERE agent_email=%s ORDER BY customer_email
   ```
5. Search Flight
   ```
      SELECT f.*, da.city AS dep_city, aa.city AS arr_city
      FROM flight f
      JOIN airport da ON f.departure_airport = da.name
      JOIN airport aa ON f.arrival_airport = aa.name
      WHERE f.status IN ('upcoming', 'Delayed') AND
            f.remaining_seats > 0 AND
            f.departure_time > NOW() AND
            f.airline_name IN (SELECT airline_name FROM work_with WHERE agent_email=%s) AND
            f.departure_airport LIKE %s OR da.city LIKE %s OR da.city IN (SELECT ca.city_name FROM city_alias ca WHERE ca.alias_name = %s) AND
            f.arrival_airport LIKE %s OR aa.city LIKE %s OR aa.city IN (SELECT ca.city_name FROM city_alias ca WHERE ca.alias_name = %s) AND
            DATE(f.departure_time) = %s
      ORDER BY f.departure_time ASC
      LIMIT 50
   ```
6. Book Ticket
   - View Confirmation
      ```
         SELECT f.*, da.city AS dep_city, aa.city AS arr_city
         FROM flight f
         LEFT JOIN airport da ON f.departure_airport = da.name
         LEFT JOIN airport aa ON f.arrival_airport = aa.name
         WHERE f.airline_name=%s AND f.flight_number=%s
      ```
   - Check Customer
     ```
        SELECT email FROM customer WHERE email=%s
     ```
   - Check Airline Partnership
     ```
        SELECT * FROM work_with WHERE agent_email=%s AND airline_name=%s
     ```
   - Check Capacity
     ```
        SELECT remaining_seats
        FROM flight
        WHERE airline_name=%s AND flight_number=%s
     ```
   - Get Price
     ```
        SELECT price FROM flight WHERE airline_name=%s AND flight_number=%s
     ```
   - Purchase
     ```
        INSERT INTO ticket (ticket_ID, ticket_price, ticket_status, airline_name, flight_number);
        INSERT INTO purchases (customer_email, agent_email, ticket_ID, purchase_date)
            VALUES (%s, %s, %s, %s);
        UPDATE flight SET remaining_seats = remaining_seats - 1
            WHERE airline_name=%s AND flight_number=%s;
     ```
7. Comission Analytics
   - Total and Average Comission
     ```
        SELECT 
            COUNT(*) as total_tickets,
            SUM(f.price * 0.10) as total_commission,
            AVG(f.price * 0.10) as avg_commission
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE p.agent_email=%s AND p.purchase_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
     ```
   - Top Tickets
     ```
        SELECT 
            COUNT(*) as total_tickets,
            SUM(f.price * 0.10) as total_commission,
            AVG(f.price * 0.10) as avg_commission
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE p.agent_email=%s AND p.purchase_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
      ```
   - Top Comission
     ```
        SELECT p.customer_email, SUM(f.price * 0.10) as total_comm
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE p.agent_email=%s 
          AND p.purchase_date >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
        GROUP BY p.customer_email
        ORDER BY total_comm DESC
        LIMIT 5
     ```

## Staff Extra
1. Search Flights
   ```
      SELECT f.*, da.city AS dep_city, aa.city AS arr_city
      FROM flight f
      LEFT JOIN airport da ON f.departure_airport = da.name
      LEFT JOIN airport aa ON f.arrival_airport = aa.name
      WHERE f.airline_name = %s
         AND f.departure_time BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 30 DAY)
         AND f.departure_time >= %s
         AND f.departure_time <= %s
         AND (f.departure_airport LIKE %s OR da.city LIKE %s OR da.city IN (SELECT ca.city_name FROM city_alias ca WHERE ca.alias_name = %s)
         AND (f.arrival_airport LIKE %s OR aa.city LIKE %s OR aa.city IN (SELECT ca.city_name FROM city_alias ca WHERE ca.alias_name = %s)
      ORDER BY f.departure_time ASC
   ```
2. View Passengers
   ```
      SELECT c.name, c.email, t.ticket_ID
      FROM ticket t
      JOIN purchases p ON t.ticket_ID = p.ticket_ID
      JOIN customer c ON p.customer_email = c.email
      WHERE t.airline_name = %s AND t.flight_number = %s
   ```
3. View Customer Flights
   ```
      SELECT t.ticket_ID, f.flight_number, f.departure_airport, f.arrival_airport, 
         f.departure_time, f.arrival_time, f.status,
         da.city AS dep_city, aa.city AS arr_city,
         p.customer_email
      FROM purchases p
         JOIN ticket t ON p.ticket_ID = t.ticket_ID
         JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
         LEFT JOIN airport da ON f.departure_airport = da.name
         LEFT JOIN airport aa ON f.arrival_airport = aa.name
      WHERE f.airline_name = %s
            AND p.customer_email = %s
      ORDER BY f.departure_time DESC LIMIT 50
   ```
4. Analytics
   - Top Agent by Month
     ```
        SELECT p.agent_email,
               COUNT(*) AS ticket_count,
               COALESCE(SUM(t.ticket_price*0.1), 0) AS commission
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE f.airline_name=%s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
          AND p.agent_email IS NOT NULL
        GROUP BY p.agent_email
        ORDER BY ticket_count DESC
        LIMIT 5
     ```        
   - Top Agent by Year
     ```
        SELECT p.agent_email,
               COALESCE(SUM(t.ticket_price*0.1), 0) AS total_commission
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE f.airline_name=%s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
          AND p.agent_email IS NOT NULL
        GROUP BY p.agent_email
        ORDER BY total_commission DESC
        LIMIT 5
     ```
   - Frequent Customer
     ```   
        SELECT p.customer_email, COUNT(*) AS cnt
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE f.airline_name=%s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
        GROUP BY p.customer_email
        ORDER BY cnt DESC
        LIMIT 1
     ```
   - Ticket Sold per Month
      ```
         SELECT DATE_FORMAT(p.purchase_date, '%%Y-%%m') AS month,
         COUNT(*) AS cnt
         FROM purchases p
         JOIN ticket t ON p.ticket_ID = t.ticket_ID
         JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
         WHERE f.airline_name=%s
         GROUP BY month
         ORDER BY month
      ```
   - Delay Analysis
     ```
        SELECT status, COUNT(*) AS cnt
        FROM flight
        WHERE airline_name=%s
        GROUP BY status
     ```
   - Top Destination
     ```
        SELECT f.arrival_airport, COUNT(*) AS cnt
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE f.airline_name=%s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
        GROUP BY f.arrival_airport
        ORDER BY cnt DESC
        LIMIT 5
     ```
5. Admin Extra
   - Add City and Airport
     ```
        INSERT INTO city (city_name) VALUES (%s);
        INSERT INTO airport (name, city) VALUES (%s, %s)
     ```
   - Add Airplane
     ```
        INSERT INTO airplane (airplane_id, airline_name, seat_capacity) VALUES (%s, %s, %s)
     ```
   - Add Flight
     ```
        INSERT INTO flight (flight_number, airline_name, departure_airport, arrival_airport, departure_time, arrival_time, price, status, airplane_assigned, remaining_seats) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
     ```
   - Add Agent
     ```
        SELECT * FROM booking_agent WHERE email=%s;
        INSERT INTO work_with (agent_email, airline_name) VALUES (%s, %s)
     ```
6. Operator Extra
   - Update Status
     ```
        UPDATE flight SET status=%s WHERE airline_name=%s AND flight_number=%s
     ```
# Contribution Summary

CREATE TABLE customer
    (email   varchar(50),
    password    varchar(255) NOT NULL,
    name    varchar(30) NOT NULL,
    building_number int,
    street  varchar(60),
    city    varchar(30),
    state   varchar(30),
    phone_number    varchar(16) NOT NULL,
    passport_expiration_date    date NOT NULL,
    passport_country    varchar(20) NOT NULL,
    date_of_birth   date NOT NULL,
    primary key(email)
);

CREATE TABLE city(
    city_name varchar(30) NOT NULL,
    primary key(city_name)
);

CREATE TABLE airport(
    name    char(3),
    city    varchar(30) NOT NULL,
    primary key(name),
    foreign key(city) references city(city_name) ON UPDATE CASCADE
);

CREATE TABLE airline(
    name    varchar(20),
    primary key(name)
);

CREATE TABLE airplane(
    airplane_id varchar(20),
    airline_name    varchar(20),
    seat_capacity   int NOT NULL,
    primary key(airplane_id, airline_name),
    foreign key(airline_name) references airline(name) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE flight(
    flight_number   varchar(6),
    airline_name    varchar(20),
    departure_airport   char(3) NOT NULL,
    arrival_airport char(3) NOT NULL,
    departure_time  datetime NOT NULL,
    arrival_time    datetime NOT NULL,
    price   numeric(12,2) check (price >= 0),
    status  varchar(11) NOT NULL,
    airplane_assigned  varchar(20) NOT NULL,
    remaining_seats   int NOT NULL,
    primary key(flight_number, airline_name),
    foreign key(airline_name) references airline(name) ON DELETE CASCADE ON UPDATE CASCADE,
    foreign key(departure_airport) references airport(name) ON UPDATE CASCADE,
    foreign key(arrival_airport) references airport(name) ON UPDATE CASCADE,
    foreign key(airplane_assigned) references airplane(airplane_id) ON UPDATE CASCADE
);

CREATE TABLE ticket(
    ticket_ID   char(16),
    ticket_price    numeric(12,2) check (ticket_price >= 0) ,
    ticket_status   varchar(10) NOT NULL,
    airline_name    varchar(20) NOT NULL,
    flight_number   varchar(6) NOT NULL,
    primary key(ticket_ID),
    foreign key(airline_name, flight_number) references flight(airline_name, flight_number) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE booking_agent(
    email   varchar(50),
    password    varchar(100) NOT NULL,
    primary key(email)
);

CREATE TABLE staff(
    username    varchar(30),
    password    varchar(100) NOT NULL,
    first_name   varchar(20) NOT NULL,
    last_name    varchar(20) NOT NULL,
    date_of_birth   date NOT NULL,
    airline_name    varchar(20) NOT NULL,
    primary key(username),
    foreign key(airline_name) references airline(name) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE city_alias(
    city_name varchar(30) NOT NULL,
    alias_name varchar(30) NOT NULL,
    primary key(city_name, alias_name),
    foreign key(city_name) references city(city_name) ON UPDATE CASCADE
);

CREATE TABLE permission(
    username    varchar(50),
    permission_type    varchar(10) NOT NULL,
    primary key(username, permission_type),
    foreign key(username) references staff(username) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE work_with(
    agent_email   varchar(50),
    airline_name    varchar(20),
    primary key(agent_email, airline_name),
    foreign key(agent_email) references booking_agent(email) ON DELETE CASCADE ON UPDATE CASCADE,
    foreign key(airline_name) references airline(name) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE purchases(
    customer_email   varchar(50) NOT NULL,
    agent_email   varchar(50),
    ticket_ID   char(16) NOT NULL,
    purchase_date   datetime NOT NULL,
    primary key(customer_email, ticket_ID),
    foreign key(customer_email) references customer(email) ON UPDATE CASCADE,
    foreign key(agent_email) references booking_agent(email) ON UPDATE CASCADE,
    foreign key(ticket_ID) references ticket(ticket_ID) ON DELETE CASCADE ON UPDATE CASCADE
);

-- inserting airlines
INSERT INTO airline VALUES("Delta");
INSERT INTO airline VALUES("United");
INSERT INTO airline VALUES("Southwest");
-- inserting cities 
Insert into city values("NewYork");
Insert into city values("Shanghai");
Insert into city values("LosAngeles");
Insert into city values("SanFrancisco");
Insert into city values("Chicago");
Insert into city values("Atlanta");
-- inserting airports
INSERT INTO airport VALUES("JFK", "NewYork");
INSERT INTO airport VALUES("PVG", "Shanghai");
INSERT INTO airport VALUES("LAX", "LosAngeles");
INSERT INTO airport VALUES("SFO", "SanFrancisco"); 
INSERT INTO airport VALUES("ORD", "Chicago");
INSERT INTO airport VALUES("ATL", "Atlanta");
-- inserting customers and booking agents
INSERT INTO customer VALUES("lz2879@nyu.edu", "123456", "Laura Zhang", "76", "Daduhe Road", "Shanghai", "Shanghai", "13817686666", "20300501","China", "20040501");
INSERT INTO customer VALUES("ly2888@nyu.edu", "789126", "Leyang Zhang", "255", "Meichuan Road", "Atlanta", "Florida", "13817688888", "20280423","Japan", "20000213");
INSERT INTO customer VALUES("xz2666@nyu.edu", "234567", "Julia Wang", "80", "Lafayette Street", "New York", "New York", "13817686666", "20351214","United States", "19881230");
INSERT INTO booking_agent VALUES("xiecheng@outlook.com", "654321");
INSERT INTO booking_agent VALUES("lvyou@163.com", "123789");
-- inserting airplanes
INSERT INTO airplane VALUES("N12345", "Delta", 180);
INSERT INTO airplane VALUES("N67890", "United", 220);
INSERT INTO airplane VALUES("N54321", "Southwest", 150);
INSERT INTO airplane VALUES("N67890", "Delta", 200);
INSERT INTO airplane VALUES("N11223", "United", 250);
-- inserting flights
INSERT INTO flight VALUES("DL1001", "Delta", "JFK", "LAX", "2025-09-01 08:00", "2025-09-01 11:00", 300.00, "in-progress", "N12345",180);
INSERT INTO flight VALUES("UA2001", "United", "LAX", "ORD", "2025-09-02 09:00", "2025-09-02 15:00", 250.00, "Delayed", "N67890", 200);
INSERT INTO flight VALUES("SW3001", "Southwest", "PVG", "ATL", "2025-09-03 12:00", "2025-09-03 15:00", 700.00, "upcoming", "N54321", 180);
INSERT INTO flight VALUES("DL1002", "Delta", "ATL", "JFK", "2025-09-04 14:00", "2025-09-04 17:00", 280.00, "Delayed", "N67890", 150);
INSERT INTO flight VALUES("UA2002", "United", "JFK", "SFO", "2025-09-05 10:00", "2025-09-05 14:00", 320.00, "upcoming", "N11223", 220);
INSERT INTO flight VALUES("DL1003", "Delta", "SFO", "JFK", "2025-10-15 12:00", "2025-10-16 16:00", 330.00, "upcoming", "N12345", 250);
-- inserting tickets
INSERT INTO ticket VALUES("1111222233334444", 300.00, "Confirmed", "Delta", "DL1001");
INSERT INTO ticket VALUES("5555666677778888", 250.00, "Pending", "United", "UA2001");
INSERT INTO ticket VALUES("9999000011112222", 700.00, "Cancelled", "Southwest", "SW3001");
INSERT INTO ticket VALUES("3333444455556666", 280.00, "Confirmed", "Delta", "DL1002");
INSERT INTO ticket VALUES("7777888899990000", 320.00, "Confirmed", "United", "UA2002");

-- inserting purchases
INSERT INTO purchases VALUES("lz2879@nyu.edu", NULL, "1111222233334444", "2025-08-01 12:00");
INSERT INTO purchases VALUES("xz2666@nyu.edu", "xiecheng@outlook.com", "5555666677778888", "2025-08-02 13:00");
INSERT INTO purchases VALUES("ly2888@nyu.edu", "lvyou@163.com", "3333444455556666", "2025-08-03 14:00");
INSERT INTO purchases VALUES("lz2879@nyu.edu", "lvyou@163.com", "7777888899990000", "2025-08-04 15:00");

-- inserting staff
INSERT INTO staff VALUES("admin_delta", "admin123", "John", "Smith", "1980-05-15", "Delta");
INSERT INTO staff VALUES("manager_delta", "mgr123", "Sarah", "Johnson", "1985-08-22", "Delta");
INSERT INTO staff VALUES("agent_united", "agent456", "Mike", "Brown", "1990-03-10", "United");
INSERT INTO staff VALUES("staff_southwest", "staff789", "Emily", "Davis", "1992-11-30", "Southwest");
INSERT INTO staff VALUES("ops_delta", "ops111", "Robert", "Wilson", "1988-07-18", "Delta");

-- inserting permissions for staff
INSERT INTO permission VALUES("admin_delta", "admin");
INSERT INTO permission VALUES("admin_delta", "operator");
INSERT INTO permission VALUES("manager_delta", "manager");
INSERT INTO permission VALUES("agent_united", "operator");
INSERT INTO permission VALUES("staff_southwest", "operator");
INSERT INTO permission VALUES("ops_delta", "operator");

-- inserting work_with relationships
INSERT INTO work_with VALUES("xiecheng@outlook.com", "Delta");
INSERT INTO work_with VALUES("xiecheng@outlook.com", "United");
INSERT INTO work_with VALUES("lvyou@163.com", "Delta");
INSERT INTO work_with VALUES("lvyou@163.com", "Southwest");
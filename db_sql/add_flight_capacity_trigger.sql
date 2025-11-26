DELIMITER $$

-- ==========================================================
-- 触发器: before_insert_flight_capacity_check
-- 目的: 确保 flight.remaining_seats 在 [1, capacity] 范围内。
-- ==========================================================
CREATE TRIGGER before_insert_flight_capacity_check
BEFORE INSERT ON flight
FOR EACH ROW
BEGIN
    DECLARE capacity INT;
    
    -- 1. 查找 assigned airplane 的 seat_capacity
    SELECT seat_capacity INTO capacity
    FROM airplane
    WHERE airplane_id = NEW.airplane_assigned  
      AND airline_name = NEW.airline_name;

    -- *** 自动补充信息 (关键点) ***
    -- 2. 如果 NEW.remaining_seats 为 NULL，则默认将其设置为最大容量
    IF NEW.remaining_seats IS NULL THEN
        SET NEW.remaining_seats = capacity;
    END IF;

    -- *** 错误检查 (NOT NULL 后的校验) ***
    
    -- 3. 校验剩余座位数不能超过实际容量 (上界检查)
    IF NEW.remaining_seats > capacity THEN
        -- 触发 SQL 错误，阻止插入
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Initial remaining_seats cannot exceed the assigned airplane seat capacity.';
    END IF;
    
    -- 4. 校验剩余座位数必须大于零 (下界检查)
    IF NEW.remaining_seats <= 0 THEN
        -- 触发 SQL 错误，阻止插入
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: New flights must be initialized with a positive number of remaining seats.';
    END IF;

END$$

DELIMITER ;
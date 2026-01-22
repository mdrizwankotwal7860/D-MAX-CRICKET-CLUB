CREATE DATABASE IF NOT EXISTS box_cricket_db;
USE box_cricket_db;

CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    customer_phone VARCHAR(20) NOT NULL,
    booking_date DATE NOT NULL,
    start_time TIME NOT NULL,
    duration_hours INT DEFAULT 1,
    total_price DECIMAL(10, 2) DEFAULT 0.00,
    paid_amount DECIMAL(10, 2) DEFAULT 0.00,
    payment_image VARCHAR(255),
    payment_status ENUM('pending', 'paid_manual_verification') DEFAULT 'pending',
    payment_uploaded_at TIMESTAMP NULL DEFAULT NULL,
    status ENUM('pending', 'confirmed', 'cancelled') DEFAULT 'confirmed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tournaments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    event_date DATE NOT NULL,
    entry_fee DECIMAL(10, 2) NOT NULL,
    image_url VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS tournament_registrations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tournament_id INT,
    team_name VARCHAR(100) NOT NULL,
    captain_name VARCHAR(100) NOT NULL,
    captain_phone VARCHAR(20) NOT NULL,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
);

-- Insert some dummy data for tournaments
INSERT INTO tournaments (title, description, event_date, entry_fee, image_url) VALUES 
('Summer Cricket Cup', 'Join the hottest tournament of the season!', '2024-06-15', 5000.00, 'assets/event1.jpg'),
('Monsoon League', 'Play in the rain (covered turf)!', '2024-07-10', 4000.00, 'assets/event2.jpg');

CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

-- Insert default admin (if not exists)
INSERT IGNORE INTO admins (username, password) VALUES ('admin', 'admin123');

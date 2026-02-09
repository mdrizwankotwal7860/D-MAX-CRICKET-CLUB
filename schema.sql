CREATE DATABASE IF NOT EXISTS box_cricket_db;
USE box_cricket_db;

-- =========================
-- ADMINS
-- =========================
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- USERS
-- =========================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- SLOTS
-- =========================
CREATE TABLE slots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slot_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES admins(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

-- =========================
-- PRICING
-- =========================
CREATE TABLE pricing (
    id INT AUTO_INCREMENT PRIMARY KEY,
    duration_hours INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES admins(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

-- =========================
-- BOOKINGS
-- =========================
CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    slot_id INT NOT NULL,
    booking_date DATE NOT NULL,
    pricing_id INT NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    paid_amount DECIMAL(10,2) DEFAULT 0.00,
    payment_proof VARCHAR(255),
    payment_status ENUM(
        'pending',
        'paid_manual_verification',
        'paid_verified',
        'rejected'
    ) DEFAULT 'pending',
    booking_status ENUM(
        'pending',
        'confirmed',
        'rejected'
    ) DEFAULT 'pending',
    verified_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (slot_id) REFERENCES slots(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    FOREIGN KEY (pricing_id) REFERENCES pricing(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    FOREIGN KEY (verified_by) REFERENCES admins(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    UNIQUE (slot_id, booking_date)
);

-- =========================
-- TOURNAMENTS
-- =========================
CREATE TABLE tournaments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    event_date DATE NOT NULL,
    entry_fee DECIMAL(10,2) NOT NULL,
    image_url VARCHAR(255),
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES admins(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

-- =========================
-- TOURNAMENT REGISTRATIONS
-- =========================
CREATE TABLE tournament_registrations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tournament_id INT NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    captain_name VARCHAR(100) NOT NULL,
    captain_phone VARCHAR(20) NOT NULL,
    status ENUM(
        'pending',
        'confirmed',
        'rejected'
    ) DEFAULT 'pending',
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    UNIQUE (tournament_id, team_name)
);

-- =========================
-- CONTACT MESSAGES
-- =========================
CREATE TABLE contact_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    handled_by INT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (handled_by) REFERENCES admins(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

-- =========================
-- SLOT LOCKS (Concurrency)
-- =========================
CREATE TABLE slot_locks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slot_id INT NOT NULL,
    user_identifier VARCHAR(50) NOT NULL,
    lock_expiry DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_slot_lock (slot_id),
    FOREIGN KEY (slot_id) REFERENCES slots(id) ON DELETE CASCADE
);

-- =========================
-- DEFAULT ADMIN (EXAMPLE HASH)
-- =========================
INSERT INTO admins (username, password_hash)
VALUES ('admin', '$2y$10$examplehashedpasswordstring');

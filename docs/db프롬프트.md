CREATE DATABASE emotion_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_general_ci;

USE emotion_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO users (username, password) VALUES
('testuser1', '1234'),
('testuser2', '1234'),
('admin', 'admin123'),
('user_a', 'pass_a'),
('user_b', 'pass_b');

INSERT INTO users (username, password, created_at) VALUES
('old_user', 'oldpass', '2024-01-01 10:00:00'),
('today_user', 'todaypass', NOW());

select *
  from users

commit
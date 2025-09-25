-- ========================================
-- Volunteer Matching System Database (LightFM compatible)
-- ========================================

CREATE DATABASE volunteer_match;
\c volunteer_match;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Students Table
CREATE TABLE students (
    student_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    college VARCHAR(100),
    city VARCHAR(50),
    skills JSONB,
    interests JSONB,
    availability JSONB,
    willingness_level INT CHECK (willingness_level BETWEEN 1 AND 5),
    preferred_shift VARCHAR(20),
    language VARCHAR(50),
    transport_access BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- NGOs Table
CREATE TABLE ngos (
    ngo_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    city VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Opportunities Table
CREATE TABLE opportunities (
    opportunity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ngo_id UUID REFERENCES ngos(ngo_id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    required_skills JSONB,
    cause_type VARCHAR(50),
    city VARCHAR(50),
    urgency_level INT CHECK (urgency_level BETWEEN 1 AND 5),
    importance_level INT CHECK (importance_level BETWEEN 1 AND 5),
    shift_type VARCHAR(20),
    duration_hours INT,
    language_required VARCHAR(50),
    certification_offered BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Interactions Table
CREATE TYPE action_enum AS ENUM ('view','save','apply');

CREATE TABLE interactions (
    interaction_id SERIAL PRIMARY KEY,
    student_id UUID REFERENCES students(student_id) ON DELETE CASCADE,
    opportunity_id UUID REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    action_type action_enum,
    certainty_factor FLOAT CHECK (certainty_factor >= 0 AND certainty_factor <= 1),
    timestamp TIMESTAMP DEFAULT NOW()
);

-- ========================================
-- Sample Data (for testing LightFM)
-- ========================================

-- Students
INSERT INTO students (name,email,password_hash,college,city,skills,interests,availability,willingness_level,preferred_shift,language)
VALUES
('Rajith Khan','rajith@example.com','hash123','KCT','Chennai','["Python","Teaching"]','["Education","Environment"]','["Weekends"]',5,'Flexible','English');

-- NGOs
INSERT INTO ngos (name,email,password_hash,city,description)
VALUES
('Helping Hands','contact1@helpinghands.org','hash123','Chennai','NGO for community welfare'),
('Green Earth','contact2@greenearth.org','hash123','Bangalore','Environmental NGO'),
('Health First','contact3@healthfirst.org','hash123','Mumbai','Health awareness NGO'),
('EduConnect','contact4@educonnect.org','hash123','Delhi','Education NGO');

-- Opportunities
INSERT INTO opportunities (ngo_id,title,description,required_skills,cause_type,city,urgency_level,importance_level,shift_type,duration_hours,language_required,certification_offered)
VALUES
((SELECT ngo_id FROM ngos WHERE name='Helping Hands'),'Teach Kids','Teach basic computer skills to kids','["Teaching","Python"]','Education','Chennai',3,5,'Short',5,'English',true),
((SELECT ngo_id FROM ngos WHERE name='Green Earth'),'Tree Plantation','Plant trees in local parks','["Gardening","Teamwork"]','Environment','Bangalore',4,5,'Long',8,'English',true);

-- Interactions
INSERT INTO interactions (student_id, opportunity_id, action_type, certainty_factor)
VALUES
((SELECT student_id FROM students WHERE name='Rajith Khan'),
 (SELECT opportunity_id FROM opportunities WHERE title='Teach Kids'),
 'apply', 1.0),
((SELECT student_id FROM students WHERE name='Ananya R'),
 (SELECT opportunity_id FROM opportunities WHERE title='Tree Plantation'),
 'view', 0.3);

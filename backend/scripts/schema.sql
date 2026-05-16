-- DishHome AI Call Center Postgres Schema for Supabase

CREATE SCHEMA IF NOT EXISTS dh;
SET search_path TO dh, public;

-- Users
CREATE TABLE IF NOT EXISTS users (
    username VARCHAR(50) PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Customers
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    mobile VARCHAR(20) NOT NULL,
    smartcard VARCHAR(50),
    address TEXT,
    ward VARCHAR(50),
    package VARCHAR(100),
    balance_npr INTEGER DEFAULT 0,
    due_date DATE,
    status VARCHAR(50),
    ont_id VARCHAR(50),
    scenario VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ONT Status
CREATE TABLE IF NOT EXISTS ont_status (
    ont_id VARCHAR(50) PRIMARY KEY,
    device_model VARCHAR(50),
    serial_number VARCHAR(100),
    firmware_version VARCHAR(100),
    hardware_version VARCHAR(50),
    olt_id VARCHAR(50),
    olt_port VARCHAR(50),
    ont_index INTEGER,
    online BOOLEAN DEFAULT TRUE,
    rx_power_dbm NUMERIC(5, 2),
    tx_power_dbm NUMERIC(5, 2),
    line_attenuation_db NUMERIC(5, 2),
    uptime_hours INTEGER DEFAULT 0,
    last_reboot TIMESTAMP WITH TIME ZONE,
    pppoe_session VARCHAR(50),
    wifi_radio_2g BOOLEAN DEFAULT TRUE,
    wifi_radio_5g BOOLEAN DEFAULT TRUE,
    error_state VARCHAR(50),
    area_outage BOOLEAN DEFAULT FALSE,
    scenario VARCHAR(50)
);

-- Tickets
CREATE TABLE IF NOT EXISTS tickets (
    id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES customers(customer_id),
    issue TEXT NOT NULL,
    priority VARCHAR(20),
    status VARCHAR(50),
    assigned_team VARCHAR(100),
    eta_minutes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    labels TEXT[]
);

-- Calls
CREATE TABLE IF NOT EXISTS calls (
    id VARCHAR(50) PRIMARY KEY,
    caller_number VARCHAR(20),
    called_number VARCHAR(20),
    customer_id VARCHAR(50) REFERENCES customers(customer_id),
    customer_name VARCHAR(100),
    language VARCHAR(10),
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_sec INTEGER,
    status VARCHAR(50),
    resolution VARCHAR(100),
    intent VARCHAR(100),
    ai_confidence NUMERIC(4, 3),
    sentiment VARCHAR(20),
    labels TEXT[],
    transcript JSONB DEFAULT '[]'::jsonb
);

-- Chat Sessions (for Khushi Chatbot)
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    messages JSONB DEFAULT '[]'::jsonb
);

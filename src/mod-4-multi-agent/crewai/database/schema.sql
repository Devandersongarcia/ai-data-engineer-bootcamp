-- CrewAI Abandoned Order Detection System
-- PostgreSQL Schema for Managed Database
-- 
-- This schema tracks Uber Eats orders, drivers, and abandonment decisions
-- made by the multi-agent system

-- Create database (run this separately if needed)
-- CREATE DATABASE uber_eats_monitoring;

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS cancellations CASCADE;
DROP TABLE IF EXISTS order_events CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS drivers CASCADE;

-- Drivers table: Tracks driver information and current status
CREATE TABLE drivers (
    id SERIAL PRIMARY KEY,
    driver_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    status VARCHAR(50) DEFAULT 'offline' CHECK (status IN ('offline', 'online', 'busy', 'break')),
    current_lat DECIMAL(10, 8),
    current_lng DECIMAL(11, 8),
    last_movement TIMESTAMP,
    movement_speed_kmh DECIMAL(5, 2),  -- Current speed in km/h
    total_deliveries INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table: Main order tracking
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    customer_name VARCHAR(100),
    customer_phone VARCHAR(20),
    restaurant_name VARCHAR(100),
    driver_id INTEGER REFERENCES drivers(id),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN (
        'pending', 'confirmed', 'preparing', 'ready', 
        'driver_assigned', 'picked_up', 'out_for_delivery', 
        'delivered', 'cancelled'
    )),
    total_amount DECIMAL(10, 2),
    delivery_address TEXT,
    delivery_lat DECIMAL(10, 8),
    delivery_lng DECIMAL(11, 8),
    distance_km DECIMAL(5, 2),  -- Distance from restaurant to delivery
    estimated_delivery_time TIMESTAMP,
    actual_delivery_time TIMESTAMP,
    driver_assigned_at TIMESTAMP,
    picked_up_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Order events: Detailed lifecycle tracking
CREATE TABLE order_events (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_description TEXT,
    event_data JSONB,  -- Flexible storage for event-specific data
    agent_involved VARCHAR(100),  -- Which CrewAI agent triggered this
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cancellations: Track all cancellation decisions
CREATE TABLE cancellations (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    cancelled_by VARCHAR(50) DEFAULT 'ai_system',
    reason TEXT NOT NULL,
    reason_category VARCHAR(50) CHECK (reason_category IN (
        'stuck_driver', 'overdue_delivery', 'driver_offline', 
        'no_movement', 'customer_request', 'restaurant_issue', 'other'
    )),
    agent_decision JSONB,  -- Store complete agent analysis
    driver_analysis JSONB,  -- Delivery Tracker agent's analysis
    timeline_analysis JSONB,  -- Timeline Analyzer agent's analysis
    guardian_decision JSONB,  -- Order Guardian's final decision
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    refund_amount DECIMAL(10, 2),
    cancelled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at);
CREATE INDEX idx_orders_driver ON orders(driver_id);
CREATE INDEX idx_orders_delivery_time ON orders(estimated_delivery_time);
CREATE INDEX idx_drivers_status ON drivers(status);
CREATE INDEX idx_drivers_last_movement ON drivers(last_movement);
CREATE INDEX idx_order_events_order ON order_events(order_id);
CREATE INDEX idx_order_events_timestamp ON order_events(timestamp);
CREATE INDEX idx_cancellations_order ON cancellations(order_id);
CREATE INDEX idx_cancellations_reason_category ON cancellations(reason_category);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
CREATE TRIGGER update_drivers_updated_at BEFORE UPDATE ON drivers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create view for problematic orders (for easy monitoring)
CREATE VIEW problematic_orders AS
SELECT 
    o.id,
    o.order_number,
    o.status,
    o.driver_id,
    d.name as driver_name,
    d.status as driver_status,
    d.last_movement,
    EXTRACT(EPOCH FROM (NOW() - d.last_movement))/60 as minutes_since_movement,
    o.estimated_delivery_time,
    EXTRACT(EPOCH FROM (NOW() - o.estimated_delivery_time))/60 as minutes_overdue,
    EXTRACT(EPOCH FROM (NOW() - o.created_at))/60 as order_age_minutes
FROM orders o
LEFT JOIN drivers d ON o.driver_id = d.id
WHERE o.status = 'out_for_delivery'
AND o.created_at < NOW() - INTERVAL '30 minutes'
AND NOT EXISTS (
    SELECT 1 FROM cancellations c WHERE c.order_id = o.id
);

-- Sample queries for monitoring
COMMENT ON VIEW problematic_orders IS 'Orders that may need cancellation review:
- Status is "out_for_delivery"
- Created more than 30 minutes ago
- Not already cancelled
Use: SELECT * FROM problematic_orders WHERE minutes_overdue > 45 OR minutes_since_movement > 20;';

-- Grant permissions (adjust based on your database user)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;
-- GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO your_user;
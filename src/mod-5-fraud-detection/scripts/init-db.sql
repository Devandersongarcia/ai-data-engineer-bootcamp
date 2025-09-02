-- Initialize PostgreSQL database for fraud detection system
-- This script sets up the necessary tables and indexes for metrics storage

-- Create database if it doesn't exist (handled by Docker init)
-- CREATE DATABASE IF NOT EXISTS fraud_detection;

-- Use the fraud_detection database
\c fraud_detection;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schema for fraud detection
CREATE SCHEMA IF NOT EXISTS fraud_detection;

-- Set default schema
SET search_path TO fraud_detection, public;

-- Table for storing fraud detection results
CREATE TABLE IF NOT EXISTS fraud_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    fraud_score DECIMAL(5,4) NOT NULL CHECK (fraud_score >= 0 AND fraud_score <= 1),
    recommended_action VARCHAR(50) NOT NULL CHECK (recommended_action IN ('ALLOW', 'REVIEW', 'BLOCK')),
    confidence_level DECIMAL(5,4) NOT NULL CHECK (confidence_level >= 0 AND confidence_level <= 1),
    reasoning TEXT,
    detected_patterns JSONB,
    agent_analyses JSONB,
    processing_time_ms INTEGER NOT NULL,
    detection_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    system_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing system metrics
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metric_type VARCHAR(100) NOT NULL,
    metric_name VARCHAR(200) NOT NULL,
    metric_value DECIMAL(15,6),
    metric_unit VARCHAR(50),
    metric_tags JSONB,
    component VARCHAR(100),
    environment VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing performance metrics
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    total_detections INTEGER NOT NULL DEFAULT 0,
    avg_processing_time_ms DECIMAL(10,3),
    throughput_per_second DECIMAL(10,3),
    uptime_seconds INTEGER,
    success_rate DECIMAL(5,4) CHECK (success_rate >= 0 AND success_rate <= 1),
    error_rate DECIMAL(5,4) CHECK (error_rate >= 0 AND error_rate <= 1),
    sla_compliance BOOLEAN,
    component_health JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing alerts
CREATE TABLE IF NOT EXISTS fraud_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id VARCHAR(255) UNIQUE NOT NULL,
    order_id VARCHAR(255) NOT NULL,
    alert_type VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    fraud_score DECIMAL(5,4) NOT NULL,
    recommended_action VARCHAR(50) NOT NULL,
    alert_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(255),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolution_status VARCHAR(50) DEFAULT 'OPEN' CHECK (resolution_status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'DISMISSED')),
    alert_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing user behavior profiles
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_key VARCHAR(255) UNIQUE NOT NULL,
    total_orders INTEGER DEFAULT 0,
    avg_order_value DECIMAL(10,2),
    avg_order_frequency_days DECIMAL(10,2),
    preferred_restaurants JSONB,
    preferred_payment_methods JSONB,
    common_delivery_areas JSONB,
    avg_order_time_hour INTEGER,
    weekend_order_ratio DECIMAL(5,4),
    cancellation_rate DECIMAL(5,4),
    refund_rate DECIMAL(5,4),
    payment_failure_rate DECIMAL(5,4),
    account_age_days INTEGER,
    last_order_timestamp TIMESTAMP WITH TIME ZONE,
    risk_score DECIMAL(5,4) CHECK (risk_score >= 0 AND risk_score <= 1),
    profile_last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing action results
CREATE TABLE IF NOT EXISTS action_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id VARCHAR(255) NOT NULL,
    action_taken VARCHAR(50) NOT NULL,
    action_status VARCHAR(50) NOT NULL CHECK (action_status IN ('PENDING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    action_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    execution_time_ms INTEGER,
    action_details JSONB,
    error_message TEXT,
    reviewer_assigned VARCHAR(255),
    review_completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_fraud_results_order_id ON fraud_results (order_id);
CREATE INDEX IF NOT EXISTS idx_fraud_results_user_id ON fraud_results (user_id);
CREATE INDEX IF NOT EXISTS idx_fraud_results_timestamp ON fraud_results (detection_timestamp);
CREATE INDEX IF NOT EXISTS idx_fraud_results_fraud_score ON fraud_results (fraud_score);
CREATE INDEX IF NOT EXISTS idx_fraud_results_action ON fraud_results (recommended_action);

CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics (metric_timestamp);
CREATE INDEX IF NOT EXISTS idx_system_metrics_type ON system_metrics (metric_type);
CREATE INDEX IF NOT EXISTS idx_system_metrics_component ON system_metrics (component);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics (timestamp);

CREATE INDEX IF NOT EXISTS idx_fraud_alerts_order_id ON fraud_alerts (order_id);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_timestamp ON fraud_alerts (alert_timestamp);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_severity ON fraud_alerts (severity);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_status ON fraud_alerts (resolution_status);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_key ON user_profiles (user_key);
CREATE INDEX IF NOT EXISTS idx_user_profiles_risk_score ON user_profiles (risk_score);
CREATE INDEX IF NOT EXISTS idx_user_profiles_updated ON user_profiles (profile_last_updated);

CREATE INDEX IF NOT EXISTS idx_action_results_order_id ON action_results (order_id);
CREATE INDEX IF NOT EXISTS idx_action_results_timestamp ON action_results (action_timestamp);
CREATE INDEX IF NOT EXISTS idx_action_results_status ON action_results (action_status);

-- Create triggers for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_fraud_alerts_updated_at 
    BEFORE UPDATE ON fraud_alerts 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at 
    BEFORE UPDATE ON user_profiles 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create views for common queries
CREATE OR REPLACE VIEW fraud_summary AS
SELECT 
    DATE(detection_timestamp) as detection_date,
    COUNT(*) as total_detections,
    AVG(fraud_score) as avg_fraud_score,
    COUNT(CASE WHEN recommended_action = 'BLOCK' THEN 1 END) as blocked_orders,
    COUNT(CASE WHEN recommended_action = 'REVIEW' THEN 1 END) as review_orders,
    COUNT(CASE WHEN recommended_action = 'ALLOW' THEN 1 END) as allowed_orders,
    AVG(processing_time_ms) as avg_processing_time_ms
FROM fraud_results 
GROUP BY DATE(detection_timestamp)
ORDER BY detection_date DESC;

CREATE OR REPLACE VIEW high_risk_users AS
SELECT 
    user_key,
    risk_score,
    total_orders,
    avg_order_value,
    cancellation_rate,
    refund_rate,
    payment_failure_rate,
    profile_last_updated
FROM user_profiles 
WHERE risk_score > 0.7 
ORDER BY risk_score DESC;

CREATE OR REPLACE VIEW system_health_summary AS
SELECT 
    DATE(timestamp) as metric_date,
    AVG(avg_processing_time_ms) as avg_processing_time,
    AVG(throughput_per_second) as avg_throughput,
    AVG(success_rate) as avg_success_rate,
    AVG(error_rate) as avg_error_rate,
    COUNT(CASE WHEN sla_compliance = true THEN 1 END)::float / COUNT(*) as sla_compliance_rate
FROM performance_metrics 
GROUP BY DATE(timestamp)
ORDER BY metric_date DESC;

-- Insert initial configuration data
INSERT INTO system_metrics (metric_type, metric_name, metric_value, metric_unit, component, environment)
VALUES 
    ('system', 'initialization_complete', 1, 'boolean', 'database', 'development'),
    ('system', 'schema_version', 1.0, 'version', 'database', 'development')
ON CONFLICT DO NOTHING;

-- Create user for application (if needed)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'fraud_app') THEN
        CREATE USER fraud_app WITH PASSWORD 'fraud_app_password';
    END IF;
END
$$;

-- Grant permissions to application user
GRANT USAGE ON SCHEMA fraud_detection TO fraud_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA fraud_detection TO fraud_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA fraud_detection TO fraud_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA fraud_detection TO fraud_app;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA fraud_detection 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO fraud_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA fraud_detection 
    GRANT USAGE, SELECT ON SEQUENCES TO fraud_app;

-- Vacuum and analyze for better performance
VACUUM ANALYZE;

-- Log successful initialization
INSERT INTO system_metrics (metric_type, metric_name, metric_value, metric_unit, component, environment)
VALUES ('system', 'database_initialized', 1, 'boolean', 'database', 'development');

-- Success message
\echo 'Fraud detection database initialized successfully!'
\echo 'Created tables: fraud_results, system_metrics, performance_metrics, fraud_alerts, user_profiles, action_results'
\echo 'Created views: fraud_summary, high_risk_users, system_health_summary'
\echo 'Database is ready for the fraud detection system'
CREATE DATABASE IF NOT EXISTS invoice_db;

CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(100) UNIQUE NOT NULL,
    order_id VARCHAR(255),
    order_date DATE NOT NULL,
    restaurant_name VARCHAR(255) NOT NULL,
    restaurant_cnpj VARCHAR(20),
    subtotal DECIMAL(15, 2) NOT NULL,
    delivery_fee DECIMAL(15, 2) DEFAULT 0,
    service_fee DECIMAL(15, 2) DEFAULT 0,
    discount DECIMAL(15, 2) DEFAULT 0,
    tip DECIMAL(15, 2) DEFAULT 0,
    total DECIMAL(15, 2) NOT NULL,
    delivery_address TEXT,
    payment_method VARCHAR(100),
    transaction_id VARCHAR(255),
    line_items JSONB NOT NULL,
    metadata JSONB NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS processing_audit (
    id SERIAL PRIMARY KEY,
    process_id VARCHAR(100) UNIQUE NOT NULL,
    source_file VARCHAR(500) NOT NULL,
    file_size BIGINT,
    model_detected VARCHAR(50),
    confidence_score FLOAT,
    processing_status VARCHAR(50),
    error_message TEXT,
    dag_run_id VARCHAR(255),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER
);

CREATE TABLE IF NOT EXISTS model_performance (
    id SERIAL PRIMARY KEY,
    model_id VARCHAR(50) NOT NULL,
    invoice_id INTEGER REFERENCES invoices(id),
    confidence_score FLOAT,
    extraction_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_invoices_order_number ON invoices(order_number);
CREATE INDEX IF NOT EXISTS idx_invoices_restaurant ON invoices(restaurant_name);
CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(order_date);
CREATE INDEX IF NOT EXISTS idx_invoices_total ON invoices(total);
CREATE INDEX IF NOT EXISTS idx_invoices_metadata ON invoices USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_invoices_line_items ON invoices USING GIN(line_items);
CREATE INDEX IF NOT EXISTS idx_audit_process_id ON processing_audit(process_id);
CREATE INDEX IF NOT EXISTS idx_audit_status ON processing_audit(processing_status);
CREATE INDEX IF NOT EXISTS idx_model_perf_model ON model_performance(model_id);
CREATE INDEX IF NOT EXISTS idx_model_perf_date ON model_performance(created_at);

CREATE OR REPLACE VIEW invoice_summary AS
SELECT 
    DATE_TRUNC('day', order_date) as date,
    COUNT(*) as total_invoices,
    SUM(total) as total_revenue,
    AVG(total) as avg_invoice_amount,
    SUM(delivery_fee) as total_delivery_fees,
    SUM(tip) as total_tips,
    COUNT(DISTINCT restaurant_name) as unique_restaurants
FROM invoices
GROUP BY DATE_TRUNC('day', order_date);

CREATE OR REPLACE VIEW model_accuracy AS
SELECT 
    model_id,
    COUNT(*) as total_processed,
    AVG(confidence_score) as avg_confidence,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
    AVG(extraction_time_ms) as avg_extraction_time_ms
FROM model_performance
GROUP BY model_id;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_invoices_updated_at
BEFORE UPDATE ON invoices
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
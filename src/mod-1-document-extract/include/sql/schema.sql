DROP TABLE IF EXISTS processing_logs CASCADE;
DROP TABLE IF EXISTS invoice_items CASCADE;
DROP TABLE IF EXISTS invoice_details CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    filename VARCHAR(255) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    model_confidence DECIMAL(3,2),
    processing_status VARCHAR(20) DEFAULT 'pending',
    processed_at TIMESTAMP,
    minio_path VARCHAR(500),
    file_checksum VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_status CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS invoice_details (
    detail_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    order_date TIMESTAMP,
    restaurant_name VARCHAR(255),
    restaurant_id VARCHAR(100),
    restaurant_cnpj VARCHAR(20),
    restaurant_address TEXT,
    restaurant_phone VARCHAR(20),
    restaurant_rating DECIMAL(2,1),
    customer_cpf_masked VARCHAR(20),
    subtotal DECIMAL(10,2),
    delivery_fee DECIMAL(10,2),
    service_fee DECIMAL(10,2),
    discount DECIMAL(10,2),
    tip_amount DECIMAL(10,2),
    total_amount DECIMAL(10,2),
    delivery_time_minutes INTEGER,
    delivery_distance_km DECIMAL(5,2),
    delivery_speed_kmh DECIMAL(5,2),
    delivery_altitude_m INTEGER,
    driver_name VARCHAR(100),
    driver_id VARCHAR(50),
    payment_method VARCHAR(50),
    payment_card_last4 VARCHAR(4),
    transaction_id VARCHAR(100),
    delivery_address TEXT,
    gps_tracking_id VARCHAR(100),
    raw_extraction_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoice_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    item_name VARCHAR(255),
    quantity INTEGER DEFAULT 1,
    unit_price DECIMAL(10,2),
    total_price DECIMAL(10,2),
    customizations TEXT,
    item_order INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS processing_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    message TEXT,
    error_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_log_status CHECK (status IN ('started', 'success', 'failed', 'retry'))
);

CREATE INDEX IF NOT EXISTS idx_invoices_order_number ON invoices(order_number);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(processing_status);
CREATE INDEX IF NOT EXISTS idx_invoices_created ON invoices(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_invoice_details_invoice_id ON invoice_details(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice_id ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_invoice_id ON processing_logs(invoice_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_created ON processing_logs(created_at DESC);

CREATE OR REPLACE VIEW invoice_summary AS
SELECT
    i.invoice_id,
    i.order_number,
    i.filename,
    i.model_type,
    i.processing_status,
    i.processed_at,
    d.restaurant_name,
    d.order_date,
    d.total_amount,
    d.driver_name,
    COUNT(DISTINCT it.item_id) as item_count,
    i.created_at
FROM invoices i
LEFT JOIN invoice_details d ON i.invoice_id = d.invoice_id
LEFT JOIN invoice_items it ON i.invoice_id = it.invoice_id
GROUP BY
    i.invoice_id, i.order_number, i.filename, i.model_type,
    i.processing_status, i.processed_at, d.restaurant_name,
    d.order_date, d.total_amount, d.driver_name, i.created_at;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_invoices_updated_at BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
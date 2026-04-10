-- MxA Mobile - Complete PostgreSQL Database Schema
-- Product: MxA Mobile (standalone)
-- Database: mxa_mobile
-- User: mxa_mobile_user

-- This schema preserves the SQLite structure from forensic_toolkit
-- and adds web-specific tables for users, jobs, and audit logging.

-- ============================================================================
-- USERS AND AUTHENTICATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    keycloak_sub VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    roles JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_email_check CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z]{2,}$')
);

CREATE INDEX idx_users_keycloak_sub ON users(keycloak_sub);
CREATE INDEX idx_users_email ON users(email);

-- ============================================================================
-- CASES (WORKSPACES)
-- ============================================================================

CREATE TABLE IF NOT EXISTS cases (
    id SERIAL PRIMARY KEY,
    case_number VARCHAR(100) UNIQUE NOT NULL,
    case_name VARCHAR(255) NOT NULL,
    description TEXT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cases_user_id ON cases(user_id);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_case_number ON cases(case_number);

-- ============================================================================
-- PROCESSING JOBS
-- ============================================================================

CREATE TABLE IF NOT EXISTS processing_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'queued',
    config JSONB DEFAULT '{}'::jsonb,
    result JSONB,
    error TEXT,
    progress INTEGER DEFAULT 0,
    current_step VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    CONSTRAINT progress_range CHECK (progress >= 0 AND progress <= 100)
);

CREATE INDEX idx_jobs_job_id ON processing_jobs(job_id);
CREATE INDEX idx_jobs_case_id ON processing_jobs(case_id);
CREATE INDEX idx_jobs_user_id ON processing_jobs(user_id);
CREATE INDEX idx_jobs_status ON processing_jobs(status);
CREATE INDEX idx_jobs_created_at ON processing_jobs(created_at DESC);

-- ============================================================================
-- COMMUNICATIONS (from forensic_toolkit)
-- ============================================================================

CREATE TABLE IF NOT EXISTS communications (
    id SERIAL PRIMARY KEY,
    case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES processing_jobs(id) ON DELETE SET NULL,
    mode VARCHAR(50),
    source_file TEXT,
    timestamp TIMESTAMP,
    date_str VARCHAR(50),
    sender TEXT,
    receiver TEXT,
    direction VARCHAR(20),
    chat TEXT,
    subject TEXT,
    message TEXT,
    body TEXT,
    category VARCHAR(100) DEFAULT 'All items',
    categories TEXT DEFAULT 'All items',
    transcription_status VARCHAR(50) DEFAULT '',
    transcription_reason TEXT DEFAULT '',
    attachment_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_comms_case_id ON communications(case_id);
CREATE INDEX idx_comms_job_id ON communications(job_id);
CREATE INDEX idx_comms_mode ON communications(mode);
CREATE INDEX idx_comms_timestamp ON communications(timestamp);
CREATE INDEX idx_comms_category ON communications(category);
CREATE INDEX idx_comms_sender ON communications(sender);
CREATE INDEX idx_comms_receiver ON communications(receiver);

-- Full-text search index
CREATE INDEX idx_comms_message_fts ON communications USING gin(to_tsvector('english', COALESCE(message, '') || ' ' || COALESCE(body, '')));

-- ============================================================================
-- ATTACHMENTS (from forensic_toolkit)
-- ============================================================================

CREATE TABLE IF NOT EXISTS attachments (
    id SERIAL PRIMARY KEY,
    communication_id INTEGER REFERENCES communications(id) ON DELETE CASCADE,
    case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
    mode VARCHAR(50),
    source_file TEXT,
    attachment_name TEXT,
    attachment_path TEXT,
    preview_image_path TEXT DEFAULT '',
    preview_doc_path TEXT DEFAULT '',
    preview_media_path TEXT DEFAULT '',
    attachment_type VARCHAR(50),
    file_ext VARCHAR(20),
    found_status VARCHAR(20),
    width INTEGER,
    height INTEGER,
    text_detected VARCHAR(20),
    ocr_status VARCHAR(50),
    ocr_text TEXT,
    reason TEXT,
    gps_lat DOUBLE PRECISION,
    gps_lon DOUBLE PRECISION,
    gps_alt DOUBLE PRECISION,
    gps_timestamp VARCHAR(50),
    gps_source VARCHAR(50) DEFAULT '',
    gps_confidence DOUBLE PRECISION,
    exif_make TEXT DEFAULT '',
    exif_model TEXT DEFAULT '',
    exif_datetime_original TEXT DEFAULT '',
    has_gps INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_attach_communication_id ON attachments(communication_id);
CREATE INDEX idx_attach_case_id ON attachments(case_id);
CREATE INDEX idx_attach_mode ON attachments(mode);
CREATE INDEX idx_attach_file_ext ON attachments(file_ext);
CREATE INDEX idx_attach_found_status ON attachments(found_status);
CREATE INDEX idx_attach_has_gps ON attachments(has_gps);
CREATE INDEX idx_attach_gps_coords ON attachments(gps_lat, gps_lon) WHERE gps_lat IS NOT NULL AND gps_lon IS NOT NULL;

-- ============================================================================
-- TAGS (from forensic_toolkit)
-- ============================================================================

CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(20) DEFAULT '#2f7de1',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (case_id, name)
);

CREATE INDEX idx_tags_case_id ON tags(case_id);

-- ============================================================================
-- ITEM TAGS (Many-to-Many)
-- ============================================================================

CREATE TABLE IF NOT EXISTS item_tags (
    id SERIAL PRIMARY KEY,
    communication_id INTEGER REFERENCES communications(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (communication_id, tag_id)
);

CREATE INDEX idx_item_tags_communication_id ON item_tags(communication_id);
CREATE INDEX idx_item_tags_tag_id ON item_tags(tag_id);

-- ============================================================================
-- AUDIT LOGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    metadata JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_action ON audit_logs(action);

-- ============================================================================
-- APPLICATION SETTINGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS app_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_settings_key ON app_settings(key);

-- ============================================================================
-- SCHEMA VERSION TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Insert initial version
INSERT INTO schema_version (version, description) 
VALUES (1, 'Initial schema for MxA Mobile web application')
ON CONFLICT (version) DO NOTHING;

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to relevant tables
CREATE TRIGGER update_cases_updated_at
    BEFORE UPDATE ON cases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON processing_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_settings_updated_at
    BEFORE UPDATE ON app_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Communication summary with attachment info
CREATE OR REPLACE VIEW v_communications_summary AS
SELECT 
    c.*,
    cases.case_number,
    cases.case_name,
    COUNT(a.id) as actual_attachment_count,
    COUNT(CASE WHEN a.has_gps = 1 THEN 1 END) as gps_attachment_count,
    COUNT(CASE WHEN a.ocr_status = 'ocr_done' THEN 1 END) as ocr_attachment_count
FROM communications c
LEFT JOIN cases ON c.case_id = cases.id
LEFT JOIN attachments a ON c.id = a.communication_id
GROUP BY c.id, cases.case_number, cases.case_name;

-- View: Job status with case info
CREATE OR REPLACE VIEW v_job_status AS
SELECT 
    j.*,
    c.case_number,
    c.case_name,
    u.email as user_email,
    u.name as user_name
FROM processing_jobs j
LEFT JOIN cases c ON j.case_id = c.id
LEFT JOIN users u ON j.user_id = u.id;

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

-- Grant appropriate permissions to application user
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO mxa_mobile_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO mxa_mobile_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO mxa_mobile_user;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON DATABASE mxa_mobile IS 'MxA Mobile - Communication Intelligence Platform';
COMMENT ON TABLE users IS 'Application users authenticated via Keycloak';
COMMENT ON TABLE cases IS 'Investigation cases/workspaces';
COMMENT ON TABLE processing_jobs IS 'Background processing jobs (Celery tasks)';
COMMENT ON TABLE communications IS 'Parsed communication records (SMS, calls, emails, etc.)';
COMMENT ON TABLE attachments IS 'Media and document attachments';
COMMENT ON TABLE tags IS 'User-defined tags for organizing communications';
COMMENT ON TABLE audit_logs IS 'Audit trail of user actions';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

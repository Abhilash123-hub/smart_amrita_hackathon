-- Migration 0001: Thresholds Policy History Audit Table
-- Tracks all calibrated and manual adjustments to operational thresholds.

CREATE TABLE IF NOT EXISTS thresholds_history (
    id SERIAL PRIMARY KEY,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    changed_by VARCHAR(128) NOT NULL,
    track VARCHAR(32) NOT NULL, -- 'TEXT', 'IMAGE', 'AUDIO', 'VIDEO', 'CODE'
    parameter_name VARCHAR(64) NOT NULL,
    old_value NUMERIC(5, 4) NOT NULL,
    new_value NUMERIC(5, 4) NOT NULL,
    false_positive_rate NUMERIC(5, 4),
    catch_rate NUMERIC(5, 4),
    calibration_report_ref VARCHAR(256),
    justification TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_thresholds_history_track ON thresholds_history(track);
CREATE INDEX IF NOT EXISTS idx_thresholds_history_changed_at ON thresholds_history(changed_at DESC);

-- Seed baseline initial thresholds
INSERT INTO thresholds_history (
    changed_by, track, parameter_name, old_value, new_value, false_positive_rate, catch_rate, justification
) VALUES
('SYSTEM_INIT', 'TEXT', 'text_cross_encoder_threshold', 0.85, 0.85, 0.0120, 1.0000, 'Baseline default from engineering specification'),
('SYSTEM_INIT', 'IMAGE', 'image_clip_cosine_threshold', 0.90, 0.90, 0.0080, 1.0000, 'Baseline default from engineering specification')
ON CONFLICT DO NOTHING;

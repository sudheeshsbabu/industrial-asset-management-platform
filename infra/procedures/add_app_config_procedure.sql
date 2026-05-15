CREATE OR REPLACE PROCEDURE add_app_config (
    p_key TEXT,
    p_value TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO app_config (key, value)
    VALUES(p_key, p_value)
    ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value
    WHERE app_config.value <> EXCLUDED.value;
END $$;
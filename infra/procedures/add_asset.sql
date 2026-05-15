CREATE OR REPLACE PROCEDURE add_asset (
    p_name VARCHAR,
    p_site VARCHAR,
    p_status VARCHAR
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO assets (name, site, status)
    VALUES (p_name, p_site, p_status);
END $$;
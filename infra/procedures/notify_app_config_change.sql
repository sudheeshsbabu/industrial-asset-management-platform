CREATE OR REPLACE FUNCTION notify_app_config_change()
RETURNS TRIGGER AS
$$
BEGIN

    PERFORM pg_notify(
        'app_config_changed',
        json_build_object(
            'table', TG_TABLE_NAME,
            'operation', TG_OP,
            'key', COALESCE(NEW.config_key, OLD.config_key)
        )::text
    );

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

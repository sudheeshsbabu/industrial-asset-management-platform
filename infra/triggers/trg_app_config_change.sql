DROP TRIGGER IF EXISTS trg_app_config_change ON app_config;

CREATE TRIGGER trg_app_config_change
AFTER INSERT OR UPDATE ON app_config
FOR EACH ROW
EXECUTE FUNCTION notify_app_config_change();
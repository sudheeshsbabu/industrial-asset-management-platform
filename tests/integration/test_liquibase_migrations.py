import pytest
import asyncpg
import subprocess
import asyncio
import json

TEST_DB_NAME = "assetops_test"
TEST_DB_URL = f"postgresql://postgres:postgres@localhost:5432/{TEST_DB_NAME}"
LIQUIBASE_TEST_URL = f"jdbc:postgresql://postgres:5432/{TEST_DB_NAME}"
EXPECTED_CHANGESET_COUNT = 16

@pytest.fixture(scope="module", autouse=True)
async def setup_test_database():
    """
    This fixture runs once before the tests in this file.
    It creates the test DB and runs liquibase against it.
    """

    #  1. Create the test database
    subprocess.run([
        "docker", "exec", "assetops-postgres",
        "psql", "-U", "postgres", "-c",
        f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH (FORCE);"
    ], capture_output=True)
    
    subprocess.run([
        "docker", "exec", "assetops-postgres",
        "psql", "-U", "postgres", "-c",
        f"CREATE DATABASE {TEST_DB_NAME};"
    ], check=True, capture_output=True)

    # 2. Run liquibase update against the TEST database
    print("\n Running Liquibase against test database...")
    result = subprocess.run([
        "docker", "compose", "run", "--rm",
        "liquibase", f"--url={LIQUIBASE_TEST_URL}",
        "update"
    ], capture_output=True, text=True)

    assert result.returncode == 0, f"Liquibase migration failed!\n{result.stderr}"

    yield # Let the tests run!


@pytest.fixture
async def db_conn():
    conn = await asyncpg.connect(TEST_DB_URL)
    try:
        yield conn
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_liquibase_records_all_changesets(db_conn):
    """
    Verifies Liquibase applied every changeset from the master changelog.
    """
    rows = await db_conn.fetch(
        """
        SELECT id, filename
        FROM databasechangelog
        WHERE filename LIKE 'changesets/%'
        ORDER BY orderexecuted;
        """
    )

    assert len(rows) == EXPECTED_CHANGESET_COUNT
    assert rows[0]["filename"] == "changesets/001_create_assets_table.yaml"
    assert rows[-1]["filename"] == "changesets/016_alter_assets_time_default.yaml"


@pytest.mark.asyncio
async def test_assets_table_has_expected_migrated_columns(db_conn):
    """
    Verifies the final assets schema after all Liquibase migrations.
    """
    rows = await db_conn.fetch(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'assets';
        """
    )
    columns = {row["column_name"]: dict(row) for row in rows}

    assert set(columns) == {
        "id",
        "name",
        "site",
        "status",
        "asset_uuid",
        "description",
        "asset_code",
        "created_at",
        "updated_at",
    }
    assert columns["id"]["is_nullable"] == "NO"
    assert columns["asset_uuid"]["data_type"] == "uuid"
    assert columns["asset_uuid"]["is_nullable"] == "NO"
    assert "gen_random_uuid" in columns["asset_uuid"]["column_default"]
    assert columns["asset_code"]["is_nullable"] == "NO"
    assert columns["created_at"]["is_nullable"] == "NO"
    assert columns["updated_at"]["is_nullable"] == "NO"
    assert "now()" in columns["created_at"]["column_default"].lower()
    assert "now()" in columns["updated_at"]["column_default"].lower()


@pytest.mark.asyncio
async def test_seed_data_is_loaded_by_test_context(db_conn):
    """
    Verifies test-context seed changesets loaded expected asset and config data.
    """
    seeded_asset_count = await db_conn.fetchval(
        "SELECT COUNT(*) FROM assets WHERE asset_code LIKE 'ASSET-%';"
    )
    app_name = await db_conn.fetchval(
        "SELECT value FROM app_config WHERE key = 'APP_NAME';"
    )

    assert seeded_asset_count == 30
    assert app_name == "AssetOps"


@pytest.mark.asyncio
async def test_asset_code_constraints_are_enforced(db_conn):
    """
    Verifies Liquibase-created NOT NULL and unique constraints for asset_code.
    """
    await db_conn.execute(
        """
        INSERT INTO assets (name, site, status, asset_code)
        VALUES ('Constraint Probe A', 'Test Plant', 'Idle', 'TEST-ASSET-001');
        """
    )

    with pytest.raises(asyncpg.UniqueViolationError):
        await db_conn.execute(
            """
            INSERT INTO assets (name, site, status, asset_code)
            VALUES ('Constraint Probe B', 'Test Plant', 'Idle', 'TEST-ASSET-001');
            """
        )

    with pytest.raises(asyncpg.NotNullViolationError):
        await db_conn.execute(
            """
            INSERT INTO assets (name, site, status)
            VALUES ('Constraint Probe C', 'Test Plant', 'Idle');
            """
        )

#3. Test triggers
@pytest.mark.asyncio
async def test_app_config_trigger_fires(db_conn):
    """
    Tests that the liquibase trigger and function for app_config changes
    """
    notifications = []

    # Setup our listener for PostgreSQL NOTIFY events
    def listener(conn, pid, channel, payload):
        notifications.append(payload)

    await db_conn.add_listener("app_config_changed", listener)

    # Call the liquibase-created procedure to add a config row
    await db_conn.execute("""
        INSERT INTO app_config(key, value) VALUES('test_key','test_value')
    """)
    await asyncio.sleep(1) # Wait for notification
    assert len(notifications) == 1, "The trigger did not fire a notificaiton!"
    assert "test_key" in notifications[0], "The notification does not contain 'test_key'!"

    payload = json.loads(notifications[0])
    assert payload == {
        "table": "app_config",
        "operation": "INSERT",
        "key": "test_key",
    }


@pytest.mark.asyncio
async def test_add_app_config_procedure_only_notifies_on_changes(db_conn):
    """
    Verifies the Liquibase-created config upsert procedure is idempotent.
    """
    notifications = []

    def listener(conn, pid, channel, payload):
        notifications.append(json.loads(payload))

    await db_conn.add_listener("app_config_changed", listener)

    await db_conn.execute("CALL add_app_config('TEST_FEATURE_FLAG', 'enabled');")
    await asyncio.sleep(1)
    assert [notification["operation"] for notification in notifications] == ["INSERT"]

    await db_conn.execute("CALL add_app_config('TEST_FEATURE_FLAG', 'enabled');")
    await asyncio.sleep(1)
    assert [notification["operation"] for notification in notifications] == ["INSERT"]

    await db_conn.execute("CALL add_app_config('TEST_FEATURE_FLAG', 'disabled');")
    await asyncio.sleep(1)
    assert [notification["operation"] for notification in notifications] == [
        "INSERT",
        "UPDATE",
    ]

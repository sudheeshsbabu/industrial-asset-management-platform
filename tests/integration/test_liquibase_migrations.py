import pytest
import asyncpg
import subprocess
import asyncio

TEST_DB_NAME = "assetops_test"
TEST_DB_URL = f"postgresql://postgres:postgres@localhost:5432/{TEST_DB_NAME}"
LIQUIBASE_TEST_URL = f"jdbc:postgresql://postgres:5432/{TEST_DB_NAME}"

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

#3. Test triggers
@pytest.mark.asyncio
async def test_app_config_trigger_fires():
    """
    Tests that the liquibase trigger and function for app_config changes
    """
    conn = await asyncpg.connect(TEST_DB_URL)

    notifications = []

    # Setup our listener for PostgreSQL NOTIFY events
    def listener(conn, pid, channel, payload):
        notifications.append(payload)

    await conn.add_listener("app_config_changed", listener)

    # Call the liquibase-created procedure to add a config row
    await conn.execute("""
        INSERT INTO app_config(key, value) VALUES('test_key','test_value')
    """)
    await asyncio.sleep(1) # Wait for notification
    assert len(notifications) == 1, "The trigger did not fire a notificaiton!"
    assert "test_key" in notifications[0], "The notification does not contain 'test_key'!"

    await conn.close()

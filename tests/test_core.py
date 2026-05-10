from telegram_mcp.core.logger import logger

def test_logger():
    # Just verify it doesn't crash
    logger.info("Testing logger")
    assert True

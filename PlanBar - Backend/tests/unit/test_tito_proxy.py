from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.tito_proxy import TiTOProxy, tito_proxy


@pytest.fixture
def proxy():
    return TiTOProxy()


@pytest.mark.asyncio
async def test_submit_job(proxy: TiTOProxy):
    mock_response = MagicMock()
    mock_response.json.return_value = {"jobId": 42}

    with patch.object(proxy.client, "post", AsyncMock(return_value=mock_response)):
        result = await proxy.submit_job({"key": "value"})
        assert result["jobId"] == 42


@pytest.mark.asyncio
async def test_get_job_status(proxy: TiTOProxy):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "completed"}

    with patch.object(proxy.client, "get", AsyncMock(return_value=mock_response)):
        result = await proxy.get_job_status(1)
        assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_retry_job(proxy: TiTOProxy):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "processing"}

    with patch.object(proxy.client, "post", AsyncMock(return_value=mock_response)):
        result = await proxy.retry_job(1)
        assert result["status"] == "processing"


@pytest.mark.asyncio
async def test_check_health_healthy(proxy: TiTOProxy):
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(proxy.client, "get", AsyncMock(return_value=mock_response)):
        assert await proxy.check_health() is True


@pytest.mark.asyncio
async def test_check_health_unhealthy(proxy: TiTOProxy):
    mock_response = MagicMock()
    mock_response.status_code = 503

    with patch.object(proxy.client, "get", AsyncMock(return_value=mock_response)):
        assert await proxy.check_health() is False


@pytest.mark.asyncio
async def test_check_health_connection_error(proxy: TiTOProxy):
    with patch.object(proxy.client, "get", AsyncMock(side_effect=httpx.HTTPError("connection failed"))):
        assert await proxy.check_health() is False


@pytest.mark.asyncio
async def test_close(proxy: TiTOProxy):
    with patch.object(proxy.client, "aclose", AsyncMock()) as mock_close:
        await proxy.close()
        mock_close.assert_awaited_once()


def test_tito_proxy_singleton():
    assert tito_proxy is not None
    assert isinstance(tito_proxy, TiTOProxy)

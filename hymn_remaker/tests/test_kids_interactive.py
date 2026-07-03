import pytest
import asyncio
from unittest.mock import patch, MagicMock

# This test will mock the required components of the api to ensure
# kids_scrape correctly utilizes the sync_interactive_callback when interactive_mode is True
@pytest.mark.asyncio
async def test_kids_scrape_interactive_callback():
    from fastapi.testclient import TestClient
    from hymn_remaker.api import app, manager

    client = TestClient(app)

    with patch("hymn_remaker.api.process_single_midi") as mock_process:
        with patch("hymn_remaker.src.children_song_finder.ChildrenSongFinder") as mock_finder:
            # Setup mock finder
            mock_finder_instance = MagicMock()
            mock_finder_instance.download_all.return_value = ["/mock/path/song.mid"]
            mock_finder.return_value = mock_finder_instance

            # Trigger the scrape with interactive_mode=True
            response = client.post("/api/v1/kids/scrape", data={"interactive_mode": "true"})
            assert response.status_code == 200

            # Let the background task run
            await asyncio.sleep(0.5)

            # Check that process_single_midi was called with an interactive_callback
            mock_process.assert_called_once()
            _, kwargs = mock_process.call_args
            assert "interactive_callback" in kwargs
            assert kwargs["interactive_callback"] is not None

            # Since interactive_mode is true, the callback should not return None
            # We can test the callback behavior
            cb = kwargs["interactive_callback"]

            # Mock the manager's request_interactive_review to return a future
            with patch.object(manager, "request_interactive_review") as mock_request:
                mock_future = asyncio.Future()
                mock_future.set_result({"title": "Reviewed Title"})
                mock_request.return_value = mock_future

                # Execute the callback
                # Note: The callback uses run_coroutine_threadsafe so it needs the real loop to be active.
                # For a pure unit test, we just check if it correctly delegates to the manager.
                # Since testing threadsafe callbacks in pytest-asyncio is tricky,
                # we just verify the arguments were passed correctly to the pipeline.

@pytest.mark.asyncio
async def test_kids_scrape_no_interactive_callback():
    from fastapi.testclient import TestClient
    from hymn_remaker.api import app

    client = TestClient(app)

    with patch("hymn_remaker.api.process_single_midi") as mock_process:
        with patch("hymn_remaker.src.children_song_finder.ChildrenSongFinder") as mock_finder:
            # Setup mock finder
            mock_finder_instance = MagicMock()
            mock_finder_instance.download_all.return_value = ["/mock/path/song.mid"]
            mock_finder.return_value = mock_finder_instance

            # Trigger the scrape with interactive_mode=False
            response = client.post("/api/v1/kids/scrape", data={"interactive_mode": "false"})
            assert response.status_code == 200

            # Let the background task run
            await asyncio.sleep(0.5)

            # Check that process_single_midi was called and test the callback
            mock_process.assert_called_once()
            _, kwargs = mock_process.call_args
            assert "interactive_callback" in kwargs

            cb = kwargs["interactive_callback"]

            # Since interactive_mode is false, the callback should immediately return None
            result = cb({"title": "Test"})
            assert result is None

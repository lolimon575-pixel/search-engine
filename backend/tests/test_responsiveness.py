import asyncio
import threading

import httpx
import pytest

from app import main


@pytest.mark.parametrize('endpoint', ['search', 'verification'])
def test_slow_network_work_does_not_block_suggestions(monkeypatch, endpoint):
    started = threading.Event()
    release = threading.Event()

    def slow_work(*args, **kwargs):
        started.set()
        release.wait(timeout=3)
        return ([], []) if endpoint == 'search' else {'status': 'UNKNOWN'}

    target = main.web_search if endpoint == 'search' else main.web_search.verifier
    monkeypatch.setattr(target, 'search' if endpoint == 'search' else 'verify', slow_work)
    monkeypatch.setattr(main, 'get_suggestions', lambda *args, **kwargs: ['nova'])

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url='http://test') as client:
            url = '/api/search?q=nova' if endpoint == 'search' else '/api/verification?url=https://example.com'
            pending = asyncio.create_task(client.get(url))
            try:
                assert await asyncio.to_thread(started.wait, 1)
                response = await asyncio.wait_for(client.get('/api/suggest?q=no'), timeout=1)
                assert response.json()['suggestions'] == ['nova']
                assert not pending.done(), 'The slow request blocked the event loop'
            finally:
                release.set()
                await pending

    asyncio.run(scenario())

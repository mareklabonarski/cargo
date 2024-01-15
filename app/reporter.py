import asyncio
import logging

import httpx

from app.settings import STATE_URL, STATE_INTERVAL
from app.state import get_app_state, redis_client


async def send_state(client: httpx.AsyncClient):
    try:
        state = await get_app_state()
    except Exception as e:  # noqa
        logging.error(f'Could not retrieve application state. {str(e)}', exc_info=False)
    else:
        try:
            response = await client.post(STATE_URL, json={'state': state})
            data = await response.json()
            logging.info(f'Response to state report: status_code={response.status_code} data={data}')
        except Exception as e:  # noqa
            logging.error(f'Could not report state {state} to the url {STATE_URL}: {str(e)}', exc_info=False)


async def report_state():
    logging.info('State reporting started...')
    async with httpx.AsyncClient() as client:
        try:
            while True:
                try:
                    while True:  # this double while makes it error proof...
                        await asyncio.create_task(send_state(client))
                        await asyncio.sleep(float(STATE_INTERVAL))
                except Exception as e:  # noqa
                    pass
        except KeyboardInterrupt:
            pass

    await redis_client.aclose()

    logging.info('State reporting shutdown...')


if __name__ == '__main__':
    asyncio.run(report_state())


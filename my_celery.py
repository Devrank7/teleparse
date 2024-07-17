import asyncio

from celery import Celery

from main1 import get_data_all

apps = Celery('my_project', broker='redis://localhost:6379/0')

apps.conf.update(
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
)


@apps.task
def get_all_data_async(**kwargs):
    number = kwargs['number']
    limit = kwargs['limit']
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(get_data_all(number=number, limit=limit))
    loop.close()
    return result

from celery import shared_task


@shared_task
def fillFromExternalRecords():
    pass

@shared_task()
def fillFixedValues():
    pass
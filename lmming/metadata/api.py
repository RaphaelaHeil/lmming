from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json

from metadata.models import Job, FacSpecificData


@csrf_exempt
def updateJobs(request):
    if request.method == 'POST':

        data = json.loads(request.body)

        for jobId in data.keys():
            job = Job.objects.filter(pk=jobId)
            if job:
                report = job.first().report
                if "volumeName" in data[jobId] and "volumeSignum" in data[jobId]:
                    if not hasattr(report, "facspecificdata"):
                        specific = FacSpecificData.objects.create(report=report)
                    else:
                        specific = report.facspecificdata
                    specific.seriesVolumeName = data[jobId]["volumeName"]
                    specific.seriesVolumeSignum = data[jobId]["volumeSignum"]
                    specific.save()
        return HttpResponse(status=204)
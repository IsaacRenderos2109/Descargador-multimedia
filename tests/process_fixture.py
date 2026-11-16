import os
import time

from video_downloader.models import Progress


def simulated_child(job, messages):
    if os.name != "nt":
        os.setsid()
    messages.put(("progress", Progress(percent=1)))
    if job.media.title == "wait":
        time.sleep(30)
    elif job.media.title == "crash":
        os._exit(3)
    else:
        messages.put(("success", "simulated.mp4"))

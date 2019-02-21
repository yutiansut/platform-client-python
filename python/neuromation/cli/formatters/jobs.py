import itertools
import time
from typing import Iterable

from click import style
from dateutil.parser import isoparse  # type: ignore

from neuromation.client import JobDescription, JobStatus, JobTelemetry, Resources

from .utils import truncate_string, wrap


BEFORE_PROGRESS = "\r"
AFTER_PROGRESS = "\n"
CLEAR_LINE_TAIL = "\033[0K"
LINE_UP = "\033[1F"

COLORS = {
    JobStatus.PENDING: "yellow",
    JobStatus.RUNNING: "blue",
    JobStatus.SUCCEEDED: "green",
    JobStatus.FAILED: "red",
    JobStatus.UNKNOWN: "yellow",
}


def format_job_status(status: JobStatus) -> str:
    return style(status.value, fg=COLORS.get(status, "reset"))


class JobFormatter:
    def __init__(self, quiet: bool = True) -> None:
        self._quiet = quiet

    def __call__(self, job: JobDescription) -> str:
        job_id = job.id
        if self._quiet:
            return job_id
        out = []
        out.append(
            style("Job ID", bold=True)
            + f": {job_id} "
            + style("Status", bold=True)
            + f": {format_job_status(job.status)}"
        )
        if job.http_url:
            out.append(style("Http URL", bold=True) + f": {job.http_url}")
        out.append(style("Shortcuts", bold=True) + ":")
        out.append(f"  neuro status {job.id}  " + style("# check job status", dim=True))
        out.append(
            f"  neuro logs {job.id}    " + style("# monitor job stdout", dim=True)
        )
        out.append(
            f"  neuro top {job.id}     "
            + style("# display real-time job telemetry", dim=True)
        )
        out.append(f"  neuro kill {job.id}    " + style("# kill job", dim=True))
        return "\n".join(out)


class JobStatusFormatter:
    def __call__(self, job_status: JobDescription) -> str:
        result: str = f"Job: {job_status.id}\n"
        result += f"Owner: {job_status.owner if job_status.owner else ''}\n"
        if job_status.description:
            result += f"Description: {job_status.description}\n"
        result += f"Status: {job_status.status}"
        if (
            job_status.history
            and job_status.history.reason
            and job_status.status in [JobStatus.FAILED, JobStatus.PENDING]
        ):
            result += f" ({job_status.history.reason})"
        result += f"\nImage: {job_status.container.image}\n"

        result += f"Command: {job_status.container.command}\n"
        resource_formatter = ResourcesFormatter()
        result += resource_formatter(job_status.container.resources) + "\n"
        result += f"Preemptible: {job_status.is_preemptible}\n"
        if job_status.internal_hostname:
            result += f"Internal Hostname: {job_status.internal_hostname}\n"
        if job_status.http_url:
            result = f"{result}Http URL: {job_status.http_url}\n"
        if job_status.container.env:
            result += f"Environment:\n"
            for key, value in job_status.container.env.items():
                result += f"{key}={value}\n"

        assert job_status.history
        result = f"{result}Created: {job_status.history.created_at}"
        if job_status.status in [
            JobStatus.RUNNING,
            JobStatus.FAILED,
            JobStatus.SUCCEEDED,
        ]:
            result += "\n" f"Started: {job_status.history.started_at}"
        if job_status.status in [JobStatus.FAILED, JobStatus.SUCCEEDED]:
            result += "\n" f"Finished: {job_status.history.finished_at}"
        if job_status.status == JobStatus.FAILED:
            result += "\n===Description===\n"
            result += f"{job_status.history.description}\n================="
        return result


class JobTelemetryFormatter:
    def __init__(self) -> None:
        self.col_len = {
            "timestamp": 24,
            "cpu": 15,
            "memory": 15,
            "gpu": 15,
            "gpu_memory": 15,
        }

    def _format_timestamp(self, timestamp: float) -> str:
        # NOTE: ctime returns time wrt timezone
        return str(time.ctime(timestamp))

    def header(self) -> str:
        return "\t".join(
            [
                "TIMESTAMP".ljust(self.col_len["timestamp"]),
                "CPU".ljust(self.col_len["cpu"]),
                "MEMORY (MB)".ljust(self.col_len["memory"]),
                "GPU (%)".ljust(self.col_len["gpu"]),
                "GPU_MEMORY (MB)".ljust(self.col_len["gpu_memory"]),
            ]
        )

    def __call__(self, info: JobTelemetry) -> str:
        timestamp = self._format_timestamp(info.timestamp)
        cpu = f"{info.cpu:.3f}"
        mem = f"{info.memory:.3f}"
        gpu = f"{info.gpu_duty_cycle}" if info.gpu_duty_cycle else "0"
        gpu_mem = f"{info.gpu_memory:.3f}" if info.gpu_memory else "0"
        return "\t".join(
            [
                timestamp.ljust(self.col_len["timestamp"]),
                cpu.ljust(self.col_len["cpu"]),
                mem.ljust(self.col_len["memory"]),
                gpu.ljust(self.col_len["gpu"]),
                gpu_mem.ljust(self.col_len["gpu_memory"]),
            ]
        )


class JobListFormatter:
    def __init__(self, quiet: bool = False):
        self.quiet = quiet
        self.tab = "\t"
        self.column_lengths = {
            "id": 40,
            "status": 10,
            "image": 15,
            "description": 50,
            "command": 50,
        }

    def __call__(self, jobs: Iterable[JobDescription], description: str = "") -> str:
        if description:
            jobs = [j for j in jobs if j.description == description]

        jobs = sorted(jobs, key=lambda j: isoparse(j.history.created_at))
        lines = list()
        if not self.quiet:
            lines.append(self._format_header_line())
        lines.extend(map(self._format_job_line, jobs))
        return "\n".join(lines)

    def _format_header_line(self) -> str:
        return self.tab.join(
            [
                "ID".ljust(self.column_lengths["id"]),
                "STATUS".ljust(self.column_lengths["status"]),
                "IMAGE".ljust(self.column_lengths["image"]),
                "DESCRIPTION".ljust(self.column_lengths["description"]),
                "COMMAND".ljust(self.column_lengths["command"]),
            ]
        )

    def _format_job_line(self, job: JobDescription) -> str:
        def truncate_then_wrap(value: str, key: str) -> str:
            return wrap(truncate_string(value, self.column_lengths[key]))

        if self.quiet:
            return job.id.ljust(self.column_lengths["id"])

        description = truncate_then_wrap(job.description or "", "description")
        command = truncate_then_wrap(job.container.command or "", "command")
        return self.tab.join(
            [
                job.id.ljust(self.column_lengths["id"]),
                job.status.ljust(self.column_lengths["status"]),
                job.container.image.ljust(self.column_lengths["image"]),
                description.ljust(self.column_lengths["description"]),
                command.ljust(self.column_lengths["command"]),
            ]
        )


class ResourcesFormatter:
    def __call__(self, resources: Resources) -> str:
        lines = list()
        lines.append(f"Memory: {resources.memory_mb} MB")
        lines.append(f"CPU: {resources.cpu:0.1f}")
        if resources.gpu:
            lines.append(f"GPU: {resources.gpu:0.1f} x {resources.gpu_model}")

        additional = list()
        if resources.shm:
            additional.append("Extended SHM space")

        if additional:
            lines.append(f'Additional: {",".join(additional)}')

        indent = "  "
        return "Resources:\n" + indent + f"\n{indent}".join(lines)


class JobStartProgress:
    SPINNER = ("◢", "◣", "◤", "◥")
    LINE_PRE = BEFORE_PROGRESS + "\r" + style("Status", bold=True) + ": "

    def __init__(self, color: bool) -> None:
        self._color = color
        self._time = time.time()
        self._spinner = itertools.cycle(self.SPINNER)
        self._prev = ""
        self._prev_reason = ""

    def __call__(self, job: JobDescription, *, finish: bool = False) -> str:
        if not self._color:
            return ""
        new_time = time.time()
        dt = new_time - self._time
        msg = format_job_status(job.status)
        if job.history.reason:
            reason = job.history.reason
            self._prev_reason = reason
        elif not self._prev_reason:
            reason = "Initializing"
        else:
            reason = ""
        if reason:
            msg += " " + style(reason, bold=True)
        if self._prev:
            ret = LINE_UP
        else:
            ret = ""
        # ret = LINE_UP
        # ret = ""
        if msg != self._prev:
            if self._prev:
                ret += self.LINE_PRE + self._prev + CLEAR_LINE_TAIL + "\n"
            self._prev = msg
        ret += self.LINE_PRE + msg + f" [{dt:.1f} sec]"
        if not finish:
            ret += " " + next(self._spinner)
        ret += CLEAR_LINE_TAIL + "\n"
        if finish:
            ret += AFTER_PROGRESS
        return ret
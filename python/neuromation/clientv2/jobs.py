from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from yarl import URL

from neuromation.client.jobs import (
    Image,
    JobStatus,
    NetworkPortForwarding,
    Resources,
    VolumeDescriptionPayload,
    network_to_api,
)
from neuromation.client.requests import ContainerPayload, ResourcesPayload
from neuromation.strings import parse

from .api import API


@dataclass(frozen=True)
class JobStatusHistory:
    status: JobStatus
    reason: str
    description: str
    created_at: str
    started_at: str
    finished_at: str


@dataclass(frozen=True)
class JobDescription:
    status: JobStatus
    id: str
    image: Optional[str] = None
    command: Optional[str] = None
    url: URL = URL()
    ssh: URL = URL()
    owner: Optional[str] = None
    history: Optional[JobStatusHistory] = None
    resources: Optional[Resources] = None
    description: Optional[str] = None
    is_preemptible: bool = True

    def jump_host(self) -> str:
        ssh_hostname = self.ssh.hostname
        ssh_hostname = ".".join(ssh_hostname.split(".")[1:])
        return ssh_hostname


class Jobs:
    def __init__(self, api: API) -> None:
        self._api = api

    async def submit(
        self,
        *,
        image: Image,
        resources: Resources,
        network: NetworkPortForwarding,
        volumes: Optional[List[VolumeDescriptionPayload]],
        description: Optional[str],
        is_preemptible: bool = False,
    ) -> JobDescription:
        http, ssh = network_to_api(network)
        resources_payload: ResourcesPayload = ResourcesPayload(
            memory_mb=parse.to_megabytes_str(resources.memory),
            cpu=resources.cpu,
            gpu=resources.gpu,
            gpu_model=resources.gpu_model,
            shm=resources.shm,
        )
        container = ContainerPayload(
            image=image.image,
            command=image.command,
            http=http,
            ssh=ssh,
            resources=resources_payload,
        )

        url = URL("jobs")
        request_details: Dict[str, Any] = {"container": container.to_primitive()}
        if volumes:
            prim_volumes = [v.to_primitive() for v in volumes]
        else:
            prim_volumes = []
        request_details["container"]["volumes"] = prim_volumes
        if description:
            request_details["description"] = description
        if is_preemptible is not None:
            request_details["is_preemptible"] = is_preemptible
        async with self._api.request("POST", url, json=request_details) as resp:
            res = await resp.json()
            return self._dict_to_description(res)

    async def list(self) -> List[JobDescription]:
        raise NotImplementedError

    async def kill(self, id: str) -> str:
        """
        the method returns None when the server has responded
        with HTTPNoContent in case of successful job deletion,
        and the text response otherwise (possibly empty).
        """
        url = URL(f"jobs/{id}")
        async with self._api.request("DELETE", url):
            # an error is raised for status >= 400
            return None  # 201 status code

    async def monitor(
        self, id: str
    ) -> Any:  # real type is async generator with data chunks
        url = URL(f"jobs/{id}/log")
        async with self._api.request(
            "GET", url, headers={"Accept-Encoding": "identity"}
        ) as resp:
            async for data in resp.content.iter_any():
                yield data

    async def status(self, id: str) -> JobDescription:
        url = URL(f"jobs/{id}")
        async with self._api.request("GET", url) as resp:
            ret = await resp.json()
            return self._dict_to_description_with_history(ret)

    def _dict_to_description_with_history(self, res: Dict[str, Any]) -> JobDescription:
        job_description = self._dict_to_description(res)
        job_history = None
        if "history" in res:
            job_history = JobStatusHistory(
                status=JobStatus(res["history"].get("status", "unknown")),
                reason=res["history"].get("reason", ""),
                description=res["history"].get("description", ""),
                created_at=res["history"].get("created_at", ""),
                started_at=res["history"].get("started_at", ""),
                finished_at=res["history"].get("finished_at", ""),
            )
        return JobDescription(
            id=job_description.id,
            status=job_description.status,
            image=job_description.image,
            command=job_description.command,
            history=job_history,
            resources=job_description.resources,
            url=job_description.url,
            ssh=job_description.ssh,
            owner=job_description.owner,
            description=job_description.description,
            is_preemptible=job_description.is_preemptible,
        )

    def _dict_to_description(self, res: Dict[str, Any]) -> JobDescription:
        job_container_image = None
        job_command = None
        job_resources = None

        if "container" in res:
            job_container_image = res["container"].get("image", None)
            job_command = res["container"].get("command", None)

            if "resources" in res["container"]:
                container_resources = res["container"]["resources"]
                shm = container_resources.get("shm", None)
                gpu = container_resources.get("gpu", None)
                gpu_model = container_resources.get("gpu_model", None)
                job_resources = Resources(
                    cpu=container_resources["cpu"],
                    memory=container_resources["memory_mb"],
                    gpu=gpu,
                    shm=shm,
                    gpu_model=gpu_model,
                )
        http_url = URL(res.get("http_url", ""))
        ssh_conn = URL(res.get("ssh_server", ""))
        description = res.get("description")
        job_owner = res.get("owner", None)
        return JobDescription(
            id=res["id"],
            status=JobStatus(res["status"]),
            image=job_container_image,
            command=job_command,
            resources=job_resources,
            url=http_url,
            ssh=ssh_conn,
            owner=job_owner,
            description=description,
            is_preemptible=res["is_preemptible"],
        )
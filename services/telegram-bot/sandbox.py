import asyncio
import logging
import secrets
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SandboxImage(Enum):
    ALPINE = "alpine:latest"
    BLACKARCH = "blackarchlinux/blackarch:latest"


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: int
    timed_out: bool
    error: Optional[str] = None


class DockerSandbox:
    def __init__(
        self,
        max_concurrent: int = 5,
        default_timeout: int = 60,
        max_memory: str = "256m",
        max_cpus: str = "0.5",
        max_pids: int = 100
    ):
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.max_memory = max_memory
        self.max_cpus = max_cpus
        self.max_pids = max_pids
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._images_pulled = set()

    async def pull_images(self):
        for image in SandboxImage:
            try:
                logger.info(f"Pulling Docker image: {image.value}")
                process = await asyncio.create_subprocess_exec(
                    "docker", "pull", image.value,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                if process.returncode == 0:
                    self._images_pulled.add(image.value)
                    logger.info(f"Successfully pulled: {image.value}")
                else:
                    logger.warning(f"Failed to pull {image.value}, will try on first use")
            except Exception as e:
                logger.error(f"Error pulling {image.value}: {e}")

    async def execute(
        self,
        command: str,
        image: SandboxImage = SandboxImage.ALPINE,
        timeout: Optional[int] = None,
        enable_network: bool = False,
        working_dir: str = "/workspace"
    ) -> SandboxResult:
        timeout = timeout or self.default_timeout
        start_time = time.time()
        container_name = f"d1337-sandbox-{secrets.token_hex(8)}"
        
        docker_args = [
            "docker", "run",
            "--rm",
            "--name", container_name,
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--tmpfs", f"{working_dir}:rw,noexec,nosuid,size=32m",
            "--memory", self.max_memory,
            "--cpus", self.max_cpus,
            "--pids-limit", str(self.max_pids),
            "--user", "1000:1000",
            "--workdir", working_dir,
        ]
        
        if not enable_network:
            docker_args.extend(["--network", "none"])
        
        docker_args.extend([
            image.value,
            "/bin/sh", "-c", command
        ])
        
        async with self._semaphore:
            try:
                process = await asyncio.create_subprocess_exec(
                    *docker_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    
                    return SandboxResult(
                        stdout=stdout.decode("utf-8", errors="replace"),
                        stderr=stderr.decode("utf-8", errors="replace"),
                        exit_code=process.returncode,
                        execution_time_ms=execution_time_ms,
                        timed_out=False
                    )
                    
                except asyncio.TimeoutError:
                    await self._kill_container(container_name)
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    
                    return SandboxResult(
                        stdout="",
                        stderr=f"Command timed out after {timeout} seconds",
                        exit_code=-1,
                        execution_time_ms=execution_time_ms,
                        timed_out=True
                    )
                    
            except Exception as e:
                execution_time_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Sandbox execution error: {e}")
                
                return SandboxResult(
                    stdout="",
                    stderr="",
                    exit_code=-1,
                    execution_time_ms=execution_time_ms,
                    timed_out=False,
                    error=str(e)
                )

    async def _kill_container(self, container_name: str):
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "kill", container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await process.wait()
        except Exception as e:
            logger.error(f"Failed to kill container {container_name}: {e}")

    async def check_docker_available(self) -> bool:
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await process.wait()
            return process.returncode == 0
        except Exception:
            return False


sandbox = DockerSandbox()

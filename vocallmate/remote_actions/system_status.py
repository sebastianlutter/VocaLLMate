import asyncio
import asyncssh
import aiohttp
import socket
import time
import yaml

from typing import Optional, Dict, Any
from vocallmate.stt.stt_whisper_remote import SpeechToTextWhisperRemote
from vocallmate.tts.tts_openedai_speech import TextToSpeechOpenedaiSpeech
from vocallmate.vocallmate_factory import VocaLLMateFactory


class SystemStatus:
    """
    A class to perform system status checks such as HTTP requests, SSH command execution,
    ping, and wake-on-lan operations. It also aggregates status information for:

      - Mandatory endpoints (STT, TTS, LLM)
      - Optional checks (HTTP/SSH), each defined in a YAML config file

    If an optional check has a 'wake_if_down' MAC address set, this class will attempt
    to send a Wake-on-LAN packet to that MAC when the check fails, wait up to 30 seconds
    (checking every 5 seconds), and retry that check once. If it remains unavailable,
    the check is marked as failed.
    """

    def __init__(self, factory: VocaLLMateFactory, config_file: Optional[str] = None):
        """
        :param factory: A VocaLLMateFactory instance that provides STT, TTS, and LLM providers.
        :param config_file: Path to a YAML file defining optional checks (optional).
        """
        is_stt_whisper = isinstance(factory.stt_provider, SpeechToTextWhisperRemote)
        is_tts_openedai = isinstance(factory.tts_provider, TextToSpeechOpenedaiSpeech)

        # Determine which endpoints are actually set, otherwise None
        # (Note the user-specified swap between STT and TTS endpoints)
        self.http_endpoints = {
            'STT': factory.tts_provider.tts_endpoint if is_stt_whisper else None,
            'TTS': factory.stt_provider.stt_endpoint if is_tts_openedai else None,
            'LLM': factory.llm_provider.llm_endpoint,
        }

        # Load optional checks from YAML if provided
        self.optional_services = []
        if config_file:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
            self.optional_services = config_data.get("optional_services", [])

    async def get_status(self) -> Dict[str, Any]:
        """
        Gathers status information for mandatory HTTP endpoints plus any optional checks
        in parallel, then returns a Python dict with the results. A global 'report' key
        is added to summarize overall availability of mandatory services (STT, TTS, LLM),
        the status of optional services, and the total runtime to fetch the status.

        If an optional check has a 'wake_if_down' MAC address configured, a Wake-on-LAN
        packet is sent if that check fails, followed by a retry after up to 30s of waiting.
        """
        return await self._get_status_async()

    def get_status_spoken(self, data: Dict[str, Any]) -> str:
        """
        Uses get_status internally, but transforms the output into a short human-readable
        string suitable for text-to-speech.

        - Reports if all mandatory services are running, or which are missing.
        - For optional checks, only mentions if there are any, and whether all are up or some are down.
        """
        report = data.get("report", {})

        all_mandatory = report.get("all_mandatory_available", False)
        missing_mandatory = report.get("missing_mandatory_services", [])
        optional_up = report.get("optional_services_up", [])
        optional_down = report.get("optional_services_down", [])

        # Build a simple spoken response
        parts = []

        if all_mandatory:
            parts.append("Alle Hauptfunktionen sind erreichbar.")
        else:
            missing_list = ", ".join(missing_mandatory)
            parts.append(f"Folgende Hauptfunktionen sind nicht erreichbar: {missing_list}.")

        # Check if we have optional checks at all
        # DISABLE FOR NOW
        if False:
            if optional_up or optional_down:
                if not optional_down:
                    parts.append("Alle sonstigen Dienste sind erreichbar.")
                else:
                    down_list = ", ".join(optional_down)
                    if len(optional_down) == 1:
                        parts.append(f"Ein optionaler Dienst ist nicht erreichbar: {down_list}.")
                    else:
                        parts.append(f"{len(optional_down)} optionale Dienste sind nicht erreichbar: {down_list}.")
            else:
                parts.append("Es wurden keine sonstigen Dienste konfiguriert.")

        return " ".join(parts)

    async def _get_status_async(self) -> Dict[str, Any]:
        """
        Async method that collects all status data in parallel and returns it as a dictionary.
        A global 'report' key is added to summarize mandatory services, optional checks,
        and the total runtime to gather the status.
        """
        start_time = time.time()
        tasks = []

        # Collect tasks for mandatory checks
        for name, url in self.http_endpoints.items():
            # No WOL for mandatory endpoints, so we pass None
            tasks.append(
                asyncio.create_task(
                    self._check_with_wake(
                        check_type="http",
                        name=name,
                        url=url,
                        wake_mac=None
                    )
                )
            )

        # Collect tasks for optional checks
        for check in self.optional_services:
            ctype = check.get("type")
            name = check.get("name", "Unnamed")
            wake_mac = check.get("wake_if_down")  # May be None if not specified

            if ctype == "ssh":
                tasks.append(
                    asyncio.create_task(
                        self._check_with_wake(
                            check_type="ssh",
                            name=name,
                            host=check.get("host"),
                            user=check.get("user"),
                            wake_mac=wake_mac
                        )
                    )
                )
            elif ctype == "http":
                tasks.append(
                    asyncio.create_task(
                        self._check_with_wake(
                            check_type="http",
                            name=name,
                            url=check.get("endpoint"),
                            wake_mac=wake_mac
                        )
                    )
                )
            else:
                # Unknown check type
                tasks.append(
                    asyncio.create_task(
                        self._check_unknown(name, ctype)
                    )
                )

        results = await asyncio.gather(*tasks)

        # Combine results into a dictionary
        status_dict = {}
        for item in results:
            status_dict[item["name"]] = item

        # Build a global report for mandatory and other services
        mandatories = ["STT", "TTS", "LLM"]
        missing = []
        optional_up = []
        optional_down = []

        for item in results:
            name = item["name"]
            if name in mandatories:
                if not item["available"]:
                    missing.append(name)
            else:
                if item["available"]:
                    optional_up.append(name)
                else:
                    optional_down.append(name)

        end_time = time.time()
        runtime_seconds = end_time - start_time

        report = {
            "all_mandatory_available": len(missing) == 0,
            "missing_mandatory_services": missing,
            "optional_services_up": optional_up,
            "optional_services_down": optional_down,
            "runtime_seconds": runtime_seconds
        }

        # Attach the report to the final dictionary
        status_dict["report"] = report
        return status_dict

    async def _check_with_wake(
            self,
            check_type: str,
            name: str,
            wake_mac: Optional[str] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Wraps the actual check (SSH or HTTP). If 'wake_mac' is provided and the first
        check fails, sends a WOL packet, waits up to 30 seconds (5-second intervals),
        and retries once. If it remains unavailable, the check is marked as failed.

        :param check_type: 'ssh' or 'http'
        :param name: Name of the service
        :param wake_mac: Optional MAC address to WOL if check fails
        :param kwargs: Additional params (e.g. host, user, url)
        """
        # Perform the initial check
        result = await self._perform_check(check_type, name, **kwargs)

        if result["available"]:
            return result

        # If it's not available and we have a MAC to wake, do so and retry
        if wake_mac and check_type in ["ssh", "http"]:
            # Send WOL
            try:
                await self.wake_on_lan(wake_mac)
            except Exception as e:
                # If WOL fails for some reason, record the error
                result["wake_on_lan_error"] = str(e)
                return result

            # Wait up to 30 seconds, checking in intervals of 5 seconds
            deadline = time.time() + 30
            while time.time() < deadline:
                await asyncio.sleep(5)
                second_attempt = await self._perform_check(check_type, name, **kwargs)
                if second_attempt["available"]:
                    return second_attempt

            # If still not available, mark WOL as attempted
            result["wake_on_lan_attempted"] = True

        return result

    async def _perform_check(
            self,
            check_type: str,
            name: str,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Dispatches to the right check function (SSH or HTTP or unknown).
        """
        if check_type == "ssh":
            host = kwargs.get("host")
            user = kwargs.get("user")
            return await self._check_ssh(name, host, user)
        elif check_type == "http":
            url = kwargs.get("url")
            return await self._check_http_endpoint(name, url)
        else:
            return await self._check_unknown(name, check_type)

    @staticmethod
    async def _check_http_endpoint(name: str, url: Optional[str]) -> Dict[str, Any]:
        """
        Helper to check an HTTP endpoint by calling test_endpoint. If `url` is None,
        mark the endpoint as unavailable.
        """
        if not url:
            return {
                "name": name,
                "type": "http",
                "endpoint": None,
                "available": False
            }
        try:
            res = await SystemStatus.test_endpoint(url)
            # Considering HTTP responses <500 as "available"
            available = (200 <= res["status"] < 500)
            return {
                "name": name,
                "type": "http",
                "endpoint": url,
                "status_code": res["status"],
                "body": res["body"],
                "available": available
            }
        except Exception as e:
            return {
                "name": name,
                "type": "http",
                "endpoint": url,
                "error": str(e),
                "available": False
            }

    @staticmethod
    async def _check_ssh(name: str, host: Optional[str], username: Optional[str]) -> Dict[str, Any]:
        """
        Helper to check an SSH server by connecting (with known_hosts=None) and running
        a trivial command. If connection fails, mark as unavailable.
        """
        if not host or not username:
            return {
                "name": name,
                "type": "ssh",
                "host": host,
                "username": username,
                "error": "No host/user specified",
                "available": False
            }
        try:
            async with asyncssh.connect(
                    host=host,
                    username=username,
                    known_hosts=None
            ) as conn:
                # Simple test command
                result = await conn.run("echo SSH_OK")
                available = (result.exit_status == 0)
                return {
                    "name": name,
                    "type": "ssh",
                    "host": host,
                    "username": username,
                    "stdout": result.stdout.strip(),
                    "returncode": result.exit_status,
                    "available": available
                }
        except Exception as e:
            return {
                "name": name,
                "type": "ssh",
                "host": host,
                "username": username,
                "error": str(e),
                "available": False
            }

    @staticmethod
    async def _check_unknown(name: str, check_type: str) -> Dict[str, Any]:
        """
        Helper to handle unknown check types.
        """
        return {
            "name": name,
            "type": check_type,
            "available": False,
            "error": f"Unknown check type: {check_type}"
        }

    @staticmethod
    async def test_endpoint(
            url: str,
            method: str = "GET",
            data: Dict[str, Any] = None,
            headers: Dict[str, str] = None,
            timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Test an HTTP endpoint using GET or POST, returning the response status and body.
        """
        if headers is None:
            headers = {}

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            if method.upper() == "POST":
                async with session.post(url, json=data, headers=headers) as response:
                    return {
                        "status": response.status,
                        "body": await response.text()
                    }
            else:
                async with session.get(url, headers=headers) as response:
                    return {
                        "status": response.status,
                        "body": await response.text()
                    }

    @staticmethod
    async def execute_ssh_command(
            host: str,
            username: str,
            password: str,
            command: str,
            port: int = 22
    ) -> Dict[str, Any]:
        """
        Execute a command on a remote host via SSH, returning stdout and return code.
        """
        try:
            async with asyncssh.connect(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    known_hosts=None
            ) as conn:
                result = await conn.run(command)
                return {
                    "stdout": result.stdout,
                    "returncode": result.exit_status
                }
        except Exception as e:
            return {
                "error": str(e),
                "stdout": "",
                "returncode": -1
            }

    @staticmethod
    async def ping(
            target: str,
            count: int = 1,
            wait_until_alive: bool = False,
            timeout: int = 5
    ) -> bool:
        """
        Ping a host or IP to check if it is alive. Optionally wait until it responds.
        """
        cmd = ["ping", "-c", str(count), "-W", str(timeout), target]

        while True:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, _ = await process.communicate()

            if process.returncode == 0:
                return True

            if not wait_until_alive:
                return False

            await asyncio.sleep(1)

    @staticmethod
    async def wake_on_lan(mac_address: str, broadcast: str = "<broadcast>", port: int = 9):
        """
        Send a Wake-on-LAN (WOL) magic packet to a given MAC address.
        """
        mac_address_clean = mac_address.replace(":", "").replace("-", "").lower()
        if len(mac_address_clean) != 12:
            raise ValueError("Invalid MAC address format.")

        # Construct magic packet
        magic_packet = b'\xff' * 6 + bytes.fromhex(mac_address_clean) * 16

        # Send packet
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(magic_packet, (broadcast, port))

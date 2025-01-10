import yaml
import asyncio
from typing import Dict, Any, List, Optional, Union

from vocallmate.remote_actions.system_status import SystemStatus


# We assume your SystemStatus class is already defined somewhere else and imported here:
# from your_module import SystemStatus


class ActionsOrchestrator:
    """
    A manager that reads the same YAML used by SystemStatus (optional_actions.yaml),
    extracts the servers (targets) and their actions, and provides a higher-level
    API to list and execute those actions.
    """

    def __init__(self, config_file: str, system_status: SystemStatus) -> None:
        """
        :param config_file: Path to the YAML file (the same file that contains 'optional_services'
                            with servers and their actions).
        :param system_status: An instance of the SystemStatus class for connectivity.
        """
        self.system_status = system_status
        self.servers = []  # Will hold the parsed servers from optional_services
        self._load_config(config_file)

    def _load_config(self, config_file: str):
        """
        Internal method to parse the YAML file and store it in self.servers.
        Each entry in 'self.servers' should have:
          - name
          - type (ssh or http)
          - host / user / endpoint / wake_if_down
          - actions: list of action definitions
        """
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}

        # We only focus on 'optional_services' here:
        self.servers = config_data.get("optional_services", [])

    def list_targets(self) -> List[str]:
        """
        Return a list of server (target) names, e.g. ["steamdeck", "raspberry", "external-api"].
        """
        return [server["name"] for server in self.servers]

    def list_actions(self, target_name: str) -> List[str]:
        """
        Given the name of a target (server), return a list of available action names.
        """
        server = self._find_server(target_name)
        if not server:
            return []
        if "actions" not in server:
            return []
        return [action["name"] for action in server["actions"]]

    async def run_action(
        self,
        target_name: str,
        action_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Run the given action on the given target (server) with the provided parameters.

        Steps:
        - Finds the server and action definition
        - Gathers required parameters (either from 'parameters' argument or prompts user, if desired)
        - Executes the 'check' step (if it fails, we skip the action)
        - Executes the 'init' step
        - Executes the 'run' step
        - Returns True if run was successful, otherwise False
        """
        if parameters is None:
            parameters = {}

        # 1) Find the server definition
        server = self._find_server(target_name)
        if not server:
            raise ValueError(f"Server '{target_name}' not found.")

        # 2) Find the action definition
        action = self._find_action(server, action_name)
        if not action:
            raise ValueError(f"Action '{action_name}' not found for server '{target_name}'.")

        # 3) Resolve/collect parameters for this action
        if "parameters" in action and isinstance(action["parameters"], list):
            # Fill missing parameters from user input or some default mechanism
            for param_def in action["parameters"]:
                param_name = param_def["name"]
                if param_name not in parameters:
                    # In a real scenario, prompt user or supply default
                    # For example:
                    # parameters[param_name] = input(f"Enter value for {param_name}: ")
                    # For now, we'll just set an empty or default
                    parameters[param_name] = None

        # 4) Execute the chain: check -> init -> run
        #    We'll treat them similarly, always going in the same order.

        # 4.1) CHECK step
        if not await self._execute_step(server, action.get("check"), parameters):
            print(f"Action '{action_name}' failed its check step. Skipping init/run.")
            return False

        # 4.2) INIT step (optional)
        init_step = action.get("init")
        if init_step:
            init_ok = await self._execute_step(server, init_step, parameters)
            if not init_ok:
                print(f"Action '{action_name}' init step failed. Skipping run.")
                return False

        # 4.3) RUN step
        run_step = action.get("run")
        if not run_step:
            print(f"Action '{action_name}' has no 'run' step defined.")
            return False

        run_ok = await self._execute_step(server, run_step, parameters)
        if run_ok:
            print(f"Action '{action_name}' completed successfully on '{target_name}'.")
        else:
            print(f"Action '{action_name}' run step failed on '{target_name}'.")
        return run_ok

    async def _execute_step(self, server: Dict[str, Any], step: Dict[str, Any], parameters: Dict[str, Any]) -> bool:
        """
        Internal method that uses SystemStatus to execute either an SSH command or HTTP endpoint,
        substituting any needed parameters. This method is used for check/init/run steps.

        :param server: The server dict (host, user, type, etc.)
        :param step: The step dict (method: ssh/http, command, endpoint, etc.)
        :param parameters: The filled-out parameter dictionary
        :return: True if step completed successfully, else False
        """
        if not step:
            # Step might not exist, consider that "success" or skip
            return True

        method = step.get("method")
        if method == "ssh":
            # Build/fill the command
            command_template = step.get("command", "")
            command_str = self._substitute_params(command_template, parameters)

            # We can call system_status.execute_ssh_command (if we have credentials)
            host = server.get("host")
            user = server.get("user")
            # password could come from somewhere else if needed
            password = None

            # Actually run it
            result = await self.system_status.execute_ssh_command(
                host=host,
                username=user,
                password=password,
                command=command_str
            )
            # Decide success/failure
            return result["returncode"] == 0

        elif method == "http":
            # Build/fill the endpoint
            endpoint_template = step.get("endpoint", "")
            endpoint_str = self._substitute_params(endpoint_template, parameters)

            # Optional data for POST, or we can parse further
            # For now, we assume GET only
            result = await self.system_status.test_endpoint(endpoint_str)
            # Decide success/failure
            return 200 <= result["status"] < 500

        else:
            print(f"Unknown or missing method for step: {step}")
            return False

    def _substitute_params(self, template: str, parameters: Dict[str, Any]) -> str:
        """
        Very simple parameter substitution method. In practice, you might want to
        parse placeholders like {param} in the command/endpoint, etc.
        For example, a command could be: "echo {game_path} {additional_option}"
        """
        cmd = template
        for key, value in parameters.items():
            if value is None:
                value = ""  # or raise an error if required
            placeholder = f"{{{key}}}"
            cmd = cmd.replace(placeholder, str(value))
        return cmd

    def _find_server(self, target_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a server dict by its 'name'.
        """
        for srv in self.servers:
            if srv.get("name") == target_name:
                return srv
        return None

    def _find_action(self, server: Dict[str, Any], action_name: str) -> Optional[Dict[str, Any]]:
        """
        Find an action in a given server's 'actions' list by action name.
        """
        for act in server.get("actions", []):
            if act.get("name") == action_name:
                return act
        return None



# system
import logging
import subprocess

# local
from ..subcommand import ServiceCommand
from ..config import LoadedConfig


def _service_has_executable(project, service, exe_name):
    """
    Test if service in project has an executable exe_name in its PATH.
    Requires /bin/sh.
    """

    try:
        # test if desired shell exists
        project.compose_run(
            ['exec', service, '/bin/sh', '-c', f"command -v {exe_name}"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True

    except subprocess.CalledProcessError as e:
        # fallback
        return False


def _find_shell(args, project, service):
    """find first working shell (provided by config and args) in service in project"""

    # builtin shells: as a last resort, fallback to '/bin/sh' and 'sh'
    shells = ['/bin/sh', 'sh']

    # load favorite shells from config
    config = LoadedConfig.get()
    if config['runtime:shells']:
        shells = [*config['runtime:shells'], *shells]

    # consider shell from args
    if args.shell:
        shells = [args.shell, *shells]

    logging.debug(f"Shells priority: {shells}")

    # actually try shells
    for i, shell in enumerate(shells):
        if _service_has_executable(project, service, shell):
            # found working shell
            logging.debug(f"Using shell '{shell}'")
            return shell

        elif i + 1 < len(shells):
            # try next in list
            logging.info(f"Shell '{shell}' not found in container, trying '{shells[i+1]}'")

        elif args.shell:
            # not found, user suggestion provided
            logging.warning(f"Could not find any working shell in this container. "
                            f"Launching provided '{args.shell}' nevertheless. "
                            f"Don't get mad if this fails!")
            return args.shell

        else:
            # not found, search exhausted
            logging.error(f"Could not find any working shell among '{shells}' in this container. "
                          f"Please suggest a shell using the '-s SHELL' command line option!")
            return None


class ShellCommand(ServiceCommand):
    """kiwi shell"""

    def __init__(self):
        super().__init__(
            'shell', num_projects=1, num_services=1,
            action="Spawning shell in",
            description="Spawn shell inside a project's service"
        )

        # -s argument: Select shell
        self._sub_parser.add_argument(
            '-s', '--shell', type=str,
            help="shell to spawn"
        )

        # -u argument: Run as user
        self._sub_parser.add_argument(
            '-u', '--user', type=str,
            help="container user to run shell"
        )

    def _run_services(self, runner, args, project, services):
        service = services[0]
        shell = _find_shell(args, project, service)

        user_args = ['-u', args.user] if args.user else []

        if shell is not None:
            # spawn shell
            project.compose_run(['exec', *user_args, service, shell])
            return True

        return False

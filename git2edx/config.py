import os
import platform
import yaml
import logging
from logging.handlers import SysLogHandler

class G2EConfigException(Exception):
    """
    General exception for throwing git2edx-related configuration exceptions.
    """
    def __init__(self, message):
        super(G2EConfigException, self).__init__(
            "{0}\nPlease see the example file (git2edx.env.example.yml) "
            "for a detailed configuration walkthrough.".format(message)
        )

def get_config(yaml_config=None):
    """
    Loads, validates, and returns the git2edx configuration.

    Order of operations:
    1. Import the GIT2EDX_ settings from the environment.
    2. Try to find the YAML config from the environment variable or various
        default locations.
    2. For each configurable setting:
       a. If it exists, utilize the YAML setting (containing studio and course 
          repository configuration), taking precedence over any environment set
          variables.
       b. If there's no environment variable or configuration file setting
          available, set defaults and append a warning to the log when
          applicable.

    See the `git2edx.env.example.yml` file with this repository for detailed
    information about each configurable setting.
    """
    # Import the GIT2EDX_ settings from the environment
    config = {
        "yaml_config_location": os.environ.get("GIT2EDX_CONFIG_FILE"),
        "default_secret": os.environ.get("GIT2EDX_DEFAULT_SECRET"),
        "course_directory": os.environ.get("GIT2EDX_COURSE_DIR"),
        "studios": None,
        "courses": None,
    }
    # This studio config is used if no YAML config is found
    environ_studio_config = {
        "url": os.environ.get("GIT2EDX_STUDIO_URL"),
        "email": os.environ.get("GIT2EDX_STUDIO_EMAIL"),
        "password": os.environ.get("GIT2EDX_STUDIO_PASSWORD"),
        "default": True,
    }

    # If the parsed YAML config wasn't passed, try to find it from the
    # environment variable as well as default locations
    if not yaml_config:
        yaml_locations = [
            config["yaml_config_location"],
            os.path.join(os.getcwd(), "git2edx.env.yml"),
            os.path.join(os.path.expanduser('~'), ".git2edx.env.yml"),
            "/etc/git2edx.env.yml"
        ]
        for loc in yaml_locations:
            if loc:
                # Intentinally don't catch anything that implies a YAML error
                try:
                    yaml_config = yaml.load(open(loc))
                except IOError:
                    # The file probably doesn't exist; move on
                    pass
                else:
                    # A valid YAML file was parsed
                    break
    if yaml_config:
        config.update(yaml_config)

    config["default_studios"] = []

    # Validate studio configuration
    if not config["studios"]:
        config["studios"] = {}
        # Set up a studio configuration named "ENVIRON_VARS" if using
        # environment variables
        if environ_studio_config["email"] and environ_studio_config["password"]:
            config["studios"]["ENVIRON_VARS"] = environ_studio_config
        else:
            raise G2EConfigException(
                "Couldn't find any studio account configuration!"
            )
    for name, studio in config["studios"].items():
        if not studio["email"] or not studio["password"]:
            raise G2EConfigException(
                "The \"{0}\" studio configuration has no {1} entry!".format(
                    name,
                    "password" if studio["email"] else "email"
                )
            )

        # When no URL is supplied, assume the destination is studio.edx.org.
        if not studio["url"]:
            studio["url"] = "https://studio.edx.org"
        if studio["default"]:
            config["default_studios"].append(name)
    if not config["default_studios"]:
        if not config["courses"]:
            # This is because
            raise G2EConfigException(
                "Because there are no course configuration entries, at least "
                "one studio configuration must be marked as default!"
            )
        # TODO: Warn the user that, because no studios are marked as default,
        #       each course repo hooking git2edx must have it's own
        #       configuration entry.

    # TODO: Validate course configuration

    return config

def configure_logging(level_override=None):
    """
    Set the log level for the application.
    (Taken from gitreload log config)
    """

    # Set up format for default logging
    hostname = platform.node().split('.')[0]
    formatter = (
        '%(asctime)s %(levelname)s %(process)d [%(name)s] '
        '%(filename)s:%(lineno)d - '
        '{hostname}- %(message)s'
    ).format(hostname=hostname)
    set_level = level_override

    # Grab config from settings if set, else allow system/language
    # defaults.
    config_log_level = settings.get('LOG_LEVEL', None)
    config_log_int = None

    if config_log_level and not set_level:
        config_log_int = getattr(logging, config_log_level.upper(), None)
        if not isinstance(config_log_int, int):
            raise ValueError('Invalid log level: {0}'.format(config_log_level))
        set_level = config_log_int

    # Set to NotSet if we still aren't set yet
    if not set_level:
        set_level = config_log_int = logging.NOTSET

    # Setup logging with format and level (do setup incase we are
    # main, or change root logger if we aren't.
    logging.basicConfig(level=level_override, format=formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(set_level)

    address = None
    if os.path.exists('/dev/log'):
        address = '/dev/log'
    elif os.path.exists('/var/run/syslog'):
        address = '/var/run/syslog'
    else:
        address = ('127.0.0.1', 514)

    # Add syslog handler before adding formatters
    root_logger.addHandler(
        SysLogHandler(address=address, facility=SysLogHandler.LOG_LOCAL0)
    )

    for handler in root_logger.handlers:
        handler.setFormatter(logging.Formatter(formatter))

    return config_log_int

log = logging.getLogger('git2edx')

# TODO: Configure logging before loading config
# Load the configuration on import
settings = get_config()

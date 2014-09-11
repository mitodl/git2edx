import os
import yaml

class G2EConfigException(Exception):
    """
    General exception for throwing git2edx-related configuration exceptions.
    """
    def __init__(self, message):
        super(G2EConfigException, self).__init__(message)
        self.message = (
            "GIT2EDX CONFIGURATION ERROR: {0} Please see the example file "
            "(git2edx.env.example.yml) for a detailed configuration "
            "walkthrough.".format(message)
        )

def get_config():
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

    # Try to find the YAML config from the environment variable as well as
    # default locations
    yaml_config = None
    for loc in [config["yaml_config_location"],
                os.path.join(os.getcwd(), "git2edx.env.yml"),
                os.path.join(os.path.expanduser('~'), ".git2edx.env.yml"),
                "/etc/git2edx.env.yml"]:
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
        if environ_studio_config["email"] and environ_studio_config["password"]:
            config["studios"]['ENVIRON_VARS'] = environ_studio_config
        else:
            raise G2EConfigException(
                "Couldn't find any studio account configuration!"
            )
    for name, studio in config.studios.items():
        if not studio["email"] or not studio["password"]:
            raise G2EConfigException(
                "The \"{0}\" studio configuration has no {1} entry!".format(
                    name,
                    "password" if studio["email"] else "email"
                )
            )
        if not studio["url"]:
            studio["url"] = "https://studio.edx.org"
            # TODO: Append a warning to the logs
        if studio["default"]:
            config["default_studios"].append(name)
    if not config["default_studios"]:
        if not config["courses"]:
            # This is because
            raise G2EConfigException(
                "Because there are no course configuration entries, at least "
                "one studio configuration must be marked as default!"
            )
        # TODO: Append a warning to the logs noting that, because no studios
        #       are marked as default, each course repo hooking git2edx must
        #       have it's own configuration entry.

    # TODO: Validate course configuration

    return config

# TODO: Configure logging before loading config
# Load the configuration on import
settings = get_config()

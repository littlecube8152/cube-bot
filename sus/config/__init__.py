"""Handle configuration parameters."""
import json
from getpass import getpass
from sus.config.config import available_options

class ConfigHandler:
    def __init__(self):
        self.mapping = {}
        self.required = []
        self.loaders = []
        self.loaded = False

    def get_configuration(self, name: str):
        r"""
        Get a configuration value.

        :param name: Name for the config. For multi-layer, please use `.` as delimeter.
        """
        path = name.split('.')
        submapping = self.mapping
        for attr in path:
            submapping = submapping[attr]
        return submapping

    def after_load(self, func):
        if self.loaded:
            func()
        else:
            self.loaders.append(func)

    def load(self):
        """
        Load config, prompt missing config, and initalize all the registered loaders.
        """
        try:
            with open('config.json') as config_file:
                self.mapping = json.load(config_file)
        except (ValueError, FileNotFoundError):
            print("Failed to load config.json.")
            self.mapping = {}

        for i in range(len(available_options)):
            if len(available_options[i]) < 5:
                available_options[i].append({})
            
        for name, typename, default, external, options in available_options:
            path = name.split('.')

            submapping = self.mapping
            for attr in path[:-1]:
                if attr not in submapping:
                    submapping[attr] = {}
                submapping = submapping[attr]

            if path[-1] not in submapping:
                if default is None:
                    passed = False
                    while not passed:
                        if "secret" in options:
                            read = getpass(f"Confidential parameter {name}{f' ({external})' if external else ''} not found in config.json. Please enter the value: ")
                        else:
                            read = input(f"Parameter {name}{f' ({external})' if external else ''} not found in config.json. Please enter the value: ")
                        if "checker" not in options or options["checker"](typename(read)):
                            passed = True
                        else:
                            print("Checker failed. Please try again.")
                    submapping[path[-1]] = typename(read)
                else:
                    submapping[path[-1]] = default

        for loader in self.loaders:
            loader()
        self.loaded = True

config_handler = ConfigHandler()


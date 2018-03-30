import yaml


class RT09Config:

    @staticmethod
    def load_config():
        with open("config.yml") as config_file:
            return yaml.safe_load(config_file)

import yaml


def load_tests(path: str):
    with open(path, 'r') as f:
        return yaml.safe_load(f).get('tests')


def load_configs(path: str):
    with open(path, 'r') as f:
        return yaml.safe_load(f).get('configs')

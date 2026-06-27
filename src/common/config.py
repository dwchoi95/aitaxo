import yaml


class Config:
    def __init__(self, path="config.yaml"):
        with open(path) as f:
            self._d = yaml.safe_load(f)

    def __getitem__(self, key):
        return self._d[key]

    def get(self, key, default=None):
        return self._d.get(key, default)

    def as_dict(self):
        return self._d

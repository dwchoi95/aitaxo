import yaml


class Config:
    def __init__(self, path="config.yaml"):
        self._data = yaml.safe_load(open(path, encoding="utf-8"))

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

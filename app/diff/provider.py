import abc
import urllib.parse

from app.diff.models.diff import Diff


class IDiffProvider(abc.ABC):
    @abc.abstractmethod
    def domain(self) -> str:
        pass

    @abc.abstractmethod
    def get_diff(self, url: str) -> Diff:
        pass


class DiffProvider:
    _providers: dict[str, IDiffProvider]

    def __init__(self) -> None:
        self._providers = dict()

    def register_provider(self, provider: IDiffProvider) -> None:
        self._providers.update({provider.domain(): provider})

    def get_diff(self, url: str) -> Diff:
        parsed_url = urllib.parse.urlparse(url)

        provider = self._providers.get(parsed_url.netloc)
        if provider == None:
            raise Exception(f"No provider is registered for domain {parsed_url.netloc}")

        return provider.get_diff(url)

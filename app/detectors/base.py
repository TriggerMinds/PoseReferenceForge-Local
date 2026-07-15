from abc import ABC, abstractmethod
import numpy as np
from app.domain.models import Person, Pose2D


class PersonDetector(ABC):
    @abstractmethod
    def detect(self, image: np.ndarray) -> list[Person]:
        ...

    @abstractmethod
    def name(self) -> str:
        ...


class PoseDetector(ABC):
    @abstractmethod
    def detect(self, image: np.ndarray, person: Person) -> Pose2D:
        ...

    @abstractmethod
    def name(self) -> str:
        ...


class HandDetector(ABC):
    @abstractmethod
    def detect(self, image: np.ndarray, person: Person) -> dict[str, tuple[float, float, float]]:
        ...

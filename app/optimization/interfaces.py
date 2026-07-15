"""Replaceable interfaces for the 3D pose fitting pipeline."""
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np
from app.domain.models import Pose2D, Pose3D


class Pose3DInitializer(ABC):
    @abstractmethod
    def initialize(self, pose2d: Pose2D) -> Pose3D:
        ...

    @abstractmethod
    def name(self) -> str:
        ...


class PoseFitter(ABC):
    @abstractmethod
    def fit(
        self,
        pose2d: Pose2D,
        pose3d: Pose3D,
        camera_params: Optional[dict] = None,
    ) -> tuple[Pose3D, dict]:
        ...


class CameraOptimizer(ABC):
    @abstractmethod
    def estimate(
        self,
        pose2d: Pose2D,
        pose3d: Pose3D,
    ) -> dict:
        ...


class ReprojectionEvaluator(ABC):
    @abstractmethod
    def evaluate(
        self,
        pose2d: Pose2D,
        pose3d: Pose3D,
        camera_params: dict,
    ) -> dict:
        ...

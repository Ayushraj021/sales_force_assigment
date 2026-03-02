"""
Model Registry

Model versioning and management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import uuid
import pickle
import hashlib
import logging

logger = logging.getLogger(__name__)


class ModelStage(str, Enum):
    """Model deployment stages."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


@dataclass
class ModelMetadata:
    """Model metadata."""
    model_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: str = "1.0.0"
    model_type: str = ""
    framework: str = ""  # sklearn, pytorch, tensorflow, etc.
    stage: ModelStage = ModelStage.DEVELOPMENT
    metrics: Dict[str, float] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "version": self.version,
            "model_type": self.model_type,
            "framework": self.framework,
            "stage": self.stage.value,
            "metrics": self.metrics,
            "parameters": self.parameters,
            "tags": self.tags,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ModelVersion:
    """A specific version of a model."""
    metadata: ModelMetadata
    model_bytes: Optional[bytes] = None
    checksum: Optional[str] = None


class ModelRegistry:
    """
    Model Registry Service.

    Features:
    - Model versioning
    - Stage management
    - Model comparison
    - Artifact storage

    Example:
        registry = ModelRegistry()

        # Register model
        version = registry.register(
            model=trained_model,
            name="sales_forecast",
            metrics={"rmse": 0.15, "mape": 0.08}
        )

        # Load model
        model = registry.load(name="sales_forecast", stage=ModelStage.PRODUCTION)
    """

    def __init__(self, storage_path: str = "./model_registry"):
        self.storage_path = storage_path
        self._models: Dict[str, List[ModelVersion]] = {}

    def register(
        self,
        model: Any,
        name: str,
        version: Optional[str] = None,
        metrics: Optional[Dict[str, float]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        description: str = "",
    ) -> ModelMetadata:
        """
        Register a new model version.

        Args:
            model: Model object to register
            name: Model name
            version: Version string
            metrics: Model performance metrics
            parameters: Model hyperparameters
            tags: Additional tags
            description: Model description

        Returns:
            ModelMetadata
        """
        # Serialize model
        model_bytes = pickle.dumps(model)
        checksum = hashlib.sha256(model_bytes).hexdigest()

        # Auto-increment version if not provided
        if not version:
            version = self._get_next_version(name)

        # Detect framework
        framework = self._detect_framework(model)

        metadata = ModelMetadata(
            name=name,
            version=version,
            model_type=type(model).__name__,
            framework=framework,
            metrics=metrics or {},
            parameters=parameters or {},
            tags=tags or {},
            description=description,
        )

        model_version = ModelVersion(
            metadata=metadata,
            model_bytes=model_bytes,
            checksum=checksum,
        )

        if name not in self._models:
            self._models[name] = []
        self._models[name].append(model_version)

        logger.info(f"Registered model: {name} v{version}")
        return metadata

    def _get_next_version(self, name: str) -> str:
        """Get next version number."""
        if name not in self._models or not self._models[name]:
            return "1.0.0"

        latest = self._models[name][-1]
        parts = latest.metadata.version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)

    def _detect_framework(self, model: Any) -> str:
        """Detect ML framework from model."""
        module = type(model).__module__
        if "sklearn" in module:
            return "sklearn"
        elif "torch" in module:
            return "pytorch"
        elif "tensorflow" in module or "keras" in module:
            return "tensorflow"
        elif "xgboost" in module:
            return "xgboost"
        elif "lightgbm" in module:
            return "lightgbm"
        return "unknown"

    def load(
        self,
        name: str,
        version: Optional[str] = None,
        stage: Optional[ModelStage] = None,
    ) -> Any:
        """
        Load a model from the registry.

        Args:
            name: Model name
            version: Specific version (optional)
            stage: Load model from specific stage

        Returns:
            Model object
        """
        if name not in self._models:
            raise ValueError(f"Model '{name}' not found")

        versions = self._models[name]

        if version:
            matching = [v for v in versions if v.metadata.version == version]
        elif stage:
            matching = [v for v in versions if v.metadata.stage == stage]
        else:
            matching = [versions[-1]]  # Latest

        if not matching:
            raise ValueError(f"No matching version found for '{name}'")

        model_version = matching[-1]
        return pickle.loads(model_version.model_bytes)

    def promote(
        self,
        name: str,
        version: str,
        stage: ModelStage,
    ) -> ModelMetadata:
        """
        Promote a model to a new stage.

        Args:
            name: Model name
            version: Version to promote
            stage: Target stage

        Returns:
            Updated metadata
        """
        if name not in self._models:
            raise ValueError(f"Model '{name}' not found")

        for model_version in self._models[name]:
            if model_version.metadata.version == version:
                model_version.metadata.stage = stage
                model_version.metadata.updated_at = datetime.utcnow()
                logger.info(f"Promoted {name} v{version} to {stage.value}")
                return model_version.metadata

        raise ValueError(f"Version {version} not found for '{name}'")

    def list_models(self) -> List[str]:
        """List all model names."""
        return list(self._models.keys())

    def list_versions(self, name: str) -> List[ModelMetadata]:
        """List all versions of a model."""
        if name not in self._models:
            return []
        return [v.metadata for v in self._models[name]]

    def get_metadata(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional[ModelMetadata]:
        """Get model metadata."""
        if name not in self._models:
            return None

        versions = self._models[name]
        if version:
            matching = [v for v in versions if v.metadata.version == version]
            return matching[0].metadata if matching else None

        return versions[-1].metadata if versions else None

    def compare_models(
        self,
        name: str,
        versions: List[str],
    ) -> List[Dict[str, Any]]:
        """Compare metrics across versions."""
        if name not in self._models:
            return []

        comparisons = []
        for v in self._models[name]:
            if v.metadata.version in versions:
                comparisons.append({
                    "version": v.metadata.version,
                    "stage": v.metadata.stage.value,
                    **v.metadata.metrics,
                })

        return comparisons

    def delete_version(self, name: str, version: str) -> bool:
        """Delete a model version."""
        if name not in self._models:
            return False

        original_count = len(self._models[name])
        self._models[name] = [
            v for v in self._models[name]
            if v.metadata.version != version
        ]

        return len(self._models[name]) < original_count

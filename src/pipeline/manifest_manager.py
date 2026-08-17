"""
BodhiRAG Corpus Manifest Manager
Manages corpus build manifests for provenance and rollback.
Implements data integrity from OPEN_SOURCE_OPERATIONS_AND_HARDENING.md
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.models import RunManifest

logger = logging.getLogger(__name__)


class ManifestManager:
    """
    Manages corpus build manifests with staging and publication workflow.
    
    Workflow:
    1. Create manifest in staging
    2. Run pipeline, update counts
    3. Validate quality gates
    4. Mark as published (atomic)
    5. Preserve previous build for rollback
    """
    
    def __init__(self, manifest_dir: str = "data/manifests"):
        self.manifest_dir = Path(manifest_dir)
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        
        self.staging_manifest: Optional[RunManifest] = None
        self.published_manifest: Optional[RunManifest] = None
        
        # Load current published manifest
        self._load_published_manifest()
    
    def _manifest_path(self, build_id: str) -> Path:
        """Get path to manifest file."""
        return self.manifest_dir / f"manifest_{build_id}.json"
    
    def _published_link_path(self) -> Path:
        """Get path to symlink pointing to current published build."""
        return self.manifest_dir / "published.json"
    
    def _load_published_manifest(self):
        """Load the currently published manifest."""
        published_link = self._published_link_path()
        
        if published_link.exists():
            try:
                with open(published_link, 'r') as f:
                    data = json.load(f)
                self.published_manifest = RunManifest(**data)
                logger.info(f"Loaded published manifest: {self.published_manifest.build_id}")
            except Exception as e:
                logger.warning(f"Could not load published manifest: {e}")
    
    def create_staging_manifest(
        self,
        input_sources: int,
        parser_name: str = "unknown",
        parser_version: str = "0.0.0",
        embedding_model: str = "unknown"
    ) -> RunManifest:
        """Create a new staging manifest for an upcoming build."""
        self.staging_manifest = RunManifest(
            input_sources=input_sources,
            parser_name=parser_name,
            parser_version=parser_version,
            embedding_model=embedding_model,
        )
        
        logger.info(f"Created staging manifest: {self.staging_manifest.build_id}")
        return self.staging_manifest
    
    def update_staging(self, **updates):
        """Update the staging manifest with new counts."""
        if self.staging_manifest is None:
            logger.error("No staging manifest to update")
            return
        
        for key, value in updates.items():
            if hasattr(self.staging_manifest, key):
                setattr(self.staging_manifest, key, value)
    
    def record_failure(self, source_id: str, stage: str, error: str):
        """Record a failure in the staging manifest."""
        if self.staging_manifest:
            self.staging_manifest.add_failure(source_id, stage, error)
    
    def validate_quality_gates(self) -> Dict[str, Any]:
        """
        Validate quality gates before publication.
        Returns dict with validation results.
        """
        if self.staging_manifest is None:
            return {"valid": False, "error": "No staging manifest"}
        
        results = {
            "valid": True,
            "checks": [],
            "warnings": []
        }
        
        manifest = self.staging_manifest
        
        # Check 1: At least some sources processed
        if manifest.sources_processed == 0:
            results["valid"] = False
            results["checks"].append({
                "check": "sources_processed",
                "status": "failed",
                "message": "No sources were processed"
            })
        else:
            results["checks"].append({
                "check": "sources_processed",
                "status": "passed",
                "message": f"{manifest.sources_processed} sources processed"
            })
        
        # Check 2: Failure rate below threshold
        total = manifest.sources_processed + manifest.sources_failed
        if total > 0:
            failure_rate = manifest.sources_failed / total
            if failure_rate > 0.5:
                results["valid"] = False
                results["checks"].append({
                    "check": "failure_rate",
                    "status": "failed",
                    "message": f"Failure rate {failure_rate:.1%} exceeds 50%"
                })
            elif failure_rate > 0.2:
                results["warnings"].append(f"Failure rate is {failure_rate:.1%}")
        
        # Check 3: At least some chunks created
        if manifest.chunks_created == 0:
            results["warnings"].append("No chunks were created")
        
        return results
    
    def publish(self) -> bool:
        """
        Publish the staging manifest after quality gates pass.
        Preserves previous build for rollback.
        """
        if self.staging_manifest is None:
            logger.error("No staging manifest to publish")
            return False
        
        # Validate quality gates
        validation = self.validate_quality_gates()
        if not validation["valid"]:
            logger.error(f"Quality gates failed: {validation}")
            return False
        
        try:
            # Mark as published
            self.staging_manifest.mark_published()
            
            # Save manifest file
            manifest_path = self._manifest_path(self.staging_manifest.build_id)
            with open(manifest_path, 'w') as f:
                json.dump(self.staging_manifest.model_dump(), f, indent=2, default=str)
            
            # Backup previous published link
            published_link = self._published_link_path()
            previous_backup = self.manifest_dir / "previous_published.json"
            
            if published_link.exists():
                if published_link.is_symlink():
                    # Copy actual file content
                    with open(published_link, 'r') as src:
                        with open(previous_backup, 'w') as dst:
                            dst.write(src.read())
                else:
                    # Rename regular file
                    published_link.rename(previous_backup)
            
            # Update published link (copy instead of symlink for HF Spaces compatibility)
            with open(published_link, 'w') as f:
                json.dump(self.staging_manifest.model_dump(), f, indent=2, default=str)
            
            logger.info(f"Published manifest: {self.staging_manifest.build_id}")
            
            # Update instance state
            self.published_manifest = self.staging_manifest
            self.staging_manifest = None
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish manifest: {e}")
            return False
    
    def rollback(self) -> bool:
        """Rollback to the previous published build."""
        previous_backup = self.manifest_dir / "previous_published.json"
        published_link = self._published_link_path()
        
        if not previous_backup.exists():
            logger.error("No previous build to rollback to")
            return False
        
        try:
            # Restore previous as current
            with open(previous_backup, 'r') as src:
                with open(published_link, 'w') as dst:
                    dst.write(src.read())
            
            # Reload
            self._load_published_manifest()
            
            logger.info("Rolled back to previous published build")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def get_published_build_id(self) -> Optional[str]:
        """Get the ID of the currently published build."""
        if self.published_manifest:
            return self.published_manifest.build_id
        return None
    
    def get_build_info(self, build_id: str) -> Optional[Dict]:
        """Get information about a specific build."""
        manifest_path = self._manifest_path(build_id)
        
        if not manifest_path.exists():
            return None
        
        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Could not load build {build_id}: {e}")
            return None
    
    def list_builds(self) -> List[Dict]:
        """List all available builds."""
        builds = []
        
        for manifest_file in self.manifest_dir.glob("manifest_*.json"):
            try:
                with open(manifest_file, 'r') as f:
                    data = json.load(f)
                
                builds.append({
                    "build_id": data.get("build_id"),
                    "status": data.get("status"),
                    "started_at": data.get("started_at"),
                    "completed_at": data.get("completed_at"),
                    "sources_processed": data.get("sources_processed"),
                    "is_published": data.get("build_id") == self.get_published_build_id()
                })
            except Exception:
                continue
        
        # Sort by started_at descending
        builds.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        
        return builds
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of current state."""
        return {
            "published_build_id": self.get_published_build_id(),
            "has_staging": self.staging_manifest is not None,
            "staging_build_id": self.staging_manifest.build_id if self.staging_manifest else None,
            "total_builds": len(self.list_builds()),
        }


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------

_manifest_manager: Optional[ManifestManager] = None


def get_manifest_manager() -> ManifestManager:
    """Get or create global manifest manager."""
    global _manifest_manager
    if _manifest_manager is None:
        from src.core.config import settings
        _manifest_manager = ManifestManager(settings.corpus_manifest_path)
    return _manifest_manager

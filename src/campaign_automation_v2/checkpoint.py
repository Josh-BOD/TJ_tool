"""
Checkpoint manager for tracking campaign creation progress.

Handles saving and resuming progress to allow for interruption recovery.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .models import CampaignBatch, CampaignStatus


class CheckpointManager:
    """Manages checkpoints for campaign creation progress."""
    
    def __init__(self, checkpoint_dir: Path):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def get_checkpoint_path(self, session_id: str) -> Path:
        """Get checkpoint file path for session."""
        return self.checkpoint_dir / f"checkpoint_{session_id}.json"
    
    def save(self, batch: CampaignBatch):
        """
        Save current progress to checkpoint.
        
        Args:
            batch: CampaignBatch to checkpoint
        """
        checkpoint_path = self.get_checkpoint_path(batch.session_id)
        
        data = {
            "session_id": batch.session_id,
            "input_file": batch.input_file,
            "timestamp": datetime.now().isoformat(),
            "campaigns": batch.to_dict()["campaigns"]
        }
        
        # Write atomically
        tmp_path = checkpoint_path.with_suffix(".tmp")
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        # Atomic rename
        tmp_path.replace(checkpoint_path)
    
    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint for session.
        
        Args:
            session_id: Session ID to load
            
        Returns:
            Checkpoint data or None if not found
        """
        checkpoint_path = self.get_checkpoint_path(session_id)
        
        if not checkpoint_path.exists():
            return None
        
        try:
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def delete(self, session_id: str):
        """
        Delete checkpoint file.
        
        Args:
            session_id: Session ID to delete
        """
        checkpoint_path = self.get_checkpoint_path(session_id)
        if checkpoint_path.exists():
            checkpoint_path.unlink()
    
    def list_checkpoints(self) -> list[Dict[str, Any]]:
        """
        List all available checkpoints.
        
        Returns:
            List of checkpoint metadata
        """
        checkpoints = []
        
        for checkpoint_file in self.checkpoint_dir.glob("checkpoint_*.json"):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                checkpoints.append({
                    "session_id": data["session_id"],
                    "input_file": data["input_file"],
                    "timestamp": data["timestamp"],
                    "file": str(checkpoint_file)
                })
            except (json.JSONDecodeError, IOError, KeyError):
                continue
        
        # Sort by timestamp (newest first)
        checkpoints.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return checkpoints
    
    def restore_batch(self, batch: CampaignBatch, checkpoint_data: Dict[str, Any]):
        """
        Restore batch state from checkpoint data.
        
        Args:
            batch: CampaignBatch to restore into
            checkpoint_data: Checkpoint data to restore from
        """
        campaigns_data = checkpoint_data.get("campaigns", [])
        
        for i, campaign in enumerate(batch.campaigns):
            if i >= len(campaigns_data):
                break
            
            campaign_data = campaigns_data[i]
            
            # Restore status
            try:
                campaign.status = CampaignStatus(campaign_data.get("status", "pending"))
            except ValueError:
                campaign.status = CampaignStatus.PENDING
            
            # Restore variant statuses
            variant_statuses = campaign_data.get("variant_statuses", {})
            for variant, status_data in variant_statuses.items():
                if variant in campaign.variant_statuses:
                    vs = campaign.variant_statuses[variant]
                    
                    try:
                        vs.status = CampaignStatus(status_data.get("status", "pending"))
                    except ValueError:
                        vs.status = CampaignStatus.PENDING
                    
                    vs.campaign_id = status_data.get("campaign_id")
                    vs.campaign_name = status_data.get("campaign_name")
                    vs.ads_uploaded = status_data.get("ads_uploaded", 0)
                    vs.error = status_data.get("error")
                    vs.step = status_data.get("step")
                    vs.completed_at = status_data.get("completed_at")


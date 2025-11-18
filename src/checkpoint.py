"""Checkpoint management for resumable uploads."""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages upload checkpoints for resume functionality."""
    
    def __init__(self, checkpoint_file: Path):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_file: Path to checkpoint JSON file
        """
        self.checkpoint_file = checkpoint_file
        self.checkpoint_data = {
            'session_id': None,
            'started_at': None,
            'last_updated': None,
            'campaigns': {}
        }
    
    def load(self) -> bool:
        """
        Load checkpoint from file.
        
        Returns:
            True if checkpoint loaded successfully, False otherwise
        """
        try:
            if not self.checkpoint_file.exists():
                logger.info("No checkpoint file found - starting fresh")
                return False
            
            with open(self.checkpoint_file, 'r') as f:
                self.checkpoint_data = json.load(f)
            
            completed = sum(1 for c in self.checkpoint_data['campaigns'].values() 
                          if c.get('status') == 'success')
            failed = sum(1 for c in self.checkpoint_data['campaigns'].values() 
                        if c.get('status') == 'failed')
            total = len(self.checkpoint_data['campaigns'])
            
            logger.info(f"✓ Loaded checkpoint from {self.checkpoint_data.get('started_at')}")
            logger.info(f"  Previous session: {completed} successful, {failed} failed, "
                       f"{total - completed - failed} remaining")
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return False
    
    def save(self):
        """Save checkpoint to file."""
        try:
            # Update last_updated timestamp
            self.checkpoint_data['last_updated'] = datetime.now().isoformat()
            
            # Ensure directory exists
            self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to file
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.checkpoint_data, f, indent=2)
            
            logger.debug(f"Checkpoint saved to {self.checkpoint_file}")
            
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")
    
    def initialize_session(self, session_id: str, campaign_ids: list):
        """
        Initialize a new checkpoint session.
        
        Args:
            session_id: Unique session identifier
            campaign_ids: List of campaign IDs to track
        """
        self.checkpoint_data = {
            'session_id': session_id,
            'started_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'campaigns': {
                cid: {'status': 'pending'} for cid in campaign_ids
            }
        }
        self.save()
    
    def update_campaign(self, campaign_id: str, status: str, **kwargs):
        """
        Update campaign status in checkpoint.
        
        Args:
            campaign_id: Campaign ID
            status: Status ('success', 'failed', 'pending', 'skipped')
            **kwargs: Additional data (ads_created, error, etc.)
        """
        if campaign_id not in self.checkpoint_data['campaigns']:
            self.checkpoint_data['campaigns'][campaign_id] = {}
        
        self.checkpoint_data['campaigns'][campaign_id]['status'] = status
        self.checkpoint_data['campaigns'][campaign_id]['timestamp'] = datetime.now().isoformat()
        
        # Add any additional data
        for key, value in kwargs.items():
            self.checkpoint_data['campaigns'][campaign_id][key] = value
        
        self.save()
    
    def get_campaign_status(self, campaign_id: str) -> Optional[str]:
        """
        Get status of a campaign.
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            Status string or None if not found
        """
        campaign = self.checkpoint_data['campaigns'].get(campaign_id)
        return campaign.get('status') if campaign else None
    
    def should_process_campaign(self, campaign_id: str, retry_failed: bool = False) -> bool:
        """
        Check if a campaign should be processed.
        
        Args:
            campaign_id: Campaign ID
            retry_failed: If True, retry failed campaigns
            
        Returns:
            True if campaign should be processed, False if should skip
        """
        status = self.get_campaign_status(campaign_id)
        
        # If no checkpoint data, process it
        if status is None:
            return True
        
        # Always skip successful campaigns
        if status == 'success':
            return False
        
        # Skip failed campaigns unless retry_failed is True
        if status == 'failed':
            return retry_failed
        
        # Process pending campaigns
        return True
    
    def get_stats(self) -> Dict:
        """
        Get checkpoint statistics.
        
        Returns:
            Dict with success, failed, pending counts
        """
        campaigns = self.checkpoint_data['campaigns']
        return {
            'total': len(campaigns),
            'success': sum(1 for c in campaigns.values() if c.get('status') == 'success'),
            'failed': sum(1 for c in campaigns.values() if c.get('status') == 'failed'),
            'pending': sum(1 for c in campaigns.values() if c.get('status') == 'pending'),
            'session_id': self.checkpoint_data.get('session_id'),
            'started_at': self.checkpoint_data.get('started_at')
        }
    
    def clear(self):
        """Clear checkpoint file."""
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                logger.info("✓ Checkpoint cleared - starting fresh")
        except Exception as e:
            logger.warning(f"Failed to clear checkpoint: {e}")
    
    def get_campaign_data(self, campaign_id: str) -> Optional[Dict]:
        """
        Get full campaign data from checkpoint.
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            Campaign data dict or None
        """
        return self.checkpoint_data['campaigns'].get(campaign_id)


"""CSV parsing for creative IDs and campaign IDs."""

import logging
import pandas as pd
from pathlib import Path
from typing import Set, List, Dict

logger = logging.getLogger(__name__)


def parse_creative_ids_csv(csv_path: Path) -> Set[str]:
    """
    Parse Creative IDs CSV file.
    
    Supports multiple columns but only uses 'Creative ID' column.
    
    Expected format:
        Creative ID,Ad Name,Notes
        2212936201,Black Friday Ad 1,Holiday promo
        2212936202,Black Friday Ad 2,Holiday promo
    
    Args:
        csv_path: Path to Creative IDs CSV file
        
    Returns:
        Set of creative IDs as strings
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If 'Creative ID' column not found
    """
    try:
        if not csv_path.exists():
            raise FileNotFoundError(f"Creative IDs CSV not found: {csv_path}")
        
        logger.info(f"Parsing Creative IDs from: {csv_path}")
        
        # Read CSV
        df = pd.read_csv(csv_path)
        
        # Check for required column
        if 'Creative ID' not in df.columns:
            raise ValueError(
                f"'Creative ID' column not found in {csv_path.name}. "
                f"Found columns: {', '.join(df.columns)}"
            )
        
        # Convert to string and remove any NaN values
        creative_ids = set(
            str(int(cid)) if pd.notna(cid) else None
            for cid in df['Creative ID']
        )
        
        # Remove None values
        creative_ids.discard(None)
        
        logger.info(f"✓ Loaded {len(creative_ids)} unique Creative IDs")
        
        if len(creative_ids) == 0:
            logger.warning("No valid Creative IDs found in CSV!")
        
        return creative_ids
        
    except Exception as e:
        logger.error(f"Failed to parse Creative IDs CSV: {e}")
        raise


def parse_campaign_ids_csv(csv_path: Path) -> List[Dict[str, str]]:
    """
    Parse Campaign IDs CSV file.
    
    Supports multiple columns but only uses 'Campaign ID' column.
    Other columns (Campaign Name, Notes) are preserved for logging.
    
    Expected format:
        Campaign ID,Campaign Name,Notes
        1012927602,Desktop-Stepmom-US,
        1012927603,iOS-Stepmom-US,
    
    Args:
        csv_path: Path to Campaign IDs CSV file
        
    Returns:
        List of dictionaries with campaign information:
        [
            {'id': '1012927602', 'name': 'Desktop-Stepmom-US', 'notes': ''},
            {'id': '1012927603', 'name': 'iOS-Stepmom-US', 'notes': ''},
        ]
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If 'Campaign ID' column not found
    """
    try:
        if not csv_path.exists():
            raise FileNotFoundError(f"Campaign IDs CSV not found: {csv_path}")
        
        logger.info(f"Parsing Campaign IDs from: {csv_path}")
        
        # Read CSV
        df = pd.read_csv(csv_path)
        
        # Check for required column
        if 'Campaign ID' not in df.columns:
            raise ValueError(
                f"'Campaign ID' column not found in {csv_path.name}. "
                f"Found columns: {', '.join(df.columns)}"
            )
        
        # Build list of campaign dicts
        campaigns = []
        for _, row in df.iterrows():
            campaign_id = row['Campaign ID']
            
            # Skip if NaN
            if pd.isna(campaign_id):
                continue
            
            # Convert to string (handle both int and string IDs)
            campaign_id = str(int(campaign_id)) if isinstance(campaign_id, float) else str(campaign_id)
            
            campaign = {
                'id': campaign_id,
                'name': str(row.get('Campaign Name', campaign_id)) if pd.notna(row.get('Campaign Name')) else campaign_id,
                'notes': str(row.get('Notes', '')) if pd.notna(row.get('Notes')) else ''
            }
            
            campaigns.append(campaign)
        
        logger.info(f"✓ Loaded {len(campaigns)} campaigns")
        
        if len(campaigns) == 0:
            logger.warning("No valid Campaign IDs found in CSV!")
        
        return campaigns
        
    except Exception as e:
        logger.error(f"Failed to parse Campaign IDs CSV: {e}")
        raise


def validate_csv_files(creatives_csv: Path, campaigns_csv: Path) -> tuple[bool, List[str]]:
    """
    Validate both CSV files before processing.
    
    Args:
        creatives_csv: Path to Creative IDs CSV
        campaigns_csv: Path to Campaign IDs CSV
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check files exist
    if not creatives_csv.exists():
        errors.append(f"Creative IDs CSV not found: {creatives_csv}")
    
    if not campaigns_csv.exists():
        errors.append(f"Campaign IDs CSV not found: {campaigns_csv}")
    
    if errors:
        return False, errors
    
    # Try parsing both files
    try:
        creative_ids = parse_creative_ids_csv(creatives_csv)
        if len(creative_ids) == 0:
            errors.append("No Creative IDs found in CSV")
    except Exception as e:
        errors.append(f"Creative IDs CSV error: {e}")
    
    try:
        campaigns = parse_campaign_ids_csv(campaigns_csv)
        if len(campaigns) == 0:
            errors.append("No Campaign IDs found in CSV")
    except Exception as e:
        errors.append(f"Campaign IDs CSV error: {e}")
    
    return len(errors) == 0, errors


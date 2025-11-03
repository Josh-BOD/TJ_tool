"""CSV processing and validation module."""

import logging
import pandas as pd
import re
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)


class CSVProcessor:
    """Handles CSV validation, cleaning, and processing."""
    
    @staticmethod
    def validate_csv(csv_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate CSV format and required columns.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Check file exists
            if not csv_path.exists():
                errors.append(f"File not found: {csv_path}")
                return False, errors
            
            # Check file size (max 500KB)
            file_size = csv_path.stat().st_size
            if file_size > 500 * 1024:  # 500KB in bytes
                errors.append(f"File too large: {file_size / 1024:.1f}KB (max 500KB)")
            
            # Read CSV
            df = pd.read_csv(csv_path)
            
            # Check required columns
            required_columns = [
                'Ad Name',
                'Target URL',
                'Creative ID',
                'Custom CTA Text',
                'Custom CTA URL',
                'Banner CTA Creative ID',
                'Banner CTA Title',
                'Banner CTA Subtitle',
                'Banner CTA URL',
                'Tracking Pixel'
            ]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                errors.append(f"Missing columns: {', '.join(missing_columns)}")
            
            # Check row count (max 50 ads)
            if len(df) > 50:
                errors.append(f"Too many ads: {len(df)} (max 50)")
            
            if len(df) == 0:
                errors.append("CSV is empty")
            
            # Check for required values in critical columns
            if 'Ad Name' in df.columns and df['Ad Name'].isna().any():
                errors.append("Some rows missing Ad Name")
            
            if 'Target URL' in df.columns and df['Target URL'].isna().any():
                errors.append("Some rows missing Target URL")
            
            if 'Creative ID' in df.columns and df['Creative ID'].isna().any():
                errors.append("Some rows missing Creative ID")
            
            return len(errors) == 0, errors
            
        except pd.errors.EmptyDataError:
            errors.append("CSV file is empty")
            return False, errors
        except pd.errors.ParserError as e:
            errors.append(f"CSV parsing error: {e}")
            return False, errors
        except Exception as e:
            errors.append(f"Validation error: {e}")
            return False, errors
    
    @staticmethod
    def remove_invalid_creatives(
        csv_path: Path, 
        invalid_creative_ids: List[str]
    ) -> Tuple[Path, pd.DataFrame]:
        """
        Remove rows with invalid creative IDs from CSV.
        
        Args:
            csv_path: Path to original CSV
            invalid_creative_ids: List of creative IDs to remove
            
        Returns:
            Tuple of (cleaned_csv_path, removed_rows_dataframe)
        """
        try:
            logger.info(f"Removing {len(invalid_creative_ids)} invalid creative IDs from CSV...")
            
            # Read CSV
            df = pd.read_csv(csv_path)
            
            # Convert creative IDs to strings for comparison
            invalid_ids_str = [str(id) for id in invalid_creative_ids]
            df['Creative ID'] = df['Creative ID'].astype(str)
            
            # Find rows to remove
            removed_rows = df[df['Creative ID'].isin(invalid_ids_str)].copy()
            
            # Keep only valid rows
            df_cleaned = df[~df['Creative ID'].isin(invalid_ids_str)]
            
            # Save cleaned CSV
            cleaned_path = csv_path.parent / f"{csv_path.stem}_cleaned{csv_path.suffix}"
            df_cleaned.to_csv(cleaned_path, index=False)
            
            logger.info(f"✓ Cleaned CSV saved: {cleaned_path}")
            logger.info(f"  Original rows: {len(df)}")
            logger.info(f"  Removed rows: {len(removed_rows)}")
            logger.info(f"  Remaining rows: {len(df_cleaned)}")
            
            return cleaned_path, removed_rows
            
        except Exception as e:
            logger.error(f"Failed to clean CSV: {e}")
            raise
    
    @staticmethod
    def update_campaign_name_in_urls(csv_path: Path, campaign_name: str) -> Path:
        """
        Update sub11 parameter in all URLs to use the campaign name.
        
        Args:
            csv_path: Path to original CSV
            campaign_name: Campaign name to insert into sub11 parameter
            
        Returns:
            Path to updated CSV file
        """
        try:
            logger.info(f"Updating URLs with campaign name: {campaign_name}")
            
            # Read CSV
            df = pd.read_csv(csv_path)
            
            # Function to update a single URL
            def update_url(url):
                if pd.isna(url) or not url:
                    return url
                
                try:
                    # Simple regex replacement for sub11 parameter
                    # Matches: sub11=anything&  OR  sub11=anything (end of string)
                    updated_url = re.sub(
                        r'sub11=[^&]*',
                        f'sub11={campaign_name}',
                        str(url)
                    )
                    return updated_url
                except Exception as e:
                    logger.warning(f"Failed to update URL: {e}")
                    return url
            
            # Update all URL columns
            url_columns = ['Target URL', 'Custom CTA URL', 'Banner CTA URL']
            urls_updated = 0
            
            for col in url_columns:
                if col in df.columns:
                    original_urls = df[col].copy()
                    df[col] = df[col].apply(update_url)
                    # Count how many were actually changed
                    urls_updated += (original_urls != df[col]).sum()
            
            # Save updated CSV to temporary location
            output_path = csv_path.parent / f"{csv_path.stem}_campaign_{campaign_name[:20]}{csv_path.suffix}"
            df.to_csv(output_path, index=False)
            
            logger.info(f"✓ Updated {urls_updated} URLs with campaign name")
            logger.info(f"✓ Updated CSV saved: {output_path.name}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to update URLs in CSV: {e}")
            # Return original path if update fails
            return csv_path
    
    @staticmethod
    def get_csv_summary(csv_path: Path) -> dict:
        """
        Get summary information about CSV file.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Dictionary with CSV summary
        """
        try:
            df = pd.read_csv(csv_path)
            
            return {
                'filename': csv_path.name,
                'row_count': len(df),
                'file_size_kb': csv_path.stat().st_size / 1024,
                'columns': list(df.columns),
                'ad_names': df['Ad Name'].tolist() if 'Ad Name' in df.columns else [],
                'creative_ids': df['Creative ID'].tolist() if 'Creative ID' in df.columns else [],
            }
        except Exception as e:
            logger.error(f"Failed to get CSV summary: {e}")
            return {'error': str(e)}


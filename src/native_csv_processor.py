"""CSV processing and validation module for Native ads."""

import logging
import pandas as pd
import re
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class NativeCSVProcessor:
    """Handles CSV validation, cleaning, and processing for Native ads."""
    
    @staticmethod
    def validate_csv(csv_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate Native CSV format and required columns.
        
        Native ad format requires:
        - Ad Name
        - Target URL
        - Video Creative ID
        - Thumbnail Creative ID
        - Headline
        - Brand Name
        
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
            
            # Check required columns for Native ads
            required_columns = [
                'Ad Name',
                'Target URL',
                'Video Creative ID',
                'Thumbnail Creative ID',
                'Headline',
                'Brand Name'
            ]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                errors.append(f"Missing columns: {', '.join(missing_columns)}")
                errors.append(f"Found columns: {', '.join(df.columns)}")
                errors.append(f"Required format for Native ads: {', '.join(required_columns)}")
            
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
            
            if 'Video Creative ID' in df.columns and df['Video Creative ID'].isna().any():
                errors.append("Some rows missing Video Creative ID")
            
            if 'Thumbnail Creative ID' in df.columns and df['Thumbnail Creative ID'].isna().any():
                errors.append("Some rows missing Thumbnail Creative ID")
            
            if 'Headline' in df.columns and df['Headline'].isna().any():
                errors.append("Some rows missing Headline")
            
            if 'Brand Name' in df.columns and df['Brand Name'].isna().any():
                errors.append("Some rows missing Brand Name")
            
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
        Remove rows with invalid creative IDs from Native CSV.
        
        For Native ads, checks both Video Creative ID and Thumbnail Creative ID.
        
        Args:
            csv_path: Path to original CSV
            invalid_creative_ids: List of creative IDs to remove
            
        Returns:
            Tuple of (cleaned_csv_path, removed_rows_dataframe)
        """
        try:
            logger.info(f"Removing {len(invalid_creative_ids)} invalid creative IDs from Native CSV...")
            
            # Read CSV
            df = pd.read_csv(csv_path)
            
            # Convert creative IDs to strings for comparison
            invalid_ids_str = [str(id) for id in invalid_creative_ids]
            df['Video Creative ID'] = df['Video Creative ID'].astype(str)
            df['Thumbnail Creative ID'] = df['Thumbnail Creative ID'].astype(str)
            
            # Find rows to remove (check both video and thumbnail IDs)
            removed_rows = df[
                df['Video Creative ID'].isin(invalid_ids_str) | 
                df['Thumbnail Creative ID'].isin(invalid_ids_str)
            ].copy()
            
            # Keep only valid rows
            df_cleaned = df[
                ~(df['Video Creative ID'].isin(invalid_ids_str) | 
                  df['Thumbnail Creative ID'].isin(invalid_ids_str))
            ]
            
            # Save cleaned CSV
            cleaned_path = csv_path.parent / f"{csv_path.stem}_cleaned{csv_path.suffix}"
            df_cleaned.to_csv(cleaned_path, index=False)
            
            logger.info(f"✓ Cleaned Native CSV saved: {cleaned_path}")
            logger.info(f"  Original rows: {len(df)}")
            logger.info(f"  Removed rows: {len(removed_rows)}")
            logger.info(f"  Remaining rows: {len(df_cleaned)}")
            
            return cleaned_path, removed_rows
            
        except Exception as e:
            logger.error(f"Failed to clean Native CSV: {e}")
            raise
    
    @staticmethod
    def update_campaign_name_in_urls(csv_path: Path, campaign_name: str, wip_dir: Path) -> Path:
        """
        Update sub11 parameter in Target URLs to use the campaign name.
        Saves to WIP folder to keep input folder clean.
        
        Args:
            csv_path: Path to original CSV
            campaign_name: Campaign name to insert into sub11 parameter
            wip_dir: Work In Progress directory for temporary files
            
        Returns:
            Path to updated CSV file in WIP folder
        """
        try:
            logger.info(f"Updating Native ad URLs with campaign name: {campaign_name}")
            
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
            
            # Update Target URL column
            if 'Target URL' in df.columns:
                original_urls = df['Target URL'].copy()
                df['Target URL'] = df['Target URL'].apply(update_url)
                urls_updated = (original_urls != df['Target URL']).sum()
            else:
                urls_updated = 0
            
            # Save updated CSV to WIP folder (keeps input folder clean)
            output_path = wip_dir / f"{csv_path.stem}_native_campaign_{campaign_name[:20]}{csv_path.suffix}"
            df.to_csv(output_path, index=False)
            
            logger.info(f"✓ Updated {urls_updated} URLs with campaign name")
            logger.info(f"✓ Updated Native CSV saved to WIP: {output_path.name}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to update URLs in Native CSV: {e}")
            # Return original path if update fails
            return csv_path
    
    @staticmethod
    def get_csv_summary(csv_path: Path) -> dict:
        """
        Get summary information about Native CSV file.
        
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
                'video_creative_ids': df['Video Creative ID'].tolist() if 'Video Creative ID' in df.columns else [],
                'thumbnail_creative_ids': df['Thumbnail Creative ID'].tolist() if 'Thumbnail Creative ID' in df.columns else [],
            }
        except Exception as e:
            logger.error(f"Failed to get Native CSV summary: {e}")
            return {'error': str(e)}


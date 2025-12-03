"""
CSV handling for Keyword Research tool.

Reads input CSVs in Niche-Findom_v2.csv format and writes discovered keywords
in the same format for direct use in campaign creation.
"""

import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple

from .models import SeedKeywordRow, DiscoveredKeyword

logger = logging.getLogger(__name__)


def parse_input_csv(csv_path: Path) -> Tuple[List[SeedKeywordRow], List[str]]:
    """
    Parse input CSV file in Niche-Findom_v2.csv format.
    
    Handles semicolon-separated keywords in the 'keywords' column,
    expanding them into separate rows.
    
    Args:
        csv_path: Path to input CSV
        
    Returns:
        Tuple of (list of SeedKeywordRow objects, list of fieldnames)
    """
    rows = []
    fieldnames = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        
        for row in reader:
            try:
                # Get keywords - may be semicolon-separated
                keywords_raw = row.get('keywords', '').strip()
                
                # Split by semicolon if present, otherwise treat as single keyword
                if ';' in keywords_raw:
                    keywords_list = [k.strip() for k in keywords_raw.split(';') if k.strip()]
                else:
                    keywords_list = [keywords_raw] if keywords_raw else []
                
                # Store any extra columns not in the standard set
                standard_columns = {
                    'group', 'keywords', 'keyword_matches', 'gender', 'geo',
                    'multi_geo', 'csv_file', 'target_cpa', 'per_source_budget',
                    'max_bid', 'frequency_cap', 'max_daily_budget', 'variants',
                    'ios_version', 'android_version', 'ad_format', 'enabled'
                }
                extra_cols = {}
                for key, value in row.items():
                    if key not in standard_columns:
                        extra_cols[key] = value
                
                # Create a row for each keyword
                for keyword in keywords_list:
                    seed_row = SeedKeywordRow(
                        group=row.get('group', ''),
                        keyword=keyword,
                        keyword_matches=row.get('keyword_matches', ''),
                        gender=row.get('gender', 'all'),
                        geo=row.get('geo', ''),
                        multi_geo=row.get('multi_geo', ''),
                        csv_file=row.get('csv_file', ''),
                        target_cpa=float(row.get('target_cpa', 50) or 50),
                        per_source_budget=float(row.get('per_source_budget', 100) or 100),
                        max_bid=float(row.get('max_bid', 10) or 10),
                        frequency_cap=int(row.get('frequency_cap', 2) or 2),
                        max_daily_budget=float(row.get('max_daily_budget', 250) or 250),
                        variants=row.get('variants', ''),
                        ios_version=row.get('ios_version', ''),
                        android_version=row.get('android_version', ''),
                        ad_format=row.get('ad_format', 'Native'),
                        enabled=str(row.get('enabled', 'FALSE')).upper() == 'TRUE',
                        extra_columns=extra_cols.copy()
                    )
                    rows.append(seed_row)
                    
            except Exception as e:
                logger.warning(f"Error parsing row: {e}")
                continue
    
    logger.info(f"Parsed {len(rows)} seed keywords from {csv_path}")
    return rows, fieldnames


def get_groups_from_rows(rows: List[SeedKeywordRow]) -> List[str]:
    """
    Get unique group names from rows.
    
    Args:
        rows: List of SeedKeywordRow objects
        
    Returns:
        List of unique group names
    """
    seen = set()
    groups = []
    for row in rows:
        if row.group and row.group not in seen:
            seen.add(row.group)
            groups.append(row.group)
    return groups


def generate_output_filename(groups: List[str], output_dir: Path) -> Path:
    """
    Generate output filename based on group names.
    
    Args:
        groups: List of group names
        output_dir: Output directory
        
    Returns:
        Path to output file
    """
    if len(groups) == 1:
        # Single group: niche-GroupName_v2.csv
        group_name = groups[0].replace(' ', '-')
        filename = f"niche-{group_name}_v2.csv"
    else:
        # Multiple groups: niche-Group1-Group2_v2.csv
        group_names = '-'.join(g.replace(' ', '-') for g in groups[:3])
        if len(groups) > 3:
            group_names += f"-and-{len(groups)-3}-more"
        filename = f"niche-{group_names}_v2.csv"
    
    return output_dir / filename


def get_unique_seed_keywords(rows: List[SeedKeywordRow]) -> List[str]:
    """
    Extract unique seed keywords from parsed rows.
    
    Args:
        rows: List of SeedKeywordRow objects
        
    Returns:
        List of unique keywords (preserving first occurrence order)
    """
    seen = set()
    unique = []
    
    for row in rows:
        keyword_lower = row.keyword.lower()
        if keyword_lower not in seen:
            seen.add(keyword_lower)
            unique.append(row.keyword)
    
    return unique


def get_existing_keywords(rows: List[SeedKeywordRow]) -> Set[str]:
    """
    Get set of existing keywords (lowercase) for deduplication.
    
    Args:
        rows: List of SeedKeywordRow objects
        
    Returns:
        Set of lowercase keyword strings
    """
    return {row.keyword.lower() for row in rows}


def write_output_csv(
    output_path: Path,
    original_rows: List[SeedKeywordRow],
    discovered_keywords: Dict[str, List[str]],
    fieldnames: List[str],
    include_originals: bool = False
) -> int:
    """
    Write discovered keywords to CSV in the same format as input.
    
    Args:
        output_path: Path to output CSV
        original_rows: Original seed keyword rows
        discovered_keywords: Dict mapping seed keyword -> list of discovered keywords
        fieldnames: Original CSV fieldnames to preserve column order
        include_originals: If True, include original seed keywords in output
        
    Returns:
        Number of rows written
    """
    # Build a lookup from seed keyword to its row (for inheriting settings)
    seed_to_row: Dict[str, SeedKeywordRow] = {}
    for row in original_rows:
        if row.keyword.lower() not in seed_to_row:
            seed_to_row[row.keyword.lower()] = row
    
    # Get existing keywords for deduplication
    existing = get_existing_keywords(original_rows)
    
    # Collect all rows to write
    output_rows: List[Dict[str, Any]] = []
    
    # Optionally include original rows
    if include_originals:
        for row in original_rows:
            output_rows.append(row.to_dict())
    
    # Add discovered keywords
    for seed_keyword, keywords in discovered_keywords.items():
        seed_row = seed_to_row.get(seed_keyword.lower())
        if not seed_row:
            logger.warning(f"No seed row found for '{seed_keyword}', skipping")
            continue
        
        for keyword in keywords:
            # Skip if already exists
            if keyword.lower() in existing:
                continue
            
            # Create new row with discovered keyword
            new_row = seed_row.create_discovered_row(keyword)
            output_rows.append(new_row.to_dict())
            
            # Add to existing to avoid duplicates within discovered
            existing.add(keyword.lower())
    
    # Write to CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)
    
    logger.info(f"Wrote {len(output_rows)} rows to {output_path}")
    return len(output_rows)


def write_output_csvs_by_group(
    output_dir: Path,
    original_rows: List[SeedKeywordRow],
    discovered_keywords: Dict[str, List[str]],
    fieldnames: List[str],
    include_originals: bool = False
) -> Dict[str, int]:
    """
    Write discovered keywords to separate CSV files per group.
    
    Args:
        output_dir: Directory to write output CSVs
        original_rows: Original seed keyword rows
        discovered_keywords: Dict mapping seed keyword -> list of discovered keywords
        fieldnames: Original CSV fieldnames to preserve column order
        include_originals: If True, include original seed keywords in output
        
    Returns:
        Dict mapping group name -> number of rows written
    """
    # Build a lookup from seed keyword to its row
    seed_to_row: Dict[str, SeedKeywordRow] = {}
    for row in original_rows:
        if row.keyword.lower() not in seed_to_row:
            seed_to_row[row.keyword.lower()] = row
    
    # Group original rows by group name
    rows_by_group: Dict[str, List[SeedKeywordRow]] = {}
    for row in original_rows:
        if row.group not in rows_by_group:
            rows_by_group[row.group] = []
        rows_by_group[row.group].append(row)
    
    # Track existing keywords per group for deduplication
    existing_by_group: Dict[str, Set[str]] = {}
    for group, rows in rows_by_group.items():
        existing_by_group[group] = {r.keyword.lower() for r in rows}
    
    # Collect discovered keywords by group
    discovered_by_group: Dict[str, List[Dict[str, Any]]] = {g: [] for g in rows_by_group}
    
    for seed_keyword, keywords in discovered_keywords.items():
        seed_row = seed_to_row.get(seed_keyword.lower())
        if not seed_row:
            logger.warning(f"No seed row found for '{seed_keyword}', skipping")
            continue
        
        group = seed_row.group
        existing = existing_by_group.get(group, set())
        
        for keyword in keywords:
            # Skip if already exists in this group
            if keyword.lower() in existing:
                continue
            
            # Create new row with discovered keyword
            new_row = seed_row.create_discovered_row(keyword)
            discovered_by_group[group].append(new_row.to_dict())
            
            # Add to existing to avoid duplicates
            existing.add(keyword.lower())
    
    # Write separate CSV for each group
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    
    for group, discovered_rows in discovered_by_group.items():
        # Build output rows for this group
        output_rows: List[Dict[str, Any]] = []
        
        # Optionally include original rows for this group
        if include_originals:
            for row in rows_by_group.get(group, []):
                output_rows.append(row.to_dict())
        
        # Add discovered keywords
        output_rows.extend(discovered_rows)
        
        if not output_rows:
            continue
        
        # Generate filename: niche-GroupName_v2.csv
        group_name = group.replace(' ', '-')
        filename = f"niche-{group_name}_v2.csv"
        output_path = output_dir / filename
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)
        
        logger.info(f"Wrote {len(output_rows)} rows to {output_path}")
        results[group] = len(output_rows)
    
    return results


def write_simple_keyword_list(
    output_path: Path,
    discovered_keywords: Dict[str, List[str]]
) -> int:
    """
    Write a simple CSV with just keywords and their sources.
    
    Args:
        output_path: Path to output CSV
        discovered_keywords: Dict mapping seed keyword -> list of discovered keywords
        
    Returns:
        Number of rows written
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    rows_written = 0
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['keyword', 'source_seed'])
        
        for seed_keyword, keywords in discovered_keywords.items():
            for keyword in keywords:
                writer.writerow([keyword, seed_keyword])
                rows_written += 1
    
    logger.info(f"Wrote {rows_written} keywords to {output_path}")
    return rows_written

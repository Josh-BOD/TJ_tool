#!/usr/bin/env python3
"""
Parallel Ad Pauser Launcher

Automatically splits your Campaign CSV and runs multiple ad pauser scripts in parallel.
Each worker gets its own Campaign CSV file but shares the same Creative IDs CSV.
"""

import sys
import subprocess
import time
import csv
from pathlib import Path
from typing import List
import os

def split_campaign_csv(input_csv: Path, output_dir: Path, num_workers: int) -> List[Path]:
    """
    Split Campaign CSV into N parts.
    
    Returns:
        List of paths to temporary CSV files
    """
    print(f"📄 Reading {input_csv}...")
    
    # Read campaigns
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        all_rows = list(reader)
    
    print(f"✓ Found {len(all_rows)} campaigns")
    
    # Split into N groups
    chunk_size = (len(all_rows) + num_workers - 1) // num_workers
    chunks = [all_rows[i:i + chunk_size] for i in range(0, len(all_rows), chunk_size)]
    
    # Create temporary CSV files
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_csvs = []
    
    for i, chunk in enumerate(chunks, 1):
        temp_csv = output_dir / f"temp_campaigns_{i}.csv"
        
        with open(temp_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(chunk)
        
        temp_csvs.append(temp_csv)
        print(f"  ✓ Created {temp_csv.name} with {len(chunk)} campaigns")
    
    return temp_csvs


def launch_worker(worker_id: int, creative_csv: Path, campaign_csv: Path, 
                  dry_run: bool = False, screenshots: bool = False) -> subprocess.Popen:
    """Launch a worker process."""
    print(f"\n🚀 Launching Worker {worker_id}...")
    print(f"   Campaigns CSV: {campaign_csv.name}")
    print(f"   Creative IDs CSV: {creative_csv.name}")
    
    # Use absolute path to Python in venv
    python_exe = Path(__file__).parent / "venv" / "bin" / "python"
    script = Path(__file__).parent / "Pause_ads_V1.py"
    
    # Create log file for this worker
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"ad_pauser_worker_{worker_id}.log"
    
    # Build command
    cmd = [
        str(python_exe),
        str(script),
        "--creatives", str(creative_csv),
        "--campaigns", str(campaign_csv)
    ]
    
    if dry_run:
        cmd.append("--dry-run")
    
    if screenshots:
        cmd.append("--screenshots")
    
    # Launch process with log file
    with open(log_file, 'w') as f:
        process = subprocess.Popen(
            cmd,
            stdout=f,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, 'WORKER_ID': str(worker_id)}
        )
    
    print(f"   PID: {process.pid}")
    print(f"   Log: {log_file}")
    return process


def monitor_workers(processes: List[subprocess.Popen]):
    """Monitor all worker processes."""
    print("\n" + "="*70)
    print("MONITORING WORKERS")
    print("="*70)
    print("\n💡 Press Ctrl+C to stop all workers\n")
    
    try:
        while True:
            # Check if all processes finished
            statuses = [p.poll() for p in processes]
            
            if all(status is not None for status in statuses):
                print("\n✓ All workers finished!")
                break
            
            # Show status
            running = sum(1 for s in statuses if s is None)
            finished = len(statuses) - running
            
            print(f"\r⏳ Workers: {running} running, {finished} finished", end='', flush=True)
            
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n\n⚠ Stopping all workers...")
        stop_all_workers(processes)


def stop_all_workers(processes: List[subprocess.Popen]):
    """Stop all worker processes."""
    for i, process in enumerate(processes, 1):
        if process.poll() is None:  # Still running
            print(f"  Stopping Worker {i}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def cleanup(temp_files: List[Path], num_workers: int):
    """Clean up temporary files and show summary."""
    print("\n🧹 Cleaning up temporary files...")
    for temp_file in temp_files:
        try:
            if temp_file.exists():
                temp_file.unlink()
                print(f"  ✓ Removed {temp_file.name}")
        except Exception as e:
            print(f"  ⚠ Could not remove {temp_file.name}: {e}")
    
    # Show log file locations
    print("\n📊 WORKER LOGS:")
    log_dir = Path(__file__).parent / "logs"
    for i in range(1, num_workers + 1):
        log_file = log_dir / f"ad_pauser_worker_{i}.log"
        if log_file.exists():
            print(f"  Worker {i}: {log_file}")
    
    # Show report locations
    print("\n📊 PAUSE REPORTS:")
    report_dir = Path(__file__).parent / "data" / "reports" / "Ad_Pause"
    if report_dir.exists():
        reports = sorted(report_dir.glob("pause_report_*.md"), reverse=True)
        for report in reports[:num_workers]:  # Show latest N reports
            print(f"  {report.name}: {report}")
    
    print("\n💡 To see detailed results, check the files above")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Parallel Ad Pauser Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with 2 workers (safest)
  python3 run_parallel_ad_pauser.py --creatives data/input/Ad_Pause/creative_ids.csv --campaigns data/input/Ad_Pause/campaign_ids.csv --workers 2
  
  # Run with 3 workers (faster)
  python3 run_parallel_ad_pauser.py --creatives data/input/Ad_Pause/creative_ids.csv --campaigns data/input/Ad_Pause/campaign_ids.csv --workers 3
  
  # Dry run to test
  python3 run_parallel_ad_pauser.py --creatives data/input/Ad_Pause/creative_ids.csv --campaigns data/input/Ad_Pause/campaign_ids.csv --workers 2 --dry-run

How it works:
  1. Reads your Campaign IDs CSV
  2. Splits campaigns into N groups
  3. Creates temporary Campaign CSV files
  4. Launches N browser instances (one per group)
  5. Each browser pauses ads using the same Creative IDs CSV
  6. Cleans up temp files when done
        """
    )
    
    parser.add_argument(
        "--creatives",
        type=Path,
        required=True,
        help="Creative IDs CSV file (shared by all workers)"
    )
    
    parser.add_argument(
        "--campaigns",
        type=Path,
        required=True,
        help="Campaign IDs CSV file (will be split among workers)"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        choices=range(1, 6),
        help="Number of parallel workers (1-5, recommended: 2-3)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without actually pausing ads"
    )
    
    parser.add_argument(
        "--screenshots",
        action="store_true",
        help="Take screenshots during execution"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.creatives.exists():
        print(f"✗ Creative IDs file not found: {args.creatives}")
        return 1
    
    if not args.campaigns.exists():
        print(f"✗ Campaign IDs file not found: {args.campaigns}")
        return 1
    
    print("="*70)
    print(f"PARALLEL AD PAUSER - {args.workers} Workers")
    print("="*70)
    
    # Create temp directory
    temp_dir = Path(__file__).parent / "data" / "temp"
    
    # Split campaign CSV
    temp_campaign_csvs = split_campaign_csv(args.campaigns, temp_dir, args.workers)
    
    # Launch workers
    processes = []
    for i, campaign_csv in enumerate(temp_campaign_csvs, 1):
        process = launch_worker(
            worker_id=i,
            creative_csv=args.creatives,
            campaign_csv=campaign_csv,
            dry_run=args.dry_run,
            screenshots=args.screenshots
        )
        processes.append(process)
        time.sleep(3)  # Stagger launches to avoid conflicts
    
    # Monitor workers
    try:
        monitor_workers(processes)
    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
        stop_all_workers(processes)
    
    # Cleanup
    cleanup(temp_campaign_csvs, args.workers)
    
    print("\n✓ All done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())


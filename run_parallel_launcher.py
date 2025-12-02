#!/usr/bin/env python3
"""
Parallel Campaign Launcher

Automatically splits your CSV and runs multiple campaign creation scripts in parallel.
Each worker gets its own CSV file and browser instance.
"""

import sys
import subprocess
import time
import csv
from pathlib import Path
from typing import List, Dict
import signal
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from campaign_automation_v2.csv_parser import parse_csv


class ParallelLauncher:
    """Launches multiple campaign creation workers in parallel."""
    
    def __init__(self, num_workers=2):
        self.num_workers = num_workers
        self.processes = []
        self.temp_files = []
        
    def split_csv(self, input_csv: Path, output_dir: Path) -> List[Path]:
        """
        Split CSV into N parts based on enabled campaigns.
        
        Returns:
            List of paths to temporary CSV files
        """
        print(f"📄 Reading {input_csv}...")
        
        # Read original CSV
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            all_rows = list(reader)
        
        # Filter enabled campaigns
        enabled_rows = [row for row in all_rows if row.get('enabled', '').upper() == 'TRUE']
        disabled_rows = [row for row in all_rows if row.get('enabled', '').upper() != 'TRUE']
        
        print(f"✓ Found {len(enabled_rows)} enabled campaigns")
        print(f"  ({len(disabled_rows)} disabled campaigns will be skipped)")
        
        # Split enabled campaigns into N groups
        chunk_size = (len(enabled_rows) + self.num_workers - 1) // self.num_workers
        chunks = [enabled_rows[i:i + chunk_size] for i in range(0, len(enabled_rows), chunk_size)]
        
        # Create temporary CSV files
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_csvs = []
        
        for i, chunk in enumerate(chunks, 1):
            temp_csv = output_dir / f"temp_batch_{i}.csv"
            
            with open(temp_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(chunk)
            
            temp_csvs.append(temp_csv)
            self.temp_files.append(temp_csv)
            print(f"  ✓ Created {temp_csv.name} with {len(chunk)} campaigns")
        
        return temp_csvs
    
    def launch_worker(self, worker_id: int, csv_file: Path, script: Path) -> subprocess.Popen:
        """Launch a worker process."""
        print(f"\n🚀 Launching Worker {worker_id}...")
        print(f"   CSV: {csv_file.name}")
        
        # Use absolute path to Python in venv
        python_exe = Path(__file__).parent / "venv" / "bin" / "python3"
        
        # Create log file for this worker
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"worker_{worker_id}.log"
        
        # Launch process with log file
        with open(log_file, 'w') as f:
            process = subprocess.Popen(
                [str(python_exe), str(script)],
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True,
                env={**os.environ, 'WORKER_ID': str(worker_id)}
            )
        
        self.processes.append(process)
        print(f"   Log: {log_file}")
        return process
    
    def monitor_workers(self):
        """Monitor all worker processes."""
        print("\n" + "="*70)
        print("MONITORING WORKERS")
        print("="*70)
        print("\n💡 Press Ctrl+C to stop all workers\n")
        
        try:
            while True:
                # Check if all processes finished
                statuses = [p.poll() for p in self.processes]
                
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
            self.stop_all_workers()
    
    def stop_all_workers(self):
        """Stop all worker processes."""
        for i, process in enumerate(self.processes, 1):
            if process.poll() is None:  # Still running
                print(f"  Stopping Worker {i}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
    
    def cleanup(self):
        """Clean up temporary files and show summary."""
        print("\n🧹 Cleaning up temporary files...")
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    print(f"  ✓ Removed {temp_file.name}")
            except Exception as e:
                print(f"  ⚠ Could not remove {temp_file.name}: {e}")
        
        # Show log file locations
        print("\n📊 WORKER LOGS:")
        log_dir = Path(__file__).parent / "logs"
        for i in range(1, self.num_workers + 1):
            log_file = log_dir / f"worker_{i}.log"
            if log_file.exists():
                print(f"  Worker {i}: {log_file}")
        
        print("\n💡 To see detailed results, check the log files above")
    
    def run(self, input_csv: Path, worker_script: Path):
        """Run the parallel launcher."""
        print("="*70)
        print(f"PARALLEL CAMPAIGN LAUNCHER - {self.num_workers} Workers")
        print("="*70)
        
        # Create temp directory
        temp_dir = Path(__file__).parent / "data" / "temp"
        
        # Split CSV
        csv_files = self.split_csv(input_csv, temp_dir)
        
        # Launch workers
        for i, csv_file in enumerate(csv_files, 1):
            self.launch_worker(i, csv_file, worker_script)
            time.sleep(2)  # Stagger launches slightly
        
        # Monitor workers
        self.monitor_workers()
        
        # Cleanup
        self.cleanup()
        
        print("\n✓ All done!")


def create_worker_script():
    """
    Create a modified version of the sync script that reads from environment variable.
    """
    worker_script_path = Path(__file__).parent / "create_campaigns_v2_sync_worker.py"
    
    # Read original script
    original_script = Path(__file__).parent / "create_campaigns_v2_sync.py"
    
    with open(original_script, 'r') as f:
        content = f.read()
    
    # Modify to accept CSV from environment variable
    modified_content = content.replace(
        'input_file = Path("data/input/Niche-Stepmom_v2.csv")',
        '''import os
    worker_id = os.environ.get('WORKER_ID', '1')
    input_file = Path(f"data/temp/temp_batch_{worker_id}.csv")
    print(f"\\n[Worker {worker_id}] Using CSV: {input_file}")'''
    )
    
    with open(worker_script_path, 'w') as f:
        f.write(modified_content)
    
    return worker_script_path


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Parallel Campaign Creation Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with 2 workers (safest)
  python3 run_parallel_launcher.py --input data/input/Niche-Stepmom_v2.csv --workers 2
  
  # Run with 3 workers (faster)
  python3 run_parallel_launcher.py --input data/input/Niche-Stepmom_v2.csv --workers 3

How it works:
  1. Reads your CSV
  2. Splits enabled campaigns into N groups
  3. Creates temporary CSV files
  4. Launches N browser instances (one per group)
  5. Each browser runs independently
  6. Cleans up temp files when done
        """
    )
    
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input CSV file with campaign definitions"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        choices=range(1, 6),
        help="Number of parallel workers (1-5, recommended: 2-3)"
    )
    
    args = parser.parse_args()
    
    # Validate input
    if not args.input.exists():
        print(f"✗ Input file not found: {args.input}")
        return 1
    
    # Create worker script
    print("📝 Creating worker script...")
    worker_script = create_worker_script()
    print(f"✓ Created {worker_script.name}\n")
    
    # Run launcher
    launcher = ParallelLauncher(num_workers=args.workers)
    
    try:
        launcher.run(args.input, worker_script)
        return 0
    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
        launcher.stop_all_workers()
        launcher.cleanup()
        return 130
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        launcher.stop_all_workers()
        launcher.cleanup()
        return 1


if __name__ == "__main__":
    sys.exit(main())


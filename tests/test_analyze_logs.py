# tests/test_analyze_logs.py

import pytest
import os
import subprocess
import shutil
import glob

def test_analyze_logs_sample(tmp_path):
    """
    Copy sample logs to tmp_path, run analyze_logs.py on them,
    verify we get analysis_subplots.png and analysis_summary.md.
    """
    # 1) Ensure our sample logs folder exists
    sample_dir = os.path.join("tests", "sample_logs")
    assert os.path.exists(sample_dir), (
        "Sample logs folder missing. "
        "Please create tests/sample_logs/ with machine_1.log, machine_2.log, machine_3.log"
    )

    # 2) Copy them into the tmp_path
    for fname in ["machine_1.log", "machine_2.log", "machine_3.log"]:
        src = os.path.join(sample_dir, fname)
        dst = os.path.join(tmp_path, fname)
        shutil.copyfile(src, dst)

    # 3) Expand the glob ourselves to get actual file paths
    log_files = glob.glob(os.path.join(str(tmp_path), "machine_*.log"))
    assert len(log_files) == 3, (
        f"Expected 3 machine logs, found {len(log_files)} in {tmp_path}"
    )

    # 4) Call analyze_logs.py, passing the real filenames (not a wildcard)
    cmd = ["python", "analyze_logs.py"] + log_files
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"analyze_logs.py failed: {proc.stderr}"

    # 5) Check for output files
    subplots_path = os.path.join(str(tmp_path), "analysis_subplots.png")
    summary_md = os.path.join(str(tmp_path), "analysis_summary.md")
    assert os.path.exists(subplots_path), "analysis_subplots.png not found"
    assert os.path.exists(summary_md), "analysis_summary.md not found"

    # 6) Optionally, read summary_md to confirm it has expected text
    with open(summary_md, "r") as f:
        summary_content = f.read()
        assert "Summary Table" in summary_content, "Expected 'Summary Table' in analysis_summary.md"
        assert "Final Drift" in summary_content, "Expected 'Final Drift' in analysis_summary.md"

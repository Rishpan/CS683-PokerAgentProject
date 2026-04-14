import os
import subprocess
import sys
import time


PROJECT_ROOT = "/home/lucas/CS683-PokerAgentProject"
ADVANCED_PID = 185646
SUPERIOR_PID = 185647
OUTFILES = {
    "discounted_mccfr_plus_vs_advanced": "/tmp/poker_compare_discounted_mccfr_plus_vs_advanced.txt",
    "discounted_mccfr_plus_vs_threshold": "/tmp/poker_compare_discounted_mccfr_plus_vs_threshold.txt",
    "advanced_vs_threshold": "/tmp/poker_compare_advanced_vs_threshold.txt",
}


def pid_alive(pid):
  try:
    os.kill(pid, 0)
    return True
  except OSError:
    return False


def wait_for_training():
  print("Waiting for current training jobs to finish...")
  while pid_alive(ADVANCED_PID) or pid_alive(SUPERIOR_PID):
    time.sleep(10)
  print("Training finished. Starting comparisons...")


def run_and_capture(label, args, outfile):
  print(f"Running {label} ...")
  with open(outfile, "w", encoding="utf-8") as handle:
    subprocess.run(args, cwd=PROJECT_ROOT, stdout=handle, stderr=subprocess.STDOUT, check=True)
  print(f"Saved {label} to {outfile}")


def main():
  wait_for_training()
  run_and_capture(
      "discounted_mccfr_plus_vs_advanced",
      [
          sys.executable,
          "compare_agents.py",
          os.path.join(
              PROJECT_ROOT,
              "lucas_agents",
              "discounted_mccfr_plus",
              "discounted_mccfr_plus_agent.py",
          ),
          os.path.join(PROJECT_ROOT, "lucas_agents", "advanced_cfr", "advanced_cfr_player.py"),
          "--games",
          "100",
          "--max-round",
          "100",
          "--initial-stack",
          "500",
          "--small-blind",
          "10",
      ],
      OUTFILES["discounted_mccfr_plus_vs_advanced"],
  )
  run_and_capture(
      "discounted_mccfr_plus_vs_threshold",
      [
          sys.executable,
          "compare_agents.py",
          os.path.join(
              PROJECT_ROOT,
              "lucas_agents",
              "discounted_mccfr_plus",
              "discounted_mccfr_plus_agent.py",
          ),
          os.path.join(PROJECT_ROOT, "lucas_agents", "condition_threshold_player.py"),
          "--games",
          "100",
          "--max-round",
          "100",
          "--initial-stack",
          "500",
          "--small-blind",
          "10",
      ],
      OUTFILES["discounted_mccfr_plus_vs_threshold"],
  )
  run_and_capture(
      "advanced_vs_threshold",
      [
          sys.executable,
          "compare_agents.py",
          os.path.join(PROJECT_ROOT, "lucas_agents", "advanced_cfr", "advanced_cfr_player.py"),
          os.path.join(PROJECT_ROOT, "lucas_agents", "condition_threshold_player.py"),
          "--games",
          "100",
          "--max-round",
          "100",
          "--initial-stack",
          "500",
          "--small-blind",
          "10",
      ],
      OUTFILES["advanced_vs_threshold"],
  )
  print("All comparisons finished.")


if __name__ == "__main__":
  main()

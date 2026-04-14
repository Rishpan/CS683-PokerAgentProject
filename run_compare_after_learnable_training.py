import os
import subprocess
import sys
import time

PROJECT_ROOT = "/home/lucas/CS683-PokerAgentProject"
TRAIN_PID = 193633


def pid_alive(pid):
  try:
    os.kill(pid, 0)
    return True
  except OSError:
    return False


def wait_for_training():
  print("Waiting for learnable training job to finish...")
  while pid_alive(TRAIN_PID):
    time.sleep(10)
  print("Training finished. Starting 500-game comparisons...")


def run(label, a_path, b_path, outfile):
  with open(outfile, "w", encoding="utf-8") as handle:
    subprocess.run(
        [
            sys.executable,
            "compare_agents.py",
            a_path,
            b_path,
            "--games",
            "500",
            "--max-round",
            "100",
            "--initial-stack",
            "500",
            "--small-blind",
            "10",
        ],
        cwd=PROJECT_ROOT,
        stdout=handle,
        stderr=subprocess.STDOUT,
        check=True,
    )
  print(f"done={label} outfile={outfile}")


def main():
  wait_for_training()
  run(
      "learnable_vs_advanced_cfr",
      os.path.join(PROJECT_ROOT, "lucas_agents", "learnable_discounted_mccfr", "learnable_discounted_mccfr_agent.py"),
      os.path.join(PROJECT_ROOT, "lucas_agents", "advanced_cfr", "advanced_cfr_player.py"),
      "/tmp/learnable_vs_advanced_cfr_500.txt",
  )
  run(
      "learnable_vs_discounted_mccfr_plus",
      os.path.join(PROJECT_ROOT, "lucas_agents", "learnable_discounted_mccfr", "learnable_discounted_mccfr_agent.py"),
      os.path.join(PROJECT_ROOT, "lucas_agents", "discounted_mccfr_plus", "discounted_mccfr_plus_agent.py"),
      "/tmp/learnable_vs_discounted_mccfr_plus_500.txt",
  )
  print("all_done")


if __name__ == "__main__":
  main()

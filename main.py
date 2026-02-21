"""CLI entry point for AI Debate Lab."""
from debate import run_debate, save_run

if __name__ == "__main__":
    topic = input("Debate topic: ").strip()
    if not topic:
        print("Topic cannot be empty.")
        exit(1)
    run_data = run_debate(topic)
    save_run(run_data)
    print(f"\nSaved to runs/{run_data['run_id']}.json")

# Newsletter Agent v1

## What this is
A multi-agent system that helps creators build and position a newsletter. Each agent is independent, shares a common output format, and reads the strategy brief produced by the strategy agent before doing anything.

## Agent architecture
- **Strategy agent** (`agents/strategy/agent.py`) — runs once per creator. Produces the strategy brief. All other agents read this first.
- Writer agent — coming soon
- Monetisation agent — coming soon
- Performance agent — coming soon

## Shared output format
Every agent reads from and writes to `briefs/<creator-slug>/strategy-brief.json` (canonical) and `briefs/<creator-slug>/strategy-brief.md` (human-readable).

## Internal state
All session state, learnings, and intermediate data lives in `.agent/<creator-slug>/`. This is never edited manually. All changes go through the CLI.

## Agent specs
- [Strategy agent](docs/specs/strategy-agent.md)

## How to run
```bash
python agents/strategy/agent.py --creator <creator-slug>
```

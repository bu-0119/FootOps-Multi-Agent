---
name: footops-player-role-analysis
description: Resolve and execute evidence-gated multi-match player role analysis from natural-language football questions.
---

# Player Role Analysis

Use this skill when the user asks about one player's position, touch zones,
receiving position, recent role, or multi-match role trend.

## Workflow

1. Extract only what the user explicitly states: player, competition, season,
   and a window from 2 to 10 matches.
2. Treat optional scope hints supplied by the application as user constraints.
3. If `scope_hint` already contains both `competition_id` and `season_id`, use
   them directly. Otherwise resolve them with `search_competitions`.
4. If `scope_hint` already contains both `player` and `player_id`, use them
   directly. Otherwise resolve the player with `search_players`.
5. If a required value is missing or candidates are ambiguous, stop and return
   `clarification_required` with one concise question.
6. When exactly one scope is verified, call `run_player_role_analysis` once.
7. Return `completed` only when that tool reports `completed`. The Harness will
   use the stored workspace, not any metric copied into model text.

## Boundaries

- Current deterministic findings cover position and touch zones, forward
  passing, progressive carries, key passes, and shot involvement across 2 to
  10 matches. A two-match comparison is descriptive and especially sensitive
  to opponent, score, and playing time.
- Shot involvement means shots plus key passes. Do not claim goals, assists,
  xG, shots on target, injuries, live form, causality, or tactical intent
  unless a later verified tool explicitly supports them.
- Do not choose a season just because it is the newest or most familiar.
- Do not expose chain-of-thought. Return only a concise decision and user-facing
  explanation.

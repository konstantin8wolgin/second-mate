# Future product notes

Status: discovery notes only. These are not approved implementation work.

## Conversational steering

Second Mate should eventually let the project owner speak or write in a live
session while work is underway. The assistant should explain the current
Direction, active packet, evidence, uncertainty, and next proposed move in
plain language. The owner can then reshape the route, pause work, or redirect
it before the system commits to more work.

## Bounded autonomy, not opaque chains

An agent may work independently inside one approved, legible packet. It must
not treat an earlier prompt as permission to execute an unbounded chain for
hours without making its current understanding visible. Return to the owner at
meaningful route or product checkpoints, and immediately for a material
Direction conflict.

## Future interaction model

The desired later experience is a short loop:

1. The owner asks what the system is doing and why.
2. The assistant reports the current state and evidence, not private reasoning.
3. The owner may continue, reshape, pause, or replace the route.
4. The next packet is updated only when that change materially affects the
   agreed Direction, foundation, or delivery route.

This should complement—not replace—the general document-first workflow. Voice
is one optional interface; typed conversation and editable documents must work
equally well.

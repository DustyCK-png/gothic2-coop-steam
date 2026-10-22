# Gameplay synchronization beta

Verified assertions are recorded in party-test.json. This package builds on the host-save beta; host-save regressions require native-pair-test.json and native-intro-test.json from this build.

Fixed in source:
- Dialogue hotfix 0.2.1: the real oCNpc::OnMessage dispatcher inlines PROCESSINFOS. Delaying SetNpc alone orphaned the information manager after the job saw the previous finished flag. Gate the native job before dispatch, retain it until grant, and run initialization only from that job.
- Clear native tracking when the job is deleted, hold a reference while inspecting it, cancel pending jobs on denial/timeout and clear talk links. Block rapid new starts while a commit awaits acknowledgement.
- Preserve in-flight requests across unrelated idle state snapshots. Protect pending/active talk NPCs from remote update resets and allow their local dialogue animations.
- The old direct-SetNpc QA did not prove an actionable dialogue menu. The revised QA checks an active opened choice view, native STOPPROCESSINFOS and another NPC interaction.

- A bounded five-second pending queue handles a client XP claim arriving before lethal damage is applied by the host; dead/KO/zero-HP confirmation is required.
- VM XP interception shares native rewards and leveling; authenticated source event IDs preserve equal legitimate awards, repeated packets do not award twice.
- Combat reward identities include world and victim; one reward per victim per saved campaign (revival does not reset the reward).
- Distant player puppet is removed from maps before destruction and recreated with cached appearance and equipment. Disconnect iteration no longer invalidates its iterator.
- Host dialogue lease gates SetNpc. Keep acknowledgements and an 8-second client deadline close a stalled dialogue before the host 15-second release.
- Full validation precedes quest state changes. Known quest globals, native journal and nonpermanent told flags replicate; changed dialogue globals expand the shared set.
- COOPGAME.SAV records reward deduplication and shared names alongside native snapshots. Save completion notifications are deferred until the native save wrapper returns.

Open / not a claim of complete co-op:
- Shared quest flags, journal and told flags are not complete world-script authority. NPC spawn/despawn, quest items, NPC routines, attitudes, world triggers and teleport side effects need individual synchronization and real quest tests. No full-game completion certification.
- Two accounts over actual Steam relay, level transitions, multiple friends, save/reload reward rollback and network fault/mutation coverage still require verification for this gameplay build.
- Cooperative play requires identical game scripts and this DLL on both peers. This is not compatible with upstream clients that lack the control protocol.
- Rewards during a late join do not backfill previous personal XP; restored host-owned profiles remain the source of personal progress.
- Persistent victim IDs use the upstream world-NPC naming scheme; total NPC-list changes in one world can invalidate its assumptions.
- An interrupted client dialogue is closed locally; arbitrary already-executed script side effects cannot be rolled back.

Upstream: Gothic-Workshop/GothicCoop, AGPL-3.0-or-later. Game files and saves must never be redistributed with the source package.

Open focused boundary: external cancellation of the pending conversation event by combat/cutscene/KillMessages during the handshake still needs its own native regression.
Artificially spawned combat-bot scenarios can occasionally time out; a passing local run is not a full real-world campaign certification.

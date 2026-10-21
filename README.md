# Gothic II Co-op over Steam вЂ” gameplay beta

Adaptations of [GothicCoop v60](https://github.com/Gothic-Workshop/GothicCoop) for Gothic II Night of the Raven 2.6 fix, Union 1.0m, Windows and Steam AppID 480. Requires a legally installed game on both PCs. Game files and proprietary runtime installations are not included in this repository.

**Verified on two real local game clients:** host and client combat rewards shared once, equal legitimate repeated rewards preserved, native level-up and learning points, player puppet distance respawn with equipment, one party-wide NPC dialogue lease, lease expiry closing the old conversation, quest flags/journal/told information replication, a native Lobart quest acceptance, and host-owned profile capture/restore/reconnect. See `tests/party-test.json`, `tests/native-pair-test.json`, `tests/native-intro-test.json`. The positive tests identify the tested DLL by SHA256; mutation checks detect disabled fixes.

**Not full shared quest authority:** quest items, NPC creation/routines/attitudes, world triggers and teleport side effects are not fully synchronized. Full campaign, transitions, several friends, old-slot reward rollback and two different real Steam accounts remain unverified. This is an experimental beta.

[РџРѕР»РЅР°СЏ РёРЅСЃС‚СЂСѓРєС†РёСЏ РїРѕ-СЂСѓСЃСЃРєРё](INSTALL-RU.md) В· [РЎРѕС…СЂР°РЅРµРЅРёСЏ Сѓ С…РѕСЃС‚Р°](HOST-SAVES-RU.md) В· [Known issues](BUGS.md)

## Build

Install Visual Studio C++, Windows SDK, Git and CMake. Run `bootstrap.ps1` in PowerShell to fetch the pinned upstream commit and apply `patches/GothicCoop.patch`. Existing vendor trees are never overwritten.

```powershell
cmake -S . -B build -G "Visual Studio 18 2026" -A Win32
cmake --build build --config Release
cmake -S steam -B steam-build -G "Visual Studio 18 2026" -A Win32
cmake --build steam-build --config Release
```

The plugin is AGPL-3.0-or-later; relay code is MIT-derived. Upstream dependency licenses apply. Do not distribute game binaries, worlds or player snapshots.

## Install / update

For a fresh manual installation, create a separate Latin-path copy, e.g. `C:\Games\Gothic2Coop`, install Union 1.0m from its official distribution, put the compiled plugin in `system/Autorun`, and the upstream GothicCoopConfig.json in `system`. Create `SteamLink` with the compiled G2Steam.exe, a legitimately obtained official **x86** steam_api.dll and steam_appid.txt containing `480`. Never use mock_steam_api.dll for play. Copy `steam/Steam-Host-Saves.cmd` and `steam/Steam-Join-Saves.cmd` to the game root. Install matching builds on both PCs. Keep the source package with redistributed plugin builds.

The GameplayBeta update archive is for an existing HostSaves install: close the game and run Update.cmd. It backs up the old DLL and leaves saves/settings untouched. The complete Gothic2Coop-Steam.zip described in INSTALL-RU.md is the separately prepared local installation bundle; it is not needed when following the manual source installation above.

## Play through Friends в†’ Join Game

1. Start Steam on both PCs with different online accounts added as friends.
2. Host: Steam-Host-Saves.cmd в†’ load the intended slot/new game в†’ finish the introduction в†’ F1 in the world.
3. Friend: Steam-Join-Saves.cmd в†’ load the world and finish dialogue в†’ Shift+Tab в†’ Friends в†’ host в†’ Join Game. F2 is not needed for this path. Keep both launchers open.
4. Only one player can talk to any NPC at a time. A stalled client's dialogue closes when its lease expires.
5. Only the host saves. Finish dialogues, stop gameplay actions, save through the menu and wait for **Host saves: complete** before quitting. Back up **Saves and CoopHostSaves together**. Next time load the same host slot and join with the same Steam account. Restart the session before loading a different slot.

Shift+Tab opens Steam overlay, F10 opens the lobby invite window, Shift+F10 opens friends. Steam may display Spacewar because AppID 480 is a test integration, not official Gothic II multiplayer. Invites are never sent just by opening the invite window.

Keep Steam overlay enabled. In SystemPack.ini use `[DEBUG] SteamOverlayFix=0` and `OptimizeVB=0`, and keep GameOverlayTakeControl=True. The plugin loads the API from SteamLink; no extra API copy in system is needed. Direct Gothic2.exe launch does not enable launcher integration.

## Testing

`tests/party_qa.py` uses two disposable installations at C:/Games/Gothic2Coop-GameplayQA and C:/Games/Gothic2Coop-TestClient. Each launches its own fresh game and exits its own processes; never point it at valuable saves. Run with an argument `xp`, `render`, `dialogue` or `quest` for a deliberate QA-only fault: that test must fail. The verified DLL hook addresses require the exact supported 2.6 fix executable. Same-PC QA changes verified singleton checks only in suspended test-process memory; no EXE is modified on disk.

`tests/native_pair_qa.py` checks native capture/restore; `tests/native_intro_qa.py` checks a new free-slot checkpoint after Xardas. Relay tests in steam use a mock Steam API. These tests do not replace a real two-account Internet playtest.

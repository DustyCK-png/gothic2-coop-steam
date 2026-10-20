# Gothic II Co-op over Steam (experimental)

Local adaptations of [GothicCoop v60](https://github.com/Gothic-Workshop/GothicCoop), with a Steam UDP relay. Requires your own Gothic II: Night of the Raven 2.6 (fix), Union 1.0m, Windows, and two Steam accounts.

**Status:** Union and the plugin load; new game and host server startup work. UDP relay mock tests and real Steam API / friends-only lobby creation passed. Two real accounts over the Internet, full campaign progression, save recovery and world transitions are NOT verified. On the test PC, starting a second game process returned exit code 1; each client works separately.

## Build

Install Visual Studio C++ and Windows SDK, CMake and Git. Run `./bootstrap.ps1` from PowerShell to fetch the pinned upstream source and apply the included patch. Dependencies remain in upstream; game files and proprietary runtimes are not redistributed here.

```powershell
cmake -S . -B build -G "Visual Studio 18 2026" -A Win32
cmake --build build --config Release
cmake -S steam -B steam-build -G "Visual Studio 18 2026" -A Win32
cmake --build steam-build --config Release
```

The game plugin is AGPL-3.0. The relay is MIT-derived; see steam/LICENSE and file attribution. Upstream SDK/dependency licenses continue to apply.

## Install into a separate game copy

Use a Latin-only path such as `C:\Games\Gothic2Coop`. Install Union 1.0m from its official distribution and follow its instructions. Union may change executable compatibility and DEP settings on first launch and request a restart. Put the built `GothicCoop_G2A.dll` into `system/Autorun`. Copy `vendor/GothicCoop/GothicCoopConfig.json` into `system`.

Create `SteamLink` inside the game copy. Put the built `G2Steam.exe` and a legally obtained official x86 `steam_api.dll` beside it. Create `steam_appid.txt` containing `480`. Do not use the mock DLL for real play. AppID 480 is the Spacewar test application; this is not official Gothic II multiplayer.

Start Steam and run from SteamLink:

```powershell
.\G2Steam.exe host --game "C:\Games\Gothic2Coop"
# Friend on another PC:
.\G2Steam.exe join --game "C:\Games\Gothic2Coop"
```

Keep the relay open. Both players start a new game in the same world and finish the opening dialogue. Host presses F1, then client presses F2. Subsequent F2 toggles sync pause. Steam mode changes server, port and loopbackOnly in JSON, preserving other preferences and a backup. No router port forwarding is required.

This mod does not guarantee shared quest flags or a single authoritative campaign save. Use matching important dialogue choices and separate coordinated saves. See BUGS.md.

## Test the relay

After building both Steam targets, create an empty `local` directory and run `python steam/test_relay.py`. This uses a mock Steam API, validates packets and JSON preservation, and does not prove Internet gameplay. Real API checks: `G2Steam.exe check --no-launch` and `G2Steam.exe check-lobby --no-launch` from SteamLink.

## Changes

Removed automatic UPnP router mapping; added optional loopback binding and a Gothic II-specific Steam lobby tag; added optional in-game QA mode via G2_COOP_QA=host/client. QA auto-starts a fresh game and writes state; leave this variable unset during normal play.

Credits: Gothic-Workshop / GothicCoop contributors; Union team; cranebeaker/deus-ex-coop relay contributors. No game assets, saves, Steam SDK binaries, or Union runtime binaries are included.

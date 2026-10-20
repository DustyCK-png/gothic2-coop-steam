# Gothic II Co-op v60 local variant

Fixed: F1 invoked UPnP mapping code that can delete an existing router mapping. Removed for this Steam package.

Fixed: Steam mode now binds the game server to localhost and keeps JSON preferences plus a backup. Uses a Gothic II-specific lobby tag.

Open: second Gothic2.exe instance exits with code 1 on this PC. Separate executable name is under test; no changes are made to original binaries.

Open: full campaign state, dialogue choices, save/transition recovery, real two-account Steam gameplay, long sessions and packet-loss gameplay tests remain unverified.

Open upstream: SyncNpcs erases the current element from a range-for iteration. Error diagnostics assumes at least ten resolved core frames. These have not been changed without a reproducing test.

Runtime requirements: Union rejects Cyrillic install paths and can change executable compatibility/DEP settings at first launch.

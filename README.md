# YTKACE — official releases in SideStore

A personal SideStore/AltStore source that links **directly to the original developer's IPAs** from [`itzzace/ytkace`](https://github.com/itzzace/ytkace). It uses the update-feed format and GitHub Actions approach found in [`mrdrvt99/Altstore-Repository`](https://github.com/mrdrvt99/Altstore-Repository), but **does not link to its modified builds** or repackage the official IPAs.

## Setup on GitHub

1. Create a **public** repository called `ytkace-sidestore-source` in the `NuclearInsanity` GitHub account. Its default branch should be `main`.
2. Add these files to that repository, preserving their relative paths:
   - `.github/workflows/update-source.yml`
   - `scripts/sync.py`
   - `tests/test_sync.py`
   - `README.md`
3. Check **Settings → Actions → General → Workflow permissions**. Allow **Read and write permissions** if GitHub Actions cannot commit the generated source. The workflow explicitly requests `contents: write`.
4. Select **Actions → Update official YTKACE SideStore source → Run workflow**. Once the workflow succeeds, `source.json` will be committed to `main`.
5. On your iPhone, go to **SideStore → Sources → +** and paste:

   `https://raw.githubusercontent.com/NuclearInsanity/ytkace-sidestore-source/main/source.json`

6. Install YTKACE through that source to establish a source-associated installation. The source gets checked every six hours (GitHub Actions schedules are best effort), and subsequent releases will appear in SideStore when its feed refreshes.

**No GitHub Pages, personal access token, or paid services required.** The workflow's `GITHUB_TOKEN` supplies the necessary read/write access.

## How it works

- The workflow checks the **public official releases API** for `itzzace/ytkace`, ignoring drafts and pre-releases.
- It selects only the IPA asset named like `YTKACE_1.1.4_YouTube_21.42.4.ipa`, explicitly excluding `iOS16` variants.
- Only when a new upstream release is found, the workflow downloads that **official** IPA to the temporary GitHub Actions runner and reads its `Info.plist`. This ensures `CFBundleShortVersionString`, `CFBundleVersion`, actual bundle ID, and minimum iOS version match what SideStore expects. It doesn't modify or host the IPA.
- It writes `source.json` pointing **directly to the developer's GitHub release asset**, keeps up to 15 prior release entries, and commits the file only if there are changes.
- The feed includes top-level `downloadURL` and `versions[]`, following the compatibility pattern used in mrdrvt99's source.

## Notes

- Installing apps via SideStore and periodically refreshing their signatures remain separate from updating the app listing. **GitHub Actions cannot silently install an update onto your phone.**
- If migrating a manually installed YTKACE or another YouTube mod, back up local settings and downloads; changing the installation method can require deleting and reinstalling the app. These builds often share the real `com.google.ios.youtube` bundle ID.
- A new YTKACE tweak release with exactly the same base YouTube app version *and* internal build number might not trigger SideStore's update detection. In that case, install the latest official IPA manually.
- The listing uses the official GitHub organisation's profile image as its icon. Change `ICON_URL` in `scripts/sync.py` if you'd rather use a YouTube icon.
- The feed is **your personal feed**, not an official SideStore feed published by the YTKACE developer. The IPA source remains the developer's official GitHub.

## Local tests

```bash
python3 -m unittest discover -s tests -v
# From the project root, if network is allowed:
GITHUB_REPOSITORY=NuclearInsanity/ytkace-sidestore-source python3 scripts/sync.py
python3 -m json.tool source.json >/dev/null
```

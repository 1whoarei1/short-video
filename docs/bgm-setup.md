# Optional sampled music setup

The composer is the AI in your Codex workspace. It authors an original score and
MIDI rather than selecting a fixed song template. FluidSynth renders notes through
a SoundFont sample bank; FFmpeg handles final audio mixing. No music-generation
model, GPU, account, or music API key is required for this route.

## Check first

Run `python scripts/setup_bgm.py`. This checks dependencies only and never downloads
anything. Missing optional music dependencies do not stop ordinary video setup.
FFmpeg and ffprobe must be available on PATH. Rendering may need the Python
dependencies reported by the music command as well.

## FluidSynth

Use the official platform packages listed at <https://www.fluidsynth.org/download/>.
On Windows, use the official FluidSynth release matching your Python architecture.
Keep all accompanying DLLs together. Place the release's `bin` contents under
`.cache/fluidsynth/bin/`, or set `FLUIDSYNTH_LIBRARY` to the absolute path of its
FluidSynth DLL. No administrator changes are required for a portable release.
The Python renderer adds that DLL's directory to its own process search path.
On Linux or macOS use the official distribution/package-manager build, or set
`FLUIDSYNTH_LIBRARY` to a compatible shared library.

Only Linux rendering is validated in this project's automated cloud tests.
Windows dependency loading still needs first-use verification on the user's
machine. A found DLL alone is not treated as successful synthesis.

## Sample library

After approving the download, run:

`python scripts/setup_bgm.py --install-soundfont`

This obtains FluidR3 GM 3.1 from the official Debian package repository, verifies
both package and SF2 SHA-256 hashes, and extracts only the data file and its
license. It does not run Debian package scripts. The installed bank is
148,398,306 bytes (about 142 MiB), uses the MIT license recorded in the upstream
package, and is saved under the ignored `.cache/soundfonts/` directory. It is not
committed to GitHub. Allow temporary space for both the compressed archive and
the extracted bank.

An existing copy of the exact package can be reused offline:

`python scripts/setup_bgm.py --install-soundfont --package /path/to/fluid-soundfont-gm_3.1-5.3_all.deb`

Alternatively set `SOUNDFONT` to an existing, appropriately licensed SF2 file.
SFZ is a different format and cannot be used by FluidSynth. Changing sample banks
changes the sound: retain the bank hash and licensing information with the score.
The pinned bank is the one used in the approved “初光 / The First Light” trial.

New computer: clone the repository, check prerequisites, install the local
renderer and sample bank once, then use the same project workflow. The UI does
not start dependency downloads automatically. Codex can perform the documented
setup after the user authorizes installation.

Software licenses and sample-bank rights are separate. Preserve the bank's
license notice. Installing the engine does not grant rights to arbitrary imported
recordings or compositions.

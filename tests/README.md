Browser tests for Chords. They run the app in an iPhone-sized headless Chromium with a fake Supabase and a fake Apple search, so they never touch real data.

    pip install playwright && python3 tests/flows.py && python3 tests/flows2.py && python3 tests/swipe.py

Each script prints ok/FAIL lines and a PROBLEMS list at the end; screenshots land in tests/shots/. They use Chromium, so iOS-only behavior (safe areas, launch screen, edge gestures) still needs a check on the phone.

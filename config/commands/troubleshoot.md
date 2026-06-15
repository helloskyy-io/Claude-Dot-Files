Apply systematic troubleshooting methodology to the problem below.

Approach this as a diagnostic exercise, not a fixing exercise:

1. **Observe** — establish ground truth: exact symptom, what changed recently, what's known to work. Don't theorize before observing.
2. **Map the possibility space** — list candidate causes explicitly. Write them down, don't hold them in your head.
3. **Articulate the hypothesis explicitly BEFORE each test.** If you can't state it in a sentence, you're guessing — return to step 2.
4. **Design a bisecting test** — the test must eliminate roughly HALF the remaining candidates regardless of outcome. A test that only proves one theory (and tells you nothing if it fails) is a guess, not bisection.
5. **Run the test and measure.** Capture both positive AND negative results — "X didn't reproduce" is data worth recording so theories aren't re-tested later.
6. **Decide:**
   - Cause clear? Apply the fix and verify the ORIGINAL symptom is gone (not just "the code runs").
   - Space narrow but answer unclear? **Web search prior art** — someone has hit this before; don't reinvent debugging.
   - Space still wide? Refine the hypothesis and loop.
7. **Iteration cap:** after 3 cycles where the test did NOT eliminate at least half the remaining candidates, escalate. Hand back structured state — symptom / known facts / ruled out / current hypothesis / what would distinguish next / where blocked.

The failure mode to avoid: hypothesis lock-in — trying cosmetic variations of the same theory instead of questioning the theory itself. If you've tried the same approach with different parameters, you're not iterating, you're spinning.

Apply this thinking to: $ARGUMENTS

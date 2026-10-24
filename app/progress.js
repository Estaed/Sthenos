/* Progression (app/progress.js, Task-04): Blueprint -> Rules -> Finish week, installed as Cali.progress through
   Cali.provide('progress', fn). Cali.progress(weekExercise, history) answers next week's { load, target, reason } for
   one exercise of week n:
     weekExercise  Cali.weekExercise(n, dayId, exId): the week's copied rules (kind, repMin, repMax, loadStep), its load,
                   target and sets. Optional dayDone: false says the day was not done that week (Finish week passes it;
                   without it the day counts as done, so the day's summary can show what moves up before Done).
     history       Cali.history(dayId, exId, n): the weeks before n, newest first, [{ week, load, target, sets, dayDone }].
   reason is 'target up', 'load up' or 'deload' when something moves, else 'no change' (the stub's word, which the
   summary reads). The rules, in the order they are tried:
     check row                      copies
     day not done                   copies; that week never counts toward the stall
     no set logged (the day done)   copies, and is skipped like a day not done: the exercise was left out (a busy
                                    machine), which is not a set that fell short
     time row, every set >= target  target + 5 s                                              'target up'
     time row, a short set          copies (a time row has no deload)
     reps, every set >= target and past repMax (target + 1 would pass repMax, or every set reached repMax, as Standing
                                    Calf Raise 15, 15 at target 12 on screen 6)
                                    load + loadStep, target back to repMin                    'load up'
     reps, every set >= target      target + 1                                                'target up'
     reps, short at this load in this week and the two done weeks before it (weeks whose day was not done, or with no
                                    set of it logged, are skipped: they neither count nor break the run), added load
                                    above 0: load x 0.9 rounded to the nearest loadStep (Blueprint, as written),
                                    never below 0; target kept                                  'deload'
                                    when that rounds back to the same load (BW +2.5 to +12.5 at step 2.5, 5 kg at
                                    step 1), nothing moves: copies
     reps, a short set              copies
   A short set is a set below the target, or not logged while another set of the exercise is. Bodyweight lifts carry
   their added load in load (0 = BW only), so every rule applies to it unchanged. A reps row without a loadStep uses
   the default load step setting. */
(() => {
  'use strict';
  const TIME_STEP = 5;
  const STALL_WEEKS = 3;
  const DELOAD = 0.9;
  const isNum = v => typeof v === 'number' && Number.isFinite(v);
  const tidy = v => Math.round(v * 1000) / 1000;                 // 47.5 + 2.5 stays 50, 0.1 steps stay readable
  const short = (sets, target) => sets.some(s => s === null || s.r < target);
  const none = sets => sets.every(s => s === null);

  function stalled(ex, history) {
    let run = 1;                                                    // this week is short
    for (const h of history) {
      if (!h.dayDone || none(h.sets)) continue;
      if (Math.abs(h.load - ex.load) > 1e-9 || !short(h.sets, h.target)) return false;
      if (++run >= STALL_WEEKS) return true;
    }
    return false;
  }

  function deload(load, step) {
    return tidy(Math.max(0, Math.round(load * DELOAD / step) * step));
  }

  function progress(ex, history) {
    const same = { load: ex.load, target: ex.target, reason: 'no change' };
    const sets = Array.isArray(ex.sets) ? ex.sets : [];
    if (ex.kind === 'check' || ex.dayDone === false || none(sets)) return same;
    const isShort = short(sets, ex.target);
    if (ex.kind === 'time') return isShort ? same : { load: ex.load, target: ex.target + TIME_STEP, reason: 'target up' };
    const step = ex.loadStep > 0 ? ex.loadStep : Cali.settings.get('loadStep');
    if (!isShort) {
      const top = isNum(ex.repMax) && (ex.target + 1 > ex.repMax || sets.every(s => s.r >= ex.repMax));
      if (top) return { load: tidy(ex.load + step), target: isNum(ex.repMin) ? ex.repMin : ex.target, reason: 'load up' };
      return { load: ex.load, target: ex.target + 1, reason: 'target up' };
    }
    if (ex.load > 0 && stalled(ex, history)) {
      const load = deload(ex.load, step);
      if (Math.abs(load - ex.load) > 1e-9) return { load, target: ex.target, reason: 'deload' };
    }
    return same;
  }

  Cali.provide('progress', progress);
})();

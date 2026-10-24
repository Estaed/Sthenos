/* Progression (Blueprint -> Rules -> Finish week), the stub Task-04 replaces: every exercise stays as it is.
   Cali.progress(weekExercise, history) answers next week's { load, target, reason } for one exercise;
   the arguments are described in app/core.js (Cali.progress, Cali.weekExercise, Cali.history). */
(() => {
  'use strict';
  Cali.provide('progress', ex => ({ load: ex.load, target: ex.target, reason: 'no change' }));
})();

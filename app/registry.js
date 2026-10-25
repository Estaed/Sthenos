/* Calisthenics feature registry, append-only. Add a feature by appending one line per file at the end:
     CALI_FEATURES.push('app/<feature>.js');
     CALI_FEATURES.push('app/<feature>.css');
   Nothing else goes in this file: index.html loads it before app/core.js, which loads the listed files in this
   order (stylesheets as <link>, scripts in order), and sw.js runs it too (importScripts) to keep every listed
   file available offline. */
self.CALI_FEATURES = [];
CALI_FEATURES.push('app/workout.js');
CALI_FEATURES.push('app/progress.js');
CALI_FEATURES.push('app/workout.css');
CALI_FEATURES.push('app/summary.js');
CALI_FEATURES.push('app/summary.css');
CALI_FEATURES.push('app/alert.js');
CALI_FEATURES.push('app/timer.js');
CALI_FEATURES.push('app/timer.css');
CALI_FEATURES.push('app/sync.js');
CALI_FEATURES.push('app/settings.js');
CALI_FEATURES.push('app/settings.css');
CALI_FEATURES.push('app/week.js');
CALI_FEATURES.push('app/week.css');
CALI_FEATURES.push('app/program.js');
CALI_FEATURES.push('app/program.css');
CALI_FEATURES.push('app/muscles-data.js');
CALI_FEATURES.push('app/muscles.js');
CALI_FEATURES.push('app/muscles.css');

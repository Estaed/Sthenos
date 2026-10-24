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

/* Tarik's A/B/C program, the built-in default (schema v5 program): six lifts a day, most at 3 sets, and the
   hamstring stretch and incline walk as timed tiles (Antrenman.md -> v3, 2026-10-25). Exercise ids are kept
   from v2 so history lines up. Week 1 is built from it on first open; a phone that already has weeks keeps its own. */
self.CALI_DEFAULT_PROGRAM = {
  "id": "abc",
  "name": "A/B/C",
  "days": [
    {
      "id": "mh4v24uyz2_gra7",
      "name": "A Heavy",
      "exercises": [
        {
          "id": "mh4v2qgzri_5zmn",
          "name": "Weighted Pull-up",
          "kind": "reps",
          "sets": 3,
          "target": 6,
          "repMin": 4,
          "repMax": 6,
          "load": 0,
          "loadStep": 2.5,
          "bodyweight": true,
          "pair": "p1"
        },
        {
          "id": "mh4v2k2kof_j8e0",
          "name": "Weighted Dip",
          "kind": "reps",
          "sets": 3,
          "target": 8,
          "repMin": 6,
          "repMax": 10,
          "load": 0,
          "loadStep": 2.5,
          "bodyweight": true,
          "pair": "p1"
        },
        {
          "id": "mh4v2d0gzq_s2x8",
          "name": "Leg Press",
          "kind": "reps",
          "sets": 3,
          "target": 10,
          "repMin": 8,
          "repMax": 12,
          "load": 110,
          "loadStep": 5,
          "pair": "p2"
        },
        {
          "id": "mh4v2s67to_35ii",
          "name": "Side Lateral Raise",
          "kind": "reps",
          "sets": 3,
          "target": 12,
          "repMin": 12,
          "repMax": 20,
          "load": 5,
          "loadStep": 1,
          "pair": "p2"
        },
        {
          "id": "mh4v216xul_13g8",
          "name": "Seated Leg Curl",
          "kind": "reps",
          "sets": 3,
          "target": 12,
          "repMin": 10,
          "repMax": 15,
          "load": 35,
          "loadStep": 2.5,
          "pair": "p3"
        },
        {
          "id": "mh4v2mw6ul_edjz",
          "name": "Standing Calf Raise",
          "kind": "reps",
          "sets": 3,
          "target": 12,
          "repMin": 12,
          "repMax": 15,
          "load": 77.5,
          "loadStep": 2.5,
          "pair": "p3"
        },
        {
          "id": "mh4v2w1p9r_c6tp",
          "name": "Plank",
          "kind": "time",
          "sets": 2,
          "target": 40,
          "repMin": null,
          "repMax": null,
          "load": 0,
          "loadStep": 2.5,
          "bodyweight": true
        },
        {
          "id": "mh4v2crf3j_300t",
          "name": "Hamstring Stretch",
          "kind": "check",
          "sets": 1,
          "target": 1,
          "repMin": null,
          "repMax": null,
          "load": 0,
          "loadStep": 0,
          "note": "Nerve glide 10/leg, then towel hamstring 1 min/leg; stop before the back of the knee burns, foot free",
          "duration": 240
        },
        {
          "id": "mh4v2nzrtm_c05q",
          "name": "Incline Walk",
          "kind": "check",
          "sets": 1,
          "target": 1,
          "repMin": null,
          "repMax": null,
          "load": 0,
          "loadStep": 0,
          "note": "5.0 km/h at 6% incline; +2% a week up to 12%",
          "duration": 1320
        }
      ]
    },
    {
      "id": "mh4v2xm2u0_5y8l",
      "name": "B Volume",
      "exercises": [
        {
          "id": "mh4wrrjxde_juu9",
          "name": "Wrist Warm-up",
          "kind": "check",
          "sets": 1,
          "target": 1,
          "repMin": null,
          "repMax": null,
          "load": 0,
          "loadStep": 0,
          "note": "Circles, then pain-free rocking on all fours",
          "duration": 60
        },
        {
          "id": "mh4v2olheb_vrf8",
          "name": "Pull-up",
          "kind": "reps",
          "sets": 3,
          "target": 8,
          "repMin": 8,
          "repMax": 12,
          "load": 0,
          "loadStep": 2.5,
          "bodyweight": true,
          "pair": "p1"
        },
        {
          "id": "mh9b2sp4ke_r7qd",
          "name": "Shoulder Press",
          "kind": "reps",
          "sets": 3,
          "target": 10,
          "repMin": 8,
          "repMax": 12,
          "load": 47.5,
          "loadStep": 2.5,
          "pair": "p1"
        },
        {
          "id": "mh4v2mv46a_xarm",
          "name": "Leg Extension",
          "kind": "reps",
          "sets": 3,
          "target": 12,
          "repMin": 10,
          "repMax": 15,
          "load": 42.5,
          "loadStep": 2.5,
          "pair": "p2"
        },
        {
          "id": "mh4v2de4vr_8gwr",
          "name": "Seated Leg Curl",
          "kind": "reps",
          "sets": 3,
          "target": 12,
          "repMin": 10,
          "repMax": 15,
          "load": 35,
          "loadStep": 2.5,
          "pair": "p2"
        },
        {
          "id": "mh4v2aihiq_no4t",
          "name": "Incline Curl",
          "kind": "reps",
          "sets": 2,
          "target": 10,
          "repMin": 10,
          "repMax": 15,
          "load": 10,
          "loadStep": 2.5,
          "pair": "p3"
        },
        {
          "id": "mh4v2lqmzi_i5r3",
          "name": "Overhead Triceps",
          "kind": "reps",
          "sets": 2,
          "target": 10,
          "repMin": 10,
          "repMax": 15,
          "load": 15,
          "loadStep": 2.5,
          "pair": "p3",
          "note": "Cable, arms overhead"
        },
        {
          "id": "mh4v2l2yvg_acl9",
          "name": "Hamstring Stretch",
          "kind": "check",
          "sets": 1,
          "target": 1,
          "repMin": null,
          "repMax": null,
          "load": 0,
          "loadStep": 0,
          "note": "Nerve glide 10/leg, then towel hamstring 1 min/leg; stop before the back of the knee burns, foot free",
          "duration": 240
        },
        {
          "id": "mh4v2rd5cu_jbph",
          "name": "Incline Walk",
          "kind": "check",
          "sets": 1,
          "target": 1,
          "repMin": null,
          "repMax": null,
          "load": 0,
          "loadStep": 0,
          "note": "5.0 km/h at 6% incline; +2% a week up to 12%",
          "duration": 1320
        }
      ]
    },
    {
      "id": "mh4v23fat8_wr8d",
      "name": "C Legs",
      "exercises": [
        {
          "id": "mh4v2p22bu_a5ka",
          "name": "Chin-up",
          "kind": "reps",
          "sets": 3,
          "target": 6,
          "repMin": 6,
          "repMax": 10,
          "load": 0,
          "loadStep": 2.5,
          "bodyweight": true,
          "pair": "p1"
        },
        {
          "id": "mh4v2hixx5_3xme",
          "name": "Incline Bench Press",
          "kind": "reps",
          "sets": 3,
          "target": 8,
          "repMin": 6,
          "repMax": 10,
          "load": 45,
          "loadStep": 2.5,
          "pair": "p1"
        },
        {
          "id": "mh4v2a3h2r_jbo4",
          "name": "Leg Press",
          "kind": "reps",
          "sets": 3,
          "target": 12,
          "repMin": 12,
          "repMax": 15,
          "load": 95,
          "loadStep": 5,
          "pair": "p2",
          "note": "Feet high on the platform"
        },
        {
          "id": "mh4v2zwy0v_vby3",
          "name": "Glute Kickback",
          "kind": "reps",
          "sets": 3,
          "target": 12,
          "repMin": 12,
          "repMax": 15,
          "load": 17.5,
          "loadStep": 2.5,
          "pair": "p2",
          "note": "Machine or cable"
        },
        {
          "id": "mh4v2wlxhs_061g",
          "name": "Side Lateral Raise",
          "kind": "reps",
          "sets": 2,
          "target": 12,
          "repMin": 12,
          "repMax": 20,
          "load": 5,
          "loadStep": 1,
          "pair": "p3"
        },
        {
          "id": "mh4v27yr8y_82dh",
          "name": "Reverse Pec Deck",
          "kind": "reps",
          "sets": 2,
          "target": 12,
          "repMin": 12,
          "repMax": 15,
          "load": 37.5,
          "loadStep": 2.5,
          "pair": "p3"
        },
        {
          "id": "mh4v26e2mb_f54j",
          "name": "Hamstring Stretch",
          "kind": "check",
          "sets": 1,
          "target": 1,
          "repMin": null,
          "repMax": null,
          "load": 0,
          "loadStep": 0,
          "note": "Nerve glide 10/leg, then towel hamstring 1 min/leg; stop before the back of the knee burns, foot free",
          "duration": 240
        },
        {
          "id": "mh4v2aqrsm_08jg",
          "name": "Incline Walk",
          "kind": "check",
          "sets": 1,
          "target": 1,
          "repMin": null,
          "repMax": null,
          "load": 0,
          "loadStep": 0,
          "note": "5.0 km/h at 6% incline; +2% a week up to 12%",
          "duration": 1320
        }
      ]
    }
  ]
};

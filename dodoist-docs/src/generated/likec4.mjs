'use client'
/* prettier-ignore-start */
/* eslint-disable */

/******************************************************************************
 * This file was generated
 * DO NOT EDIT MANUALLY!
 ******************************************************************************/


import { jsx } from "react/jsx-runtime";
import { useRef, useCallback, useSyncExternalStore, useState, useEffect } from "react";
import { LikeC4Model } from "@likec4/core/model";
import { LikeC4ModelProvider as LikeC4ModelProvider$1, LikeC4View as LikeC4View$1, ReactLikeC4 as ReactLikeC4$1 } from "likec4/react";
const Icons = {};
function IconRenderer({ node, ...props }) {
  const IconComponent = Icons[node.icon ?? ""];
  if (!IconComponent) {
    return null;
  }
  return jsx(IconComponent, props);
}
let r = /* @__PURE__ */ Symbol(`clean`), i = [], a = 0, o = 0;
const s = (e2) => {
  let t2 = [], n = { get() {
    return n.lc || n.listen(() => {
    })(), n.value;
  }, lc: 0, listen(e3) {
    return n.lc = t2.push(e3), () => {
      for (let t3 = a + 4; t3 < i.length; ) i[t3] === e3 ? i.splice(t3, 4) : t3 += 4;
      let r2 = t2.indexOf(e3);
      ~r2 && (t2.splice(r2, 1), --n.lc || n.off());
    };
  }, notify(e3, r2) {
    o++;
    let s2 = !i.length;
    for (let a2 of t2) i.push(a2, n.value, e3, r2);
    if (s2) {
      for (a = 0; a < i.length; a += 4) i[a](i[a + 1], i[a + 2], i[a + 3]);
      i.length = 0;
    }
  }, off() {
  }, set(e3) {
    let t3 = n.value;
    t3 !== e3 && (n.value = e3, n.notify(t3));
  }, subscribe(e3) {
    let t3 = n.listen(e3);
    return e3(n.value), t3;
  }, value: e2 };
  return process.env.NODE_ENV !== `production` && (n[r] = () => {
    t2 = [], n.lc = 0, n.off();
  }), n;
};
let c = (e2, t2, n, r2) => (e2.events = e2.events || {}, e2.events[n + 10] || (e2.events[n + 10] = r2((t3) => {
  e2.events[n].reduceRight((e3, t4) => (t4(e3), e3), { shared: {}, ...t3 });
})), e2.events[n] = e2.events[n] || [], e2.events[n].push(t2), () => {
  let r3 = e2.events[n], i2 = r3.indexOf(t2);
  r3.splice(i2, 1), r3.length || (delete e2.events[n], e2.events[n + 10](), delete e2.events[n + 10]);
}), l = (e2, t2) => {
  let n = (n2) => {
    let r2 = t2(n2);
    r2 && e2.events[6].push(r2);
  };
  return c(e2, n, 5, (t3) => {
    let n2 = e2.listen;
    e2.listen = (...r2) => (!e2.lc && !e2.active && (e2.active = true, t3()), n2(...r2));
    let i2 = e2.off;
    if (e2.events[6] = [], e2.off = () => {
      i2(), setTimeout(() => {
        if (e2.active && !e2.lc) {
          e2.active = false;
          for (let t4 of e2.events[6]) t4();
          e2.events[6] = [];
        }
      }, 1e3);
    }, process.env.NODE_ENV !== `production`) {
      let t4 = e2[r];
      e2[r] = () => {
        for (let t5 of e2.events[6]) t5();
        e2.events[6] = [], e2.active = false, t4();
      };
    }
    return () => {
      e2.listen = n2, e2.off = i2;
    };
  });
}, u = (e2, t2, n) => {
  Array.isArray(e2) || (e2 = [e2]);
  let r2, i2, a2 = () => {
    if (i2 === o) return;
    i2 = o;
    let n2 = e2.map((e3) => e3.get());
    if (!r2 || n2.some((e3, t3) => e3 !== r2[t3])) {
      r2 = n2;
      let e3 = t2(...n2);
      e3 && e3.then && e3.t ? e3.then((e4) => {
        r2 === n2 && c2.set(e4);
      }) : (c2.set(e3), i2 = o);
    }
  }, c2 = s(void 0), u2 = c2.get;
  c2.get = () => (a2(), u2());
  let f2 = a2;
  return l(c2, () => {
    let t3 = e2.map((e3) => e3.listen(f2));
    return a2(), () => {
      for (let e3 of t3) e3();
    };
  }), c2;
};
const d = (e2, t2) => u(e2, t2);
function p(e2, t2, n) {
  let r2 = new Set(t2).add(void 0);
  return e2.listen((e3, t3, i2) => {
    r2.has(i2) && n(e3, t3, i2);
  });
}
let h = (e2, t2) => (n) => {
  e2.current !== n && (e2.current = n, t2());
};
function g(r2, { keys: i2, deps: a2 = [r2, i2] } = {}) {
  let o2 = useRef();
  o2.current = r2.get();
  let s2 = useCallback((e2) => (h(o2, e2)(r2.value), i2?.length > 0 ? p(r2, i2, h(o2, e2)) : r2.listen(h(o2, e2))), a2), c2 = () => o2.current;
  return useSyncExternalStore(s2, c2, c2);
}
Math.random.bind(Math);
function e(e2, t2, n) {
  let r2 = (n2) => e2(n2, ...t2);
  return n === void 0 ? r2 : Object.assign(r2, { lazy: n, lazyArgs: t2 });
}
function t(t2, n, r2) {
  let i2 = t2.length - n.length;
  if (i2 === 0) return t2(...n);
  if (i2 === 1) return e(t2, n, r2);
  throw Error(`Wrong number of arguments`);
}
function ae(...e2) {
  return t(Z, e2);
}
function Z(e2, t2) {
  if (e2 === t2 || Object.is(e2, t2)) return true;
  if (typeof e2 != `object` || typeof t2 != `object` || e2 === null || t2 === null || Object.getPrototypeOf(e2) !== Object.getPrototypeOf(t2)) return false;
  if (Array.isArray(e2)) return oe(e2, t2);
  if (e2 instanceof Map) return se(e2, t2);
  if (e2 instanceof Set) return ce(e2, t2);
  if (e2 instanceof Date) return e2.getTime() === t2.getTime();
  if (e2 instanceof RegExp) return e2.toString() === t2.toString();
  if (Object.keys(e2).length !== Object.keys(t2).length) return false;
  for (let [n, r2] of Object.entries(e2)) if (!(n in t2) || !Z(r2, t2[n])) return false;
  return true;
}
function oe(e2, t2) {
  if (e2.length !== t2.length) return false;
  for (let [n, r2] of e2.entries()) if (!Z(r2, t2[n])) return false;
  return true;
}
function se(e2, t2) {
  if (e2.size !== t2.size) return false;
  for (let [n, r2] of e2.entries()) if (!t2.has(n) || !Z(r2, t2.get(n))) return false;
  return true;
}
function ce(e2, t2) {
  if (e2.size !== t2.size) return false;
  let n = [...t2];
  for (let t3 of e2) {
    let e3 = false;
    for (let [r2, i2] of n.entries()) if (Z(t3, i2)) {
      e3 = true, n.splice(r2, 1);
      break;
    }
    if (!e3) return false;
  }
  return true;
}
function Me(...e2) {
  return t(Ne, e2);
}
function Ne(e2, t2) {
  let n = {};
  for (let [r2, i2] of Object.entries(e2)) n[r2] = t2(i2, r2, e2);
  return n;
}
/* @__PURE__ */ new Set([`-`, `_`, ...`	.
.\v.\f.\r. .. . . . . . . . . . . . . .\u2028.\u2029. . .　.\uFEFF`.split(`.`)]);
const f = (e2) => {
  let n = d(e2, (e3) => LikeC4Model.create(e3));
  function r2(t2) {
    let n2 = e2.get();
    if (ae(n2, t2)) return;
    let r3 = { ...t2, views: Me(t2.views, (e3) => {
      let t3 = n2.views[e3.id];
      return ae(t3, e3) ? t3 : e3;
    }) };
    e2.set(r3);
  }
  let a2 = d(e2, (e3) => Object.values(e3.views));
  function d$1() {
    return g(n);
  }
  function f2() {
    return g(a2);
  }
  function p2(t2) {
    let [n2, r3] = useState(e2.value?.views[t2] ?? null);
    return useEffect(() => e2.subscribe((e3) => {
      r3(e3.views[t2] ?? null);
    }), [t2]), n2;
  }
  return { updateModel: r2, $likec4model: n, useLikeC4Model: d$1, useLikeC4Views: f2, useLikeC4View: p2 };
};
const $likec4data = s({ _stage: "layouted", projectId: "default", project: { id: "default", title: "default" }, specification: { tags: { restApi: { color: "tomato" } }, elements: { actor: { style: { shape: "person", color: "green" } }, system: { style: {} }, container: { style: {} }, database: { style: {} } }, relationships: {}, deployments: {}, customColors: {} }, elements: { endUser: { style: { shape: "person", color: "green" }, description: { txt: "Manages personal and work tasks." }, title: "End User", kind: "actor", id: "endUser" }, systemAdmin: { style: { shape: "person", color: "green" }, description: { txt: "Manages users, workspaces, and global configuration." }, title: "System Administrator", kind: "actor", id: "systemAdmin" }, taskTracker: { style: {}, description: { txt: "Hybrid personal/work task tracker with project management, agile boards, sprints, and analytics." }, title: "Task Tracker", kind: "system", id: "taskTracker" }, "taskTracker.angularSpa": { style: {}, technology: "Angular, TypeScript", description: { txt: "Browser client. Implements all UI and communicates with the backend via REST API." }, title: "Angular SPA", kind: "container", id: "taskTracker.angularSpa" }, "taskTracker.djangoApi": { style: {}, technology: "Django, Django REST Framework", description: { txt: "Stateless API server. Handles business logic, permissions, and JWT authentication." }, title: "Django REST API", kind: "container", id: "taskTracker.djangoApi" }, "taskTracker.postgresDb": { style: {}, technology: "PostgreSQL 16", description: { txt: "Primary relational data store." }, title: "PostgreSQL", kind: "container", id: "taskTracker.postgresDb" } }, relations: { pbt2q: { title: "Uses via browser", source: { model: "endUser" }, target: { model: "taskTracker.angularSpa" }, id: "pbt2q" }, "15hmdcx": { title: "Administers via browser", source: { model: "systemAdmin" }, target: { model: "taskTracker.angularSpa" }, id: "15hmdcx" }, fmdgf4: { title: "HTTPS REST API (Bearer JWT)", tags: ["restApi"], source: { model: "taskTracker.angularSpa" }, target: { model: "taskTracker.djangoApi" }, id: "fmdgf4" }, "8wnr2": { title: "Reads / writes data", source: { model: "taskTracker.djangoApi" }, target: { model: "taskTracker.postgresDb" }, id: "8wnr2" } }, globals: { predicates: {}, dynamicPredicates: {}, styles: {} }, views: { index: { _stage: "layouted", _type: "element", id: "index", title: "Landscape view", description: null, autoLayout: { direction: "TB" }, hash: "SuHmVo9E944iJQYgzse2F2Oeg5MyurzdXVKFXCpTIJE", bounds: { x: 0, y: 0, width: 750, height: 503 }, nodes: [{ id: "endUser", parent: null, level: 0, children: [], inEdges: [], outEdges: ["d2du9t"], title: "End User", modelRef: "endUser", shape: "person", color: "green", style: { opacity: 15, size: "md" }, description: { txt: "Manages personal and work tasks." }, tags: [], kind: "actor", navigateTo: "__endUser", x: 0, y: 0, width: 320, height: 180, labelBBox: { x: 42, y: 63, width: 236, height: 48 } }, { id: "systemAdmin", parent: null, level: 0, children: [], inEdges: [], outEdges: ["1w8mvqt"], title: "System Administrator", modelRef: "systemAdmin", shape: "person", color: "green", style: { opacity: 15, size: "md" }, description: { txt: "Manages users, workspaces, and global configuration." }, tags: [], kind: "actor", navigateTo: "__systemAdmin", x: 430, y: 0, width: 320, height: 180, labelBBox: { x: 24, y: 54, width: 272, height: 66 } }, { id: "taskTracker", parent: null, level: 0, children: [], inEdges: ["d2du9t", "1w8mvqt"], outEdges: [], title: "Task Tracker", modelRef: "taskTracker", shape: "rectangle", color: "primary", style: { opacity: 15, size: "md" }, description: { txt: "Hybrid personal/work task tracker with project management, agile boards, sprints, and analytics." }, tags: [], kind: "system", navigateTo: "systemContext", x: 213, y: 323, width: 323, height: 180, labelBBox: { x: 18, y: 45, width: 287, height: 83 } }], edges: [{ id: "d2du9t", source: "endUser", target: "taskTracker", label: "Uses via browser", points: [[220, 180], [248, 222], [281, 271], [310, 314]], labelBBox: { x: 275, y: 240, width: 111, height: 18 }, parent: null, relations: ["pbt2q"], color: "gray", line: "dashed", head: "normal" }, { id: "1w8mvqt", source: "systemAdmin", target: "taskTracker", label: "Administers via browser", points: [[530, 180], [502, 222], [469, 271], [440, 314]], labelBBox: { x: 490, y: 240, width: 153, height: 18 }, parent: null, relations: ["15hmdcx"], color: "gray", line: "dashed", head: "normal" }] }, systemContext: { _type: "element", tags: null, links: null, viewOf: "taskTracker", _stage: "layouted", sourcePath: "docs/architecture/tasktracker-architecture.c4", description: null, title: "C1 — Task Tracker: System Context", id: "systemContext", autoLayout: { direction: "TB" }, hash: "eL5GpP-Xphn_qDvEm35qarmzbuV6VZ5f3Gc7kyHT4ok", bounds: { x: 0, y: 0, width: 750, height: 503 }, nodes: [{ id: "endUser", parent: null, level: 0, children: [], inEdges: [], outEdges: ["d2du9t"], title: "End User", modelRef: "endUser", shape: "person", color: "green", style: { opacity: 15, size: "md" }, description: { txt: "Manages personal and work tasks." }, tags: [], kind: "actor", navigateTo: "__endUser", x: 0, y: 0, width: 320, height: 180, labelBBox: { x: 42, y: 63, width: 236, height: 48 } }, { id: "systemAdmin", parent: null, level: 0, children: [], inEdges: [], outEdges: ["1w8mvqt"], title: "System Administrator", modelRef: "systemAdmin", shape: "person", color: "green", style: { opacity: 15, size: "md" }, description: { txt: "Manages users, workspaces, and global configuration." }, tags: [], kind: "actor", navigateTo: "__systemAdmin", x: 430, y: 0, width: 320, height: 180, labelBBox: { x: 24, y: 54, width: 272, height: 66 } }, { id: "taskTracker", parent: null, level: 0, children: [], inEdges: ["d2du9t", "1w8mvqt"], outEdges: [], title: "Task Tracker", modelRef: "taskTracker", shape: "rectangle", color: "blue", style: { opacity: 15, size: "md" }, description: { txt: "Hybrid personal/work task tracker with project management, agile boards, sprints, and analytics." }, tags: [], kind: "system", navigateTo: "containers", x: 213, y: 323, width: 323, height: 180, labelBBox: { x: 18, y: 45, width: 287, height: 83 } }], edges: [{ id: "d2du9t", source: "endUser", target: "taskTracker", label: "Uses via browser", points: [[220, 180], [248, 222], [281, 271], [310, 314]], labelBBox: { x: 275, y: 240, width: 111, height: 18 }, parent: null, relations: ["pbt2q"], color: "gray", line: "dashed", head: "normal" }, { id: "1w8mvqt", source: "systemAdmin", target: "taskTracker", label: "Administers via browser", points: [[530, 180], [502, 222], [469, 271], [440, 314]], labelBBox: { x: 490, y: 240, width: 153, height: 18 }, parent: null, relations: ["15hmdcx"], color: "gray", line: "dashed", head: "normal" }] }, containers: { _type: "element", tags: null, links: null, viewOf: "taskTracker", _stage: "layouted", sourcePath: "docs/architecture/tasktracker-architecture.c4", description: null, title: "C2 — Task Tracker: Containers", id: "containers", autoLayout: { direction: "TB" }, hash: "QAzZlFC7V973grhTwEXE0MhF65W-PHJTltpGPsC0s1M", bounds: { x: 0, y: 0, width: 750, height: 1148 }, nodes: [{ id: "endUser", parent: null, level: 0, children: [], inEdges: [], outEdges: ["tbgh4f"], title: "End User", modelRef: "endUser", shape: "person", color: "green", style: { opacity: 15, size: "md" }, description: { txt: "Manages personal and work tasks." }, tags: [], kind: "actor", navigateTo: "__endUser", x: 0, y: 0, width: 320, height: 180, labelBBox: { x: 42, y: 63, width: 236, height: 48 } }, { id: "systemAdmin", parent: null, level: 0, children: [], inEdges: [], outEdges: ["10h4o2j"], title: "System Administrator", modelRef: "systemAdmin", shape: "person", color: "green", style: { opacity: 15, size: "md" }, description: { txt: "Manages users, workspaces, and global configuration." }, tags: [], kind: "actor", navigateTo: "__systemAdmin", x: 430, y: 0, width: 320, height: 180, labelBBox: { x: 24, y: 54, width: 272, height: 66 } }, { id: "taskTracker.angularSpa", parent: null, level: 0, children: [], inEdges: ["tbgh4f", "10h4o2j"], outEdges: ["15ecq0r"], title: "Angular SPA", modelRef: "taskTracker.angularSpa", shape: "rectangle", color: "green", style: { opacity: 15, size: "md" }, description: { txt: "Browser client. Implements all UI and communicates with the backend via REST API." }, tags: [], technology: "Angular, TypeScript", kind: "container", navigateTo: "__taskTracker_angularSpa", x: 198, y: 323, width: 353, height: 180, labelBBox: { x: 18, y: 44, width: 317, height: 85 } }, { id: "taskTracker.djangoApi", parent: null, level: 0, children: [], inEdges: ["15ecq0r"], outEdges: ["sd0fd2"], title: "Django REST API", modelRef: "taskTracker.djangoApi", shape: "rectangle", color: "blue", style: { opacity: 15, size: "md" }, description: { txt: "Stateless API server. Handles business logic, permissions, and JWT authentication." }, tags: [], technology: "Django, Django REST Framework", kind: "container", navigateTo: "__taskTracker_djangoApi", x: 204, y: 646, width: 341, height: 180, labelBBox: { x: 18, y: 44, width: 306, height: 85 } }, { id: "taskTracker.postgresDb", parent: null, level: 0, children: [], inEdges: ["sd0fd2"], outEdges: [], title: "PostgreSQL", modelRef: "taskTracker.postgresDb", shape: "storage", color: "indigo", style: { opacity: 15, size: "md" }, description: { txt: "Primary relational data store." }, tags: [], technology: "PostgreSQL 16", kind: "container", navigateTo: "__taskTracker_postgresDb", x: 215, y: 968, width: 320, height: 180, labelBBox: { x: 62, y: 54, width: 196, height: 67 } }], edges: [{ id: "tbgh4f", source: "endUser", target: "taskTracker.angularSpa", label: "Uses via browser", points: [[220, 180], [248, 222], [281, 271], [310, 314]], labelBBox: { x: 275, y: 240, width: 111, height: 18 }, parent: null, relations: ["pbt2q"], color: "gray", line: "dashed", head: "normal" }, { id: "10h4o2j", source: "systemAdmin", target: "taskTracker.angularSpa", label: "Administers via browser", points: [[530, 180], [502, 222], [469, 271], [440, 314]], labelBBox: { x: 490, y: 240, width: 153, height: 18 }, parent: null, relations: ["15hmdcx"], color: "gray", line: "dashed", head: "normal" }, { id: "15ecq0r", source: "taskTracker.angularSpa", target: "taskTracker.djangoApi", label: "HTTPS REST API (Bearer JWT)", points: [[375, 503], [375, 544], [375, 593], [375, 635]], labelBBox: { x: 376, y: 562, width: 205, height: 18 }, parent: null, relations: ["fmdgf4"], color: "gray", line: "dashed", head: "normal", tags: ["restApi"] }, { id: "sd0fd2", source: "taskTracker.djangoApi", target: "taskTracker.postgresDb", label: "Reads / writes data", points: [[375, 826], [375, 866], [375, 915], [375, 957]], labelBBox: { x: 376, y: 885, width: 124, height: 18 }, parent: null, relations: ["8wnr2"], color: "gray", line: "dashed", head: "normal" }] }, __endUser: { _stage: "layouted", _type: "element", id: "__endUser", viewOf: "endUser", title: "Auto / End User", description: null, autoLayout: { direction: "TB" }, hash: "QiwgP_qSE2tbLcKBFXxcfHIhOS2RKScUB89g6lKt6S8", bounds: { x: 0, y: 0, width: 324, height: 503 }, nodes: [{ id: "endUser", parent: null, level: 0, children: [], inEdges: [], outEdges: ["d2du9t"], title: "End User", modelRef: "endUser", shape: "person", color: "green", style: { opacity: 15, size: "md" }, description: { txt: "Manages personal and work tasks." }, tags: [], kind: "actor", x: 2, y: 0, width: 320, height: 180, labelBBox: { x: 42, y: 63, width: 236, height: 48 } }, { id: "taskTracker", parent: null, level: 0, children: [], inEdges: ["d2du9t"], outEdges: [], title: "Task Tracker", modelRef: "taskTracker", shape: "rectangle", color: "primary", style: { opacity: 15, size: "md" }, description: { txt: "Hybrid personal/work task tracker with project management, agile boards, sprints, and analytics." }, tags: [], kind: "system", navigateTo: "systemContext", x: 0, y: 323, width: 323, height: 180, labelBBox: { x: 18, y: 45, width: 287, height: 83 } }], edges: [{ id: "d2du9t", source: "endUser", target: "taskTracker", label: "Uses via browser", points: [[162, 180], [162, 221], [162, 270], [162, 313]], labelBBox: { x: 163, y: 240, width: 111, height: 18 }, parent: null, relations: ["pbt2q"], color: "gray", line: "dashed", head: "normal" }] }, __systemAdmin: { _stage: "layouted", _type: "element", id: "__systemAdmin", viewOf: "systemAdmin", title: "Auto / System Administrator", description: null, autoLayout: { direction: "TB" }, hash: "Q655n73-wsraFfGxCOuO2ulZlchvLu3Pv6gzaCd6CiE", bounds: { x: 0, y: 0, width: 324, height: 503 }, nodes: [{ id: "systemAdmin", parent: null, level: 0, children: [], inEdges: [], outEdges: ["1w8mvqt"], title: "System Administrator", modelRef: "systemAdmin", shape: "person", color: "green", style: { opacity: 15, size: "md" }, description: { txt: "Manages users, workspaces, and global configuration." }, tags: [], kind: "actor", x: 2, y: 0, width: 320, height: 180, labelBBox: { x: 24, y: 54, width: 272, height: 66 } }, { id: "taskTracker", parent: null, level: 0, children: [], inEdges: ["1w8mvqt"], outEdges: [], title: "Task Tracker", modelRef: "taskTracker", shape: "rectangle", color: "primary", style: { opacity: 15, size: "md" }, description: { txt: "Hybrid personal/work task tracker with project management, agile boards, sprints, and analytics." }, tags: [], kind: "system", navigateTo: "systemContext", x: 0, y: 323, width: 323, height: 180, labelBBox: { x: 18, y: 45, width: 287, height: 83 } }], edges: [{ id: "1w8mvqt", source: "systemAdmin", target: "taskTracker", label: "Administers via browser", points: [[162, 180], [162, 221], [162, 270], [162, 313]], labelBBox: { x: 163, y: 240, width: 153, height: 18 }, parent: null, relations: ["15hmdcx"], color: "gray", line: "dashed", head: "normal" }] }, __taskTracker_angularSpa: { _stage: "layouted", _type: "element", id: "__taskTracker_angularSpa", viewOf: "taskTracker.angularSpa", title: "Auto / Angular SPA", description: null, autoLayout: { direction: "TB" }, hash: "fyVwDGhZj6FYM0uioOsh-vHOevUWI1La-OeV4kw_c8Q", bounds: { x: 0, y: 0, width: 750, height: 826 }, nodes: [{ id: "endUser", parent: null, level: 0, children: [], inEdges: [], outEdges: ["tbgh4f"], title: "End User", modelRef: "endUser", shape: "person", color: "green", style: { opacity: 15, size: "md" }, description: { txt: "Manages personal and work tasks." }, tags: [], kind: "actor", navigateTo: "__endUser", x: 0, y: 0, width: 320, height: 180, labelBBox: { x: 42, y: 63, width: 236, height: 48 } }, { id: "systemAdmin", parent: null, level: 0, children: [], inEdges: [], outEdges: ["10h4o2j"], title: "System Administrator", modelRef: "systemAdmin", shape: "person", color: "green", style: { opacity: 15, size: "md" }, description: { txt: "Manages users, workspaces, and global configuration." }, tags: [], kind: "actor", navigateTo: "__systemAdmin", x: 430, y: 0, width: 320, height: 180, labelBBox: { x: 24, y: 54, width: 272, height: 66 } }, { id: "taskTracker.angularSpa", parent: null, level: 0, children: [], inEdges: ["tbgh4f", "10h4o2j"], outEdges: ["15ecq0r"], title: "Angular SPA", modelRef: "taskTracker.angularSpa", shape: "rectangle", color: "primary", style: { opacity: 15, size: "md" }, description: { txt: "Browser client. Implements all UI and communicates with the backend via REST API." }, tags: [], technology: "Angular, TypeScript", kind: "container", x: 198, y: 323, width: 353, height: 180, labelBBox: { x: 18, y: 44, width: 317, height: 85 } }, { id: "taskTracker.djangoApi", parent: null, level: 0, children: [], inEdges: ["15ecq0r"], outEdges: [], title: "Django REST API", modelRef: "taskTracker.djangoApi", shape: "rectangle", color: "primary", style: { opacity: 15, size: "md" }, description: { txt: "Stateless API server. Handles business logic, permissions, and JWT authentication." }, tags: [], technology: "Django, Django REST Framework", kind: "container", navigateTo: "__taskTracker_djangoApi", x: 204, y: 646, width: 341, height: 180, labelBBox: { x: 18, y: 44, width: 306, height: 85 } }], edges: [{ id: "tbgh4f", source: "endUser", target: "taskTracker.angularSpa", label: "Uses via browser", points: [[220, 180], [248, 222], [281, 271], [310, 314]], labelBBox: { x: 275, y: 240, width: 111, height: 18 }, parent: null, relations: ["pbt2q"], color: "gray", line: "dashed", head: "normal" }, { id: "10h4o2j", source: "systemAdmin", target: "taskTracker.angularSpa", label: "Administers via browser", points: [[530, 180], [502, 222], [469, 271], [440, 314]], labelBBox: { x: 490, y: 240, width: 153, height: 18 }, parent: null, relations: ["15hmdcx"], color: "gray", line: "dashed", head: "normal" }, { id: "15ecq0r", source: "taskTracker.angularSpa", target: "taskTracker.djangoApi", label: "HTTPS REST API (Bearer JWT)", points: [[375, 503], [375, 544], [375, 593], [375, 635]], labelBBox: { x: 376, y: 562, width: 205, height: 18 }, parent: null, relations: ["fmdgf4"], color: "gray", line: "dashed", head: "normal", tags: ["restApi"] }] }, __taskTracker_djangoApi: { _stage: "layouted", _type: "element", id: "__taskTracker_djangoApi", viewOf: "taskTracker.djangoApi", title: "Auto / Django REST API", description: null, autoLayout: { direction: "TB" }, hash: "4xJsvdxu7_P_bUnOFyO-PEmclUA1O9nJz0969yqalOU", bounds: { x: 0, y: 0, width: 384, height: 826 }, nodes: [{ id: "taskTracker.angularSpa", parent: null, level: 0, children: [], inEdges: [], outEdges: ["15ecq0r"], title: "Angular SPA", modelRef: "taskTracker.angularSpa", shape: "rectangle", color: "primary", style: { opacity: 15, size: "md" }, description: { txt: "Browser client. Implements all UI and communicates with the backend via REST API." }, tags: [], technology: "Angular, TypeScript", kind: "container", navigateTo: "__taskTracker_angularSpa", x: 0, y: 0, width: 353, height: 180, labelBBox: { x: 18, y: 44, width: 317, height: 85 } }, { id: "taskTracker.djangoApi", parent: null, level: 0, children: [], inEdges: ["15ecq0r"], outEdges: ["sd0fd2"], title: "Django REST API", modelRef: "taskTracker.djangoApi", shape: "rectangle", color: "primary", style: { opacity: 15, size: "md" }, description: { txt: "Stateless API server. Handles business logic, permissions, and JWT authentication." }, tags: [], technology: "Django, Django REST Framework", kind: "container", x: 6, y: 323, width: 341, height: 180, labelBBox: { x: 18, y: 44, width: 306, height: 85 } }, { id: "taskTracker.postgresDb", parent: null, level: 0, children: [], inEdges: ["sd0fd2"], outEdges: [], title: "PostgreSQL", modelRef: "taskTracker.postgresDb", shape: "rectangle", color: "primary", style: { opacity: 15, size: "md" }, description: { txt: "Primary relational data store." }, tags: [], technology: "PostgreSQL 16", kind: "container", navigateTo: "__taskTracker_postgresDb", x: 17, y: 646, width: 320, height: 180, labelBBox: { x: 62, y: 53, width: 196, height: 67 } }], edges: [{ id: "15ecq0r", source: "taskTracker.angularSpa", target: "taskTracker.djangoApi", label: "HTTPS REST API (Bearer JWT)", points: [[177, 180], [177, 221], [177, 270], [177, 313]], labelBBox: { x: 178, y: 240, width: 205, height: 18 }, parent: null, relations: ["fmdgf4"], color: "gray", line: "dashed", head: "normal", tags: ["restApi"] }, { id: "sd0fd2", source: "taskTracker.djangoApi", target: "taskTracker.postgresDb", label: "Reads / writes data", points: [[177, 503], [177, 544], [177, 593], [177, 635]], labelBBox: { x: 178, y: 562, width: 124, height: 18 }, parent: null, relations: ["8wnr2"], color: "gray", line: "dashed", head: "normal" }] }, __taskTracker_postgresDb: { _stage: "layouted", _type: "element", id: "__taskTracker_postgresDb", viewOf: "taskTracker.postgresDb", title: "Auto / PostgreSQL", description: null, autoLayout: { direction: "TB" }, hash: "aURQuNd5TG5au-hO28MdxYKMC1rPMxQObb_zPSQRvJU", bounds: { x: 0, y: 0, width: 342, height: 503 }, nodes: [{ id: "taskTracker.djangoApi", parent: null, level: 0, children: [], inEdges: [], outEdges: ["sd0fd2"], title: "Django REST API", modelRef: "taskTracker.djangoApi", shape: "rectangle", color: "primary", style: { opacity: 15, size: "md" }, description: { txt: "Stateless API server. Handles business logic, permissions, and JWT authentication." }, tags: [], technology: "Django, Django REST Framework", kind: "container", navigateTo: "__taskTracker_djangoApi", x: 0, y: 0, width: 341, height: 180, labelBBox: { x: 18, y: 44, width: 306, height: 85 } }, { id: "taskTracker.postgresDb", parent: null, level: 0, children: [], inEdges: ["sd0fd2"], outEdges: [], title: "PostgreSQL", modelRef: "taskTracker.postgresDb", shape: "rectangle", color: "primary", style: { opacity: 15, size: "md" }, description: { txt: "Primary relational data store." }, tags: [], technology: "PostgreSQL 16", kind: "container", x: 11, y: 323, width: 320, height: 180, labelBBox: { x: 62, y: 53, width: 196, height: 67 } }], edges: [{ id: "sd0fd2", source: "taskTracker.djangoApi", target: "taskTracker.postgresDb", label: "Reads / writes data", points: [[171, 180], [171, 221], [171, 270], [171, 313]], labelBBox: { x: 172, y: 240, width: 124, height: 18 }, parent: null, relations: ["8wnr2"], color: "gray", line: "dashed", head: "normal" }] } }, deployments: { elements: {}, relations: {} }, imports: {}, manualLayouts: {} });
const {
  $likec4model,
  useLikeC4Model,
  useLikeC4View
} = f($likec4data);
function LikeC4ModelProvider({ children }) {
  const likeC4Model = useLikeC4Model();
  return jsx(LikeC4ModelProvider$1, { likec4model: likeC4Model, children });
}
function LikeC4View(props) {
  return jsx(LikeC4ModelProvider, { children: jsx(LikeC4View$1, { renderIcon: IconRenderer, ...props }) });
}
function ReactLikeC4(props) {
  return jsx(LikeC4ModelProvider, { children: jsx(ReactLikeC4$1, { renderIcon: IconRenderer, ...props }) });
}
const likec4model = $likec4model.get();
function isLikeC4ViewId(value) {
  const model = $likec4data.get();
  return value != null && typeof value === "string" && !!model.views[value];
}
export {
  LikeC4ModelProvider,
  LikeC4View,
  ReactLikeC4,
  IconRenderer as RenderIcon,
  isLikeC4ViewId,
  likec4model,
  useLikeC4Model,
  useLikeC4View
};


/* prettier-ignore-end */


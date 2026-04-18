module.exports = [
"[project]/Documents/Coding/oilrig/routewise/routewise/.next-internal/server/app/page/actions.js [app-rsc] (server actions loader, ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([]);
}),
"[project]/Documents/Coding/oilrig/routewise/routewise/src/app/layout.tsx [app-rsc] (ecmascript, Next.js Server Component)", ((__turbopack_context__) => {

__turbopack_context__.n(__turbopack_context__.i("[project]/Documents/Coding/oilrig/routewise/routewise/src/app/layout.tsx [app-rsc] (ecmascript)"));
}),
"[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx [app-rsc] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>Home
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Documents/Coding/oilrig/routewise/routewise/node_modules/next/dist/server/route-modules/app-page/vendored/rsc/react-jsx-dev-runtime.js [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Documents/Coding/oilrig/routewise/routewise/node_modules/next/dist/client/app-dir/link.js [app-rsc] (ecmascript)");
;
;
const DEMO_TRIPS = [
    {
        label: "Miami -> Tampa (the hero demo)",
        description: "I-75 / Alligator Alley. Urban, Everglades rural interstate, Gulf metro.",
        olat: 25.7617,
        olon: -80.1918,
        dlat: 27.9506,
        dlon: -82.4572
    },
    {
        label: "Jacksonville -> Pensacola (fatigue + rural)",
        description: "I-10 across the Panhandle. Long, sparse-services, wildlife.",
        olat: 30.3322,
        olon: -81.6557,
        dlat: 30.4213,
        dlon: -87.2169
    },
    {
        label: "Orlando -> Tampa (verification demo)",
        description: 'I-4. The "deadliest interstate" — show retrieval surfaces what locals know.',
        olat: 28.5383,
        olon: -81.3792,
        dlat: 27.9506,
        dlon: -82.4572
    }
];
function buildHref(t) {
    const params = new URLSearchParams({
        olat: String(t.olat),
        olon: String(t.olon),
        dlat: String(t.dlat),
        dlon: String(t.dlon)
    });
    return `/brief?${params.toString()}`;
}
function Home() {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("main", {
        className: "flex min-h-screen flex-col items-center bg-gradient-to-b from-slate-950 to-slate-900 px-4 py-16 text-slate-100",
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "container flex max-w-3xl flex-col gap-10",
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("header", {
                    className: "flex flex-col gap-3",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                            className: "text-4xl font-extrabold tracking-tight sm:text-5xl",
                            children: "RouteWise"
                        }, void 0, false, {
                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                            lineNumber: 45,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "text-lg text-slate-300",
                            children: "A pre-trip briefing for unfamiliar long drives. Paste a route and we'll pull the real crashes that have happened on roads like yours in conditions like yours."
                        }, void 0, false, {
                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                            lineNumber: 48,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                    lineNumber: 44,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                    className: "flex flex-col gap-4 rounded-xl bg-slate-800/40 p-6",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                            className: "text-xl font-semibold",
                            children: "Plan a trip"
                        }, void 0, false, {
                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                            lineNumber: 56,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
                            action: "/brief",
                            className: "flex flex-col gap-3",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "grid grid-cols-2 gap-3",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                            className: "flex flex-col gap-1 text-sm",
                                            children: [
                                                "Origin lat",
                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                    name: "olat",
                                                    type: "number",
                                                    step: "any",
                                                    required: true,
                                                    defaultValue: 25.7617,
                                                    className: "rounded-md bg-slate-900/70 px-3 py-2 text-base"
                                                }, void 0, false, {
                                                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                                    lineNumber: 61,
                                                    columnNumber: 17
                                                }, this)
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                            lineNumber: 59,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                            className: "flex flex-col gap-1 text-sm",
                                            children: [
                                                "Origin lon",
                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                    name: "olon",
                                                    type: "number",
                                                    step: "any",
                                                    required: true,
                                                    defaultValue: -80.1918,
                                                    className: "rounded-md bg-slate-900/70 px-3 py-2 text-base"
                                                }, void 0, false, {
                                                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                                    lineNumber: 72,
                                                    columnNumber: 17
                                                }, this)
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                            lineNumber: 70,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                            className: "flex flex-col gap-1 text-sm",
                                            children: [
                                                "Destination lat",
                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                    name: "dlat",
                                                    type: "number",
                                                    step: "any",
                                                    required: true,
                                                    defaultValue: 27.9506,
                                                    className: "rounded-md bg-slate-900/70 px-3 py-2 text-base"
                                                }, void 0, false, {
                                                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                                    lineNumber: 83,
                                                    columnNumber: 17
                                                }, this)
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                            lineNumber: 81,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                            className: "flex flex-col gap-1 text-sm",
                                            children: [
                                                "Destination lon",
                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                                    name: "dlon",
                                                    type: "number",
                                                    step: "any",
                                                    required: true,
                                                    defaultValue: -82.4572,
                                                    className: "rounded-md bg-slate-900/70 px-3 py-2 text-base"
                                                }, void 0, false, {
                                                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                                    lineNumber: 94,
                                                    columnNumber: 17
                                                }, this)
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                            lineNumber: 92,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                    lineNumber: 58,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                    className: "flex flex-col gap-1 text-sm",
                                    children: [
                                        "Departure (optional, ISO 8601)",
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                            name: "depart",
                                            type: "datetime-local",
                                            className: "rounded-md bg-slate-900/70 px-3 py-2 text-base"
                                        }, void 0, false, {
                                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                            lineNumber: 106,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                    lineNumber: 104,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                    type: "submit",
                                    className: "mt-2 self-start rounded-md bg-indigo-500 px-5 py-2 font-medium text-white hover:bg-indigo-400",
                                    children: "Brief me"
                                }, void 0, false, {
                                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                    lineNumber: 112,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                            lineNumber: 57,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                    lineNumber: 55,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                    className: "flex flex-col gap-3",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                            className: "text-xl font-semibold",
                            children: "Demo trips"
                        }, void 0, false, {
                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                            lineNumber: 122,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "flex flex-col gap-3",
                            children: DEMO_TRIPS.map((t)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["default"], {
                                    href: buildHref(t),
                                    className: "flex flex-col gap-1 rounded-lg bg-slate-800/40 p-4 hover:bg-slate-800/70",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "text-base font-semibold",
                                            children: t.label
                                        }, void 0, false, {
                                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                            lineNumber: 130,
                                            columnNumber: 17
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                            className: "text-sm text-slate-400",
                                            children: t.description
                                        }, void 0, false, {
                                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                            lineNumber: 131,
                                            columnNumber: 17
                                        }, this)
                                    ]
                                }, t.label, true, {
                                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                                    lineNumber: 125,
                                    columnNumber: 15
                                }, this))
                        }, void 0, false, {
                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                            lineNumber: 123,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                    lineNumber: 121,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("footer", {
                    className: "text-xs text-slate-500",
                    children: [
                        "v0.1 groundwork. Backend at ",
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("code", {
                            children: `${"$"}{BACKEND_URL}`
                        }, void 0, false, {
                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                            lineNumber: 138,
                            columnNumber: 39
                        }, this),
                        " on",
                        " ",
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("code", {
                            children: "POST /trip/brief"
                        }, void 0, false, {
                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                            lineNumber: 139,
                            columnNumber: 11
                        }, this),
                        ". See ",
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("code", {
                            children: "ROUTEWISE.md"
                        }, void 0, false, {
                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                            lineNumber: 139,
                            columnNumber: 46
                        }, this),
                        " for the spec."
                    ]
                }, void 0, true, {
                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
                    lineNumber: 137,
                    columnNumber: 9
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
            lineNumber: 43,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx",
        lineNumber: 42,
        columnNumber: 5
    }, this);
}
}),
"[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx [app-rsc] (ecmascript, Next.js Server Component)", ((__turbopack_context__) => {

__turbopack_context__.n(__turbopack_context__.i("[project]/Documents/Coding/oilrig/routewise/routewise/src/app/page.tsx [app-rsc] (ecmascript)"));
}),
"[externals]/next/dist/shared/lib/no-fallback-error.external.js [external] (next/dist/shared/lib/no-fallback-error.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/shared/lib/no-fallback-error.external.js", () => require("next/dist/shared/lib/no-fallback-error.external.js"));

module.exports = mod;
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__715721b6._.js.map
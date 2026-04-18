module.exports = [
"[project]/Documents/Coding/oilrig/routewise/routewise/.next-internal/server/app/brief/page/actions.js [app-rsc] (server actions loader, ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([]);
}),
"[project]/Documents/Coding/oilrig/routewise/routewise/src/app/layout.tsx [app-rsc] (ecmascript, Next.js Server Component)", ((__turbopack_context__) => {

__turbopack_context__.n(__turbopack_context__.i("[project]/Documents/Coding/oilrig/routewise/routewise/src/app/layout.tsx [app-rsc] (ecmascript)"));
}),
"[project]/Documents/Coding/oilrig/routewise/routewise/src/env.js [app-rsc] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "env",
    ()=>env
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f40$t3$2d$oss$2f$env$2d$nextjs$2f$dist$2f$index$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Documents/Coding/oilrig/routewise/routewise/node_modules/@t3-oss/env-nextjs/dist/index.js [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$zod$2f$v3$2f$external$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__ = __turbopack_context__.i("[project]/Documents/Coding/oilrig/routewise/routewise/node_modules/zod/v3/external.js [app-rsc] (ecmascript) <export * as z>");
;
;
const env = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f40$t3$2d$oss$2f$env$2d$nextjs$2f$dist$2f$index$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["createEnv"])({
    /**
   * Specify your server-side environment variables schema here. This way you can ensure the app
   * isn't built with invalid env vars.
   */ server: {
        DATABASE_URL: __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$zod$2f$v3$2f$external$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].string().url().optional(),
        NODE_ENV: __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$zod$2f$v3$2f$external$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].enum([
            "development",
            "test",
            "production"
        ]).default("development"),
        BACKEND_URL: __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$zod$2f$v3$2f$external$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].string().url().default("http://localhost:8000")
    },
    /**
   * Specify your client-side environment variables schema here. This way you can ensure the app
   * isn't built with invalid env vars. To expose them to the client, prefix them with
   * `NEXT_PUBLIC_`.
   */ client: {
    },
    /**
   * You can't destruct `process.env` as a regular object in the Next.js edge runtimes (e.g.
   * middlewares) or client-side so we need to destruct manually.
   */ runtimeEnv: {
        DATABASE_URL: process.env.DATABASE_URL,
        NODE_ENV: ("TURBOPACK compile-time value", "development"),
        BACKEND_URL: process.env.BACKEND_URL
    },
    /**
   * Run `build` or `dev` with `SKIP_ENV_VALIDATION` to skip env validation. This is especially
   * useful for Docker builds.
   */ skipValidation: !!process.env.SKIP_ENV_VALIDATION,
    /**
   * Makes it so that empty strings are treated as undefined. `SOME_VAR: z.string()` and
   * `SOME_VAR=''` will throw an error.
   */ emptyStringAsUndefined: true
});
}),
"[project]/Documents/Coding/oilrig/routewise/routewise/src/lib/api.ts [app-rsc] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "BackendError",
    ()=>BackendError,
    "fetchHotspotDetail",
    ()=>fetchHotspotDetail,
    "fetchTripBrief",
    ()=>fetchTripBrief
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$server$2d$only$2f$empty$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Documents/Coding/oilrig/routewise/routewise/node_modules/next/dist/compiled/server-only/empty.js [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$src$2f$env$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Documents/Coding/oilrig/routewise/routewise/src/env.js [app-rsc] (ecmascript)");
;
;
class BackendError extends Error {
    status;
    constructor(status, message){
        super(message);
        this.status = status;
        this.name = "BackendError";
    }
}
async function request(path, init) {
    const url = `${__TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$src$2f$env$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["env"].BACKEND_URL}${path}`;
    const res = await fetch(url, {
        ...init,
        headers: {
            "content-type": "application/json",
            ...init.headers ?? {}
        },
        cache: "no-store"
    });
    if (!res.ok) {
        const body = await res.text().catch(()=>"");
        throw new BackendError(res.status, `${res.status} ${url}: ${body.slice(0, 200)}`);
    }
    return await res.json();
}
async function fetchTripBrief(req) {
    return request("/trip/brief", {
        method: "POST",
        body: JSON.stringify(req)
    });
}
async function fetchHotspotDetail(id) {
    return request(`/hotspots/${encodeURIComponent(id)}`, {
        method: "GET"
    });
}
;
}),
"[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx [app-rsc] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>BriefPage
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Documents/Coding/oilrig/routewise/routewise/node_modules/next/dist/server/route-modules/app-page/vendored/rsc/react-jsx-dev-runtime.js [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Documents/Coding/oilrig/routewise/routewise/node_modules/next/dist/client/app-dir/link.js [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Documents/Coding/oilrig/routewise/routewise/src/lib/api.ts [app-rsc] (ecmascript)");
;
;
;
function num(v) {
    if (typeof v !== "string") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
}
function fmtMin(total) {
    const h = Math.floor(total / 60);
    const m = Math.round(total % 60);
    if (h && m) return `${h}h ${m}m`;
    if (h) return `${h}h`;
    return `${m}m`;
}
function fmtKm(km) {
    return `${km.toFixed(0)} km`;
}
function fmtIso(iso) {
    if (!iso) return "-";
    return new Date(iso).toLocaleString();
}
async function BriefPage({ searchParams }) {
    const params = await searchParams;
    const olat = num(params.olat);
    const olon = num(params.olon);
    const dlat = num(params.dlat);
    const dlon = num(params.dlon);
    const depart = typeof params.depart === "string" ? params.depart : undefined;
    if (olat === null || olon === null || dlat === null || dlon === null) {
        return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(Shell, {
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                    className: "text-red-300",
                    children: "Missing or invalid coordinates. Go back and fill them in."
                }, void 0, false, {
                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                    lineNumber: 46,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["default"], {
                    href: "/",
                    className: "text-indigo-300 underline",
                    children: "Back to home"
                }, void 0, false, {
                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                    lineNumber: 49,
                    columnNumber: 9
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
            lineNumber: 45,
            columnNumber: 7
        }, this);
    }
    let brief = null;
    let error = null;
    try {
        brief = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["fetchTripBrief"])({
            origin: {
                lat: olat,
                lon: olon
            },
            destination: {
                lat: dlat,
                lon: dlon
            },
            timestamp: depart ? new Date(depart).toISOString() : null
        });
    } catch (e) {
        if (e instanceof __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["BackendError"]) {
            error = `Backend error (${e.status}): ${e.message}`;
        } else if (e instanceof Error) {
            error = `Could not reach the RouteWise backend: ${e.message}`;
        } else {
            error = "Unknown error contacting the backend.";
        }
    }
    if (error || !brief) {
        return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(Shell, {
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                    className: "text-2xl font-semibold",
                    children: "Trip briefing"
                }, void 0, false, {
                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                    lineNumber: 77,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                    className: "text-red-300",
                    children: error
                }, void 0, false, {
                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                    lineNumber: 78,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                    className: "text-sm text-slate-400",
                    children: [
                        "Is the FastAPI backend running on port 8000? Try",
                        " ",
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("code", {
                            children: "./start.sh"
                        }, void 0, false, {
                            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                            lineNumber: 81,
                            columnNumber: 11
                        }, this),
                        " from the repo root."
                    ]
                }, void 0, true, {
                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                    lineNumber: 79,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["default"], {
                    href: "/",
                    className: "text-indigo-300 underline",
                    children: "Back to home"
                }, void 0, false, {
                    fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                    lineNumber: 83,
                    columnNumber: 9
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
            lineNumber: 76,
            columnNumber: 7
        }, this);
    }
    const { route, conditions_banner, fatigue_plan, hotspots, pre_trip_checklist } = brief;
    const distanceKm = route.distance_m / 1000;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(Shell, {
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("header", {
                className: "flex flex-col gap-1",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                        className: "text-3xl font-extrabold tracking-tight",
                        children: "Trip briefing"
                    }, void 0, false, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 97,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "text-sm text-slate-400",
                        children: [
                            olat.toFixed(4),
                            ",",
                            olon.toFixed(4),
                            " ",
                            "->",
                            " ",
                            dlat.toFixed(4),
                            ",",
                            dlon.toFixed(4)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 100,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                lineNumber: 96,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                className: "grid grid-cols-2 gap-3 rounded-xl bg-slate-800/40 p-5 sm:grid-cols-4",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(Stat, {
                        label: "Distance",
                        value: fmtKm(distanceKm)
                    }, void 0, false, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 106,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(Stat, {
                        label: "Duration",
                        value: fmtMin(route.duration_s / 60)
                    }, void 0, false, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 107,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(Stat, {
                        label: "Departure",
                        value: fmtIso(route.departure_iso)
                    }, void 0, false, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 108,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(Stat, {
                        label: "Arrival",
                        value: fmtIso(route.arrival_iso)
                    }, void 0, false, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 109,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                lineNumber: 105,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                className: "rounded-xl bg-amber-500/10 p-5 ring-1 ring-amber-400/30",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                        className: "mb-2 text-lg font-semibold text-amber-200",
                        children: "Tonight's conditions"
                    }, void 0, false, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 113,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "text-amber-100",
                        children: conditions_banner.summary
                    }, void 0, false, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 116,
                        columnNumber: 9
                    }, this),
                    conditions_banner.dark_drive_minutes > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "mt-2 text-sm text-amber-200/80",
                        children: [
                            "~",
                            fmtMin(conditions_banner.dark_drive_minutes),
                            " after dark. Sunset at ",
                            fmtIso(conditions_banner.sunset_iso),
                            "."
                        ]
                    }, void 0, true, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 118,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                lineNumber: 112,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                className: "rounded-xl bg-slate-800/40 p-5",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                        className: "mb-3 text-lg font-semibold",
                        children: "Hotspots"
                    }, void 0, false, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 126,
                        columnNumber: 9
                    }, this),
                    hotspots.length === 0 ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "text-sm text-slate-400",
                        children: [
                            "No hotspots returned for this route. This is the spec's honesty test (s2.4): with the vector DB empty or down, the briefing card count is zero. Once you ingest data with",
                            " ",
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("code", {
                                children: "scripts/seed_synthetic.py"
                            }, void 0, false, {
                                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                                lineNumber: 132,
                                columnNumber: 13
                            }, this),
                            " (or real FARS / FDOT / CISS), pins will appear here."
                        ]
                    }, void 0, true, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 128,
                        columnNumber: 11
                    }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                        className: "flex flex-col gap-3",
                        children: hotspots.map((h)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                className: "flex flex-col gap-1 rounded-lg bg-slate-900/40 p-4",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "flex items-baseline justify-between gap-2",
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                className: "font-semibold",
                                                children: h.label
                                            }, void 0, false, {
                                                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                                                lineNumber: 143,
                                                columnNumber: 19
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                className: "text-xs text-slate-400",
                                                children: [
                                                    fmtKm(h.km_into_trip),
                                                    " in - ",
                                                    h.n_crashes,
                                                    " crash",
                                                    h.n_crashes === 1 ? "" : "es"
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                                                lineNumber: 144,
                                                columnNumber: 19
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                                        lineNumber: 142,
                                        columnNumber: 17
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                        className: "text-sm text-slate-200",
                                        children: h.coaching_line
                                    }, void 0, false, {
                                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                                        lineNumber: 149,
                                        columnNumber: 17
                                    }, this),
                                    h.intensity_ratio !== null && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                        className: "text-xs text-slate-400",
                                        children: [
                                            h.intensity_ratio.toFixed(1),
                                            "x the FL baseline rate at AADT",
                                            " ",
                                            h.aadt?.toLocaleString() ?? "?"
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                                        lineNumber: 151,
                                        columnNumber: 19
                                    }, this)
                                ]
                            }, h.hotspot_id, true, {
                                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                                lineNumber: 138,
                                columnNumber: 15
                            }, this))
                    }, void 0, false, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 136,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                lineNumber: 125,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                className: "rounded-xl bg-slate-800/40 p-5",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                        className: "mb-3 text-lg font-semibold",
                        children: "Fatigue plan"
                    }, void 0, false, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 163,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "text-sm text-slate-400",
                        children: [
                            "Total drive: ",
                            fmtMin(fatigue_plan.total_drive_minutes)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 164,
                        columnNumber: 9
                    }, this),
                    fatigue_plan.suggested_stops.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                        className: "mt-2 flex flex-col gap-2",
                        children: fatigue_plan.suggested_stops.map((s, i)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                className: "text-sm",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "font-medium",
                                        children: s.label
                                    }, void 0, false, {
                                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                                        lineNumber: 171,
                                        columnNumber: 17
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "text-slate-400",
                                        children: [
                                            " ",
                                            "- ETA ",
                                            fmtIso(s.eta_iso),
                                            " (",
                                            fmtKm(s.km_into_trip),
                                            " in)"
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                                        lineNumber: 172,
                                        columnNumber: 17
                                    }, this)
                                ]
                            }, i, true, {
                                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                                lineNumber: 170,
                                columnNumber: 15
                            }, this))
                    }, void 0, false, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 168,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                lineNumber: 162,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                className: "rounded-xl bg-slate-800/40 p-5",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                        className: "mb-3 text-lg font-semibold",
                        children: "Before you go"
                    }, void 0, false, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 183,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                        className: "list-disc pl-5 text-sm",
                        children: pre_trip_checklist.map((c, i)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                                children: c
                            }, i, false, {
                                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                                lineNumber: 186,
                                columnNumber: 13
                            }, this))
                    }, void 0, false, {
                        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                        lineNumber: 184,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                lineNumber: 182,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["default"], {
                href: "/",
                className: "text-indigo-300 underline",
                children: "Plan another trip"
            }, void 0, false, {
                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                lineNumber: 191,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
        lineNumber: 95,
        columnNumber: 5
    }, this);
}
function Shell({ children }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("main", {
        className: "flex min-h-screen flex-col items-center bg-gradient-to-b from-slate-950 to-slate-900 px-4 py-12 text-slate-100",
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "container flex max-w-3xl flex-col gap-6",
            children: children
        }, void 0, false, {
            fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
            lineNumber: 201,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
        lineNumber: 200,
        columnNumber: 5
    }, this);
}
function Stat({ label, value }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "flex flex-col gap-1",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                className: "text-xs uppercase tracking-wide text-slate-400",
                children: label
            }, void 0, false, {
                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                lineNumber: 209,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Documents$2f$Coding$2f$oilrig$2f$routewise$2f$routewise$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                className: "text-base font-semibold",
                children: value
            }, void 0, false, {
                fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
                lineNumber: 212,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx",
        lineNumber: 208,
        columnNumber: 5
    }, this);
}
}),
"[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx [app-rsc] (ecmascript, Next.js Server Component)", ((__turbopack_context__) => {

__turbopack_context__.n(__turbopack_context__.i("[project]/Documents/Coding/oilrig/routewise/routewise/src/app/brief/page.tsx [app-rsc] (ecmascript)"));
}),
"[externals]/next/dist/shared/lib/no-fallback-error.external.js [external] (next/dist/shared/lib/no-fallback-error.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/shared/lib/no-fallback-error.external.js", () => require("next/dist/shared/lib/no-fallback-error.external.js"));

module.exports = mod;
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__9ba4a678._.js.map
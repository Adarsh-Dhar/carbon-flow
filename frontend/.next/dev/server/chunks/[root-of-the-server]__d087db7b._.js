module.exports = [
"[externals]/next/dist/compiled/next-server/app-route-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-route-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-unit-async-storage.external.js [external] (next/dist/server/app-render/work-unit-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-unit-async-storage.external.js", () => require("next/dist/server/app-render/work-unit-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-async-storage.external.js [external] (next/dist/server/app-render/work-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-async-storage.external.js", () => require("next/dist/server/app-render/work-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/shared/lib/no-fallback-error.external.js [external] (next/dist/shared/lib/no-fallback-error.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/shared/lib/no-fallback-error.external.js", () => require("next/dist/shared/lib/no-fallback-error.external.js"));

module.exports = mod;
}),
"[project]/app/api/respiro/chat/route.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "POST",
    ()=>POST
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f40$ai$2d$sdk$2b$google$40$2$2e$0$2e$44_zod$40$3$2e$25$2e$76$2f$node_modules$2f40$ai$2d$sdk$2f$google$2f$dist$2f$index$2e$mjs__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/.pnpm/@ai-sdk+google@2.0.44_zod@3.25.76/node_modules/@ai-sdk/google/dist/index.mjs [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$ai$40$5$2e$0$2e$104_zod$40$3$2e$25$2e$76$2f$node_modules$2f$ai$2f$dist$2f$index$2e$mjs__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/.pnpm/ai@5.0.104_zod@3.25.76/node_modules/ai/dist/index.mjs [app-route] (ecmascript) <locals>");
;
;
const gemini = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f40$ai$2d$sdk$2b$google$40$2$2e$0$2e$44_zod$40$3$2e$25$2e$76$2f$node_modules$2f40$ai$2d$sdk$2f$google$2f$dist$2f$index$2e$mjs__$5b$app$2d$route$5d$__$28$ecmascript$29$__["createGoogleGenerativeAI"])({
    apiKey: process.env.GEMINI_API_KEY ?? ""
});
async function POST(req) {
    const { messages } = await req.json();
    const modelMessages = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$ai$40$5$2e$0$2e$104_zod$40$3$2e$25$2e$76$2f$node_modules$2f$ai$2f$dist$2f$index$2e$mjs__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__["convertToModelMessages"])(messages ?? []);
    if (!process.env.GEMINI_API_KEY) {
        return new Response(JSON.stringify({
            error: "GEMINI_API_KEY missing. Set it to enable live agent streaming."
        }), {
            status: 400,
            headers: {
                "content-type": "application/json"
            }
        });
    }
    const result = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$ai$40$5$2e$0$2e$104_zod$40$3$2e$25$2e$76$2f$node_modules$2f$ai$2f$dist$2f$index$2e$mjs__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__["streamText"])({
        model: gemini(process.env.GEMINI_MODEL ?? process.env.OPENAI_MODEL ?? "models/gemini-2.5-flash"),
        system: "You are the Respiro Negotiator and Orchestrator agent. You collaborate with Sentry and Clinical agents to move high-risk calendar events, coordinate with families, and explain every action with calm authority.",
        messages: modelMessages,
        maxOutputTokens: 200
    });
    return result.toUIMessageStreamResponse();
}
}),
"[project]/app/api/chat/route.ts [app-route] (ecmascript) <locals>", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([]);
var __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$respiro$2f$chat$2f$route$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/app/api/respiro/chat/route.ts [app-route] (ecmascript)");
;
}),
"[project]/app/api/chat/route.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "POST",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$respiro$2f$chat$2f$route$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["POST"]
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$chat$2f$route$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/app/api/chat/route.ts [app-route] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$app$2f$api$2f$respiro$2f$chat$2f$route$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/app/api/respiro/chat/route.ts [app-route] (ecmascript)");
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__d087db7b._.js.map
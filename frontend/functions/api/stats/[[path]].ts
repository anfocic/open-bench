interface Env {
    ANALYTICS_HOST?: string;
}

const DEFAULT_HOST = "https://analytics.openbenchmark.dev";
const ALLOWED = new Set(["summary", "timeseries", "top", "vitals"]);

export const onRequestGet: PagesFunction<Env, "path"> = async ({request, params, env}) => {
    const segs = Array.isArray(params.path) ? params.path : [params.path ?? ""];
    const leaf = segs[0] ?? "";
    if (!ALLOWED.has(leaf)) {
        return new Response(JSON.stringify({error: "not found"}), {
            status: 404,
            headers: {"content-type": "application/json"},
        });
    }

    const incoming = new URL(request.url);
    const host = (env.ANALYTICS_HOST ?? DEFAULT_HOST).replace(/\/$/, "");
    const upstream = new URL(`${host}/stats/${leaf}`);
    incoming.searchParams.forEach((v, k) => upstream.searchParams.set(k, v));

    try {
        const r = await fetch(upstream.toString(), {
            method: "GET",
            cf: {cacheTtl: 60, cacheEverything: false},
        });
        return new Response(r.body, {
            status: r.status,
            headers: {
                "content-type": r.headers.get("content-type") ?? "application/json",
                "cache-control": "public, max-age=60",
            },
        });
    } catch {
        return new Response(JSON.stringify({error: "upstream unavailable"}), {
            status: 502,
            headers: {"content-type": "application/json"},
        });
    }
};

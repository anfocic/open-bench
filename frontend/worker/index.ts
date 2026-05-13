interface Env {
  ASSETS: Fetcher;
  ANALYTICS_HOST?: string;
  ADMIN_TOKEN?: string;
}

const DEFAULT_HOST = "https://analytics.openbenchmark.dev";
const STATS_LEAVES = new Set(["summary", "timeseries", "top", "vitals"]);

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const host = (env.ANALYTICS_HOST ?? DEFAULT_HOST).replace(/\/$/, "");

    if (url.pathname === "/api/p" && request.method === "POST") {
      return proxyCollect(request, host);
    }

    if (url.pathname.startsWith("/api/stats/") && request.method === "GET") {
      return proxyStats(request, url, host, env.ADMIN_TOKEN);
    }

    return env.ASSETS.fetch(request);
  },
};

async function proxyCollect(request: Request, host: string): Promise<Response> {
  const headers = new Headers();
  headers.set("content-type", request.headers.get("content-type") ?? "application/json");
  headers.set("user-agent", request.headers.get("user-agent") ?? "");
  headers.set("x-forwarded-for", request.headers.get("cf-connecting-ip") ?? "");
  const cfCountry = request.headers.get("cf-ipcountry");
  if (cfCountry) headers.set("x-country", cfCountry);

  try {
    const upstream = await fetch(`${host}/collect`, {
      method: "POST",
      headers,
      body: await request.text(),
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") ?? "text/plain" },
    });
  } catch {
    return new Response("", { status: 204 });
  }
}

async function proxyStats(
  request: Request,
  url: URL,
  host: string,
  adminToken: string | undefined,
): Promise<Response> {
  const leaf = url.pathname.slice("/api/stats/".length).split("/")[0];
  if (!STATS_LEAVES.has(leaf)) {
    return new Response(JSON.stringify({ error: "not found" }), {
      status: 404,
      headers: { "content-type": "application/json" },
    });
  }

  const upstream = new URL(`${host}/stats/${leaf}`);
  url.searchParams.forEach((v, k) => upstream.searchParams.set(k, v));

  const headers = new Headers();
  if (adminToken) headers.set("authorization", `Bearer ${adminToken}`);

  try {
    const r = await fetch(upstream.toString(), {
      method: "GET",
      headers,
      cf: { cacheTtl: 60, cacheEverything: false },
    });
    return new Response(r.body, {
      status: r.status,
      headers: {
        "content-type": r.headers.get("content-type") ?? "application/json",
        "cache-control": "public, max-age=60",
      },
    });
  } catch {
    return new Response(JSON.stringify({ error: "upstream unavailable" }), {
      status: 502,
      headers: { "content-type": "application/json" },
    });
  }
}

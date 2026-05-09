interface Env {
    ANALYTICS_HOST?: string;
}

const DEFAULT_HOST = "https://analytics.openbenchmark.dev";

export const onRequestPost: PagesFunction<Env> = async ({request, env}) => {
    const host = (env.ANALYTICS_HOST ?? DEFAULT_HOST).replace(/\/$/, "");

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
            headers: {"content-type": upstream.headers.get("content-type") ?? "text/plain"},
        });
    } catch {
        return new Response("", {status: 204});
    }
};

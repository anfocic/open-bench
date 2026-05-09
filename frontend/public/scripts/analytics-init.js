import { Analytics } from "/scripts/pagetally.js";

const analytics = new Analytics({
  siteId: "openbenchmark",
  endpoint: "/api/p",
  respectDNT: true,
});

window.pagetally = analytics;

document.addEventListener("astro:after-swap", () => analytics.page());

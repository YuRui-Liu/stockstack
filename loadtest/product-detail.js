import http from "k6/http";
import { check, fail } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

const BASE_URL = (__ENV.BASE_URL || "http://localhost:8080").replace(/\/$/, "");
const PRODUCT_ID = __ENV.PRODUCT_ID || "0198c8bc-1234-7abc-8def-0123456789ab";
const SCENARIO = __ENV.SCENARIO || "cached";
const BASELINE_URL = __ENV.BASELINE_URL || "";

function randomHex(length) {
  let value = "";
  for (let index = 0; index < length; index += 1) {
    value += Math.floor(Math.random() * 16).toString(16);
  }
  return value;
}

function uuidV7() {
  // UUIDv7: 48-bit Unix epoch milliseconds, version 7, RFC 4122 variant 10.
  const timestamp = Date.now().toString(16).padStart(12, "0").slice(-12);
  const variant = (8 + Math.floor(Math.random() * 4)).toString(16);
  return `${timestamp.slice(0, 8)}-${timestamp.slice(8)}-7${randomHex(3)}-${variant}${randomHex(3)}-${randomHex(12)}`;
}

// Generated independently by each k6 runtime; callers can pin a known-absent value.
const MISSING_PRODUCT_ID = __ENV.MISSING_ID || uuidV7();

const scenarioOptions = {
  cached: { executor: "constant-vus", vus: 50, duration: "30s" },
  missing: { executor: "constant-vus", vus: 20, duration: "30s" },
  "hot-expiry": { executor: "constant-vus", vus: 100, duration: "10s" },
  "direct-baseline": { executor: "constant-vus", vus: 50, duration: "30s" },
};

if (!scenarioOptions[SCENARIO]) {
  throw new Error(
    `Unsupported SCENARIO=${SCENARIO}; use cached, missing, hot-expiry, or direct-baseline`,
  );
}

export const options = {
  scenarios: {
    [SCENARIO]: scenarioOptions[SCENARIO],
  },
  thresholds:
    SCENARIO === "cached"
      ? {
          "http_req_failed{scenario:cached}": ["rate<0.001"],
          "http_req_duration{scenario:cached}": ["p(95)<200"],
          unexpected_status: ["rate<0.001"],
        }
      : { unexpected_status: ["rate<0.001"] },
};

const scenarioLatency = new Trend("cache_scenario_latency", true);
const responseStatuses = new Counter("response_status_total");
const status429 = new Counter("response_status_429");
const status503 = new Counter("response_status_503");
const unexpectedStatus = new Rate("unexpected_status");

export function setup() {
  if (SCENARIO === "direct-baseline" && !BASELINE_URL) {
    fail(
      "SCENARIO=direct-baseline requires BASELINE_URL pointing to a separately provided direct-read endpoint; the management API is authenticated and is not a valid public baseline",
    );
  }
}

function record(response, expectedStatus) {
  scenarioLatency.add(response.timings.duration, { scenario: SCENARIO });
  responseStatuses.add(1, { scenario: SCENARIO, status: String(response.status) });
  status429.add(response.status === 429 ? 1 : 0, { scenario: SCENARIO });
  status503.add(response.status === 503 ? 1 : 0, { scenario: SCENARIO });
  unexpectedStatus.add(response.status !== expectedStatus, { scenario: SCENARIO });
}

export default function () {
  const missing = SCENARIO === "missing";
  const productId = missing ? MISSING_PRODUCT_ID : PRODUCT_ID;
  const url =
    SCENARIO === "direct-baseline"
      ? BASELINE_URL.replaceAll("{PRODUCT_ID}", PRODUCT_ID)
      : `${BASE_URL}/api/v1/public/products/${productId}`;
  const expectedStatus = missing ? 404 : 200;
  const response = http.get(url, {
    responseCallback: http.expectedStatuses(expectedStatus),
    tags: { load_scenario: SCENARIO },
  });

  record(response, expectedStatus);
  check(response, { [`status is ${expectedStatus}`]: (r) => r.status === expectedStatus });
}

// For hot-expiry, immediately before starting k6, clear the seeded product key externally:
// docker compose exec -T redis redis-cli DEL product:v1:0198c8bc-1234-7abc-8def-0123456789ab
// Then run SCENARIO=hot-expiry so all VUs request the same ID. Correlate this script's
// latency/status output with the application's database-fallback metric; k6 cannot prove
// single-flight behavior from an HTTP response alone.

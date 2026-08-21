import http from "k6/http";
import { check } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

// Operator-owned fault injection (this script never controls Docker):
//   Before:  docker compose pause redis
//   Finally: docker compose unpause redis
// Always run the unpause command, including after an interrupted or failed k6 run.

const BASE_URL = (__ENV.BASE_URL || "http://localhost:8080").replace(/\/$/, "");
const PRODUCT_ID = __ENV.PRODUCT_ID || "0198c8bc-1234-7abc-8def-0123456789ab";

export const options = {
  scenarios: {
    redis_degraded: { executor: "constant-vus", vus: 20, duration: "30s" },
  },
  thresholds: {
    connection_error: ["rate<0.001"],
    unexpected_status: ["rate<0.001"],
  },
};

const degradedLatency = new Trend("redis_degraded_latency", true);
const responseStatuses = new Counter("response_status_total");
const status200 = new Counter("response_status_200");
const status429 = new Counter("response_status_429");
const status503 = new Counter("response_status_503");
const serviceAvailable = new Rate("service_available");
const controlledDegradation = new Rate("controlled_degradation");
const connectionError = new Rate("connection_error");
const unexpectedStatus = new Rate("unexpected_status");

export default function () {
  const response = http.get(`${BASE_URL}/api/v1/public/products/${PRODUCT_ID}`, {
    responseCallback: http.expectedStatuses(200, 429, 503),
  });
  const accepted = response.status === 200 || response.status === 429 || response.status === 503;

  degradedLatency.add(response.timings.duration);
  responseStatuses.add(1, { status: String(response.status) });
  status200.add(response.status === 200 ? 1 : 0);
  status429.add(response.status === 429 ? 1 : 0);
  status503.add(response.status === 503 ? 1 : 0);
  serviceAvailable.add(response.status === 200);
  controlledDegradation.add(response.status === 429 || response.status === 503);
  connectionError.add(response.status === 0);
  unexpectedStatus.add(!accepted);

  check(response, {
    "status is 200 or controlled 429/503": () => accepted,
  });
}

// Because responseCallback marks 200/429/503 as expected, http_req_failed only captures
// non-controlled HTTP statuses or transport failures. It is not the service success rate;
// use service_available plus the explicit 200/429/503 counters when reporting availability.

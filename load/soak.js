// k6 load certification scenario: 10k assets/minute sustained under 500ms p95 latency
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },
    { duration: '3m', target: 167 }, // ~10,000 req / minute
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.001'],
  },
};

export default function () {
  const payload = JSON.stringify({
    batch_id: `batch-k6-${__VU}-${__ITER}`,
    assets: [
      {
        asset_id: `sample-${__ITER}`,
        source_uri: 'https://example.com/asset.txt',
        mime_type: 'text/plain',
      },
    ],
  });

  const res = http.post('http://localhost:8000/v1/ingest', payload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(0.1);
}

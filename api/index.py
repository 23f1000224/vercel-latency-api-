
import json
import math
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI()

DATA_FILE = Path(__file__).parent / "q-vercel-latency.json"

with open(DATA_FILE, "r") as f:
    DATA = json.load(f)


@app.middleware("http")
async def force_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response(status_code=204)
    else:
        response = await call_next(request)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Expose-Headers"] = "Access-Control-Allow-Origin"
    return response


def percentile95(values):
    values = sorted(values)
    position = (len(values) - 1) * 0.95
    lower = math.floor(position)
    upper = math.ceil(position)
    return values[lower] + (
        values[upper] - values[lower]
    ) * (position - lower)


@app.post("/")
async def analytics(request: Request):
    body = await request.json()
    regions = body.get("regions", [])
    threshold = float(body.get("threshold_ms", 180))

    result = {}

    for region in regions:
        rows = [r for r in DATA if r["region"] == region]

        if not rows:
            continue

        latencies = [r["latency_ms"] for r in rows]
        uptimes = [r["uptime_pct"] for r in rows]

        result[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": percentile95(latencies),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(x > threshold for x in latencies),
        }

    return JSONResponse(content={"regions": result})

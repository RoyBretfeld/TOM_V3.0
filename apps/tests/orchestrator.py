"""
TOM v3.0 - Test Orchestrator
FastAPI-Service für automatisierte Tests
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


app = FastAPI(title="TOM v3.0 Test Orchestrator")

# Test-Ergebnisse in Memory
test_runs: Dict[str, 'TestRun'] = {}


class TestRun(BaseModel):
    """Test-Run Status und Ergebnisse"""
    run_id: str
    start_time: str
    end_time: Optional[str] = None
    status: str  # pending, running, completed, failed
    results: List[dict] = []
    summary: Optional[dict] = None


@app.get("/tests/latest")
async def get_latest_test():
    """Gibt den letzten Test-Run zurück"""
    if not test_runs:
        return {"error": "No tests run yet"}
    
    latest_run_id = max(test_runs.keys(), key=lambda k: test_runs[k].start_time)
    run = test_runs[latest_run_id]
    
    return {
        "run_id": run.run_id,
        "status": run.status,
        "summary": run.summary,
        "results_count": len(run.results)
    }


@app.post("/tests/run")
async def trigger_test_run(background_tasks: BackgroundTasks):
    """Löst einen Test-Run aus"""
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    run = TestRun(
        run_id=run_id,
        start_time=datetime.now().isoformat(),
        status="running"
    )
    test_runs[run_id] = run
    
    # Test-Run im Hintergrund starten
    background_tasks.add_task(run_tests, run)
    
    return {
        "run_id": run_id,
        "status": "started",
        "message": "Test run started"
    }


@app.get("/tests/stream/{run_id}")
async def stream_test_events(run_id: str):
    """Streamt Test-Events via SSE"""
    async def generate():
        if run_id not in test_runs:
            yield "data: " + json.dumps({"error": "Run not found"}) + "\n\n"
            return
            
        run = test_runs[run_id]
        
        # Bisherige Events senden
        for event in run.results:
            yield "data: " + json.dumps(event) + "\n\n"
            await asyncio.sleep(0.01)
        
        # Live Events streamen
        initial_count = len(run.results)
        while run.status == "running":
            if len(run.results) > initial_count:
                for event in run.results[initial_count:]:
                    yield "data: " + json.dumps(event) + "\n\n"
                initial_count = len(run.results)
            
            await asyncio.sleep(0.5)
        
        # Final Event
        yield "data: " + json.dumps({
            "type": "run_complete",
            "status": run.status,
            "summary": run.summary
        }) + "\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/tests/{run_id}")
async def get_test_run(run_id: str):
    """Gibt Test-Run Details zurück"""
    if run_id not in test_runs:
        return {"error": "Run not found"}
    
    run = test_runs[run_id]
    return {
        "run_id": run.run_id,
        "start_time": run.start_time,
        "end_time": run.end_time,
        "status": run.status,
        "summary": run.summary,
        "results": run.results
    }


async def run_tests(run: TestRun):
    """Führt Tests aus und sammelt Ergebnisse"""
    logger.info(f"Starting test run {run.run_id}")
    
    try:
        # Test-Suite definieren
        test_suite = [
            {"name": "test_stt_latency", "component": "stt"},
            {"name": "test_llm_latency", "component": "llm"},
            {"name": "test_tts_latency", "component": "tts"},
            {"name": "test_e2e_latency", "component": "pipeline"},
            {"name": "test_barge_in", "component": "telephony"},
            {"name": "test_audio_quality", "component": "audio"},
            {"name": "test_rl_policy", "component": "rl"},
            {"name": "test_rl_reward", "component": "rl"},
            {"name": "test_freeswitch_integration", "component": "telephony"},
            {"name": "test_monitoring", "component": "monitoring"},
            {"name": "test_security", "component": "security"},
            {"name": "test_toolhub", "component": "toolhub"}
        ]
        
        # Tests ausführen
        for test in test_suite:
            try:
                result = await execute_test(test)
                run.results.append(result)
                
            except Exception as e:
                logger.error(f"Test {test['name']} failed: {e}")
                run.results.append({
                    "test": test['name'],
                    "status": "failed",
                    "error": str(e)
                })
        
        # Zusammenfassung berechnen
        passed = sum(1 for r in run.results if r.get('status') == 'passed')
        failed = sum(1 for r in run.results if r.get('status') == 'failed')
        
        run.summary = {
            "total": len(test_suite),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(test_suite) if test_suite else 0
        }
        
        run.status = "completed" if failed == 0 else "failed"
        run.end_time = datetime.now().isoformat()
        
        # Ergebnisse persistieren
        persist_test_results(run)
        
        logger.info(f"Test run {run.run_id} completed: {passed}/{len(test_suite)} passed")
        
    except Exception as e:
        logger.error(f"Test run {run.run_id} failed: {e}")
        run.status = "failed"
        run.end_time = datetime.now().isoformat()


async def execute_test(test_config: dict) -> dict:
    """Führt einzelnen Test aus"""
    test_name = test_config['name']
    component = test_config['component']
    
    # Placeholder-Test-Implementierung
    # Hier würden echte Tests ausgeführt
    await asyncio.sleep(0.1)  # Simuliere Test-Laufzeit
    
    # Mock-Ergebnisse
    result = {
        "test": test_name,
        "component": component,
        "status": "passed",
        "duration_ms": 100,
        "timestamp": datetime.now().isoformat()
    }
    
    # Beispiel: E2E-Latenz Test
    if test_name == "test_e2e_latency":
        result["metrics"] = {
            "e2e_ms": 450,
            "stt_ms": 150,
            "llm_ms": 200,
            "tts_ms": 100
        }
    
    return result


def persist_test_results(run: TestRun):
    """Persistiert Test-Ergebnisse in JSONL"""
    results_dir = Path("data/test_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = results_dir / f"{run.run_id}.jsonl"
    
    with open(results_file, 'w') as f:
        for result in run.results:
            f.write(json.dumps(result) + '\n')
    
    logger.info(f"Test results persisted to {results_file}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8087)


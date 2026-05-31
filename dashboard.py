"""
GMB HUNTER — DASHBOARD SERVER
Flask backend that connects the visual dashboard to the scraping system.
Run: python dashboard.py
Then open: http://localhost:5000
"""

import sys
import os
import json
import threading
import subprocess
from datetime import datetime, date
from flask import Flask, render_template, request, jsonify, send_file

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from scheduler import load_jobs, save_jobs, run_job

app = Flask(__name__)

# Global scraping state
scraping_state = {
    "running":   False,
    "progress":  0,
    "target":    100,
    "current":   "",
    "saved":     0,
    "skipped":   0,
    "log":       [],
    "done":      False,
    "error":     None,
}


# ── Pages ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── API: Stats ───────────────────────────────────────────────────────────────

@app.route("/api/stats")
def get_stats():
    try:
        db = DatabaseManager()
        conn = db.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM businesses")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as today FROM businesses WHERE scraped_date = ?", (str(date.today()),))
        today = cursor.fetchone()["today"]

        cursor.execute("SELECT COUNT(*) as emails FROM businesses WHERE email != '' AND email IS NOT NULL")
        emails = cursor.fetchone()["emails"]

        cursor.execute("SELECT COUNT(*) as phones FROM businesses WHERE phone_number != '' AND phone_number IS NOT NULL")
        phones = cursor.fetchone()["phones"]

        cursor.execute("SELECT COUNT(DISTINCT city) as cities FROM businesses")
        cities = cursor.fetchone()["cities"]

        cursor.execute("SELECT COUNT(DISTINCT category) as categories FROM businesses")
        categories = cursor.fetchone()["categories"]

        conn.close()

        return jsonify({
            "total":      total,
            "today":      today,
            "emails":     emails,
            "phones":     phones,
            "cities":     cities,
            "categories": categories,
            "email_pct":  round(emails / total * 100) if total else 0,
            "phone_pct":  round(phones / total * 100) if total else 0,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Records ─────────────────────────────────────────────────────────────

@app.route("/api/records")
def get_records():
    try:
        db     = DatabaseManager()
        conn   = db.connect()
        cursor = conn.cursor()

        search   = request.args.get("search", "")
        city     = request.args.get("city", "")
        category = request.args.get("category", "")
        page     = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))
        offset   = (page - 1) * per_page

        query  = "SELECT * FROM businesses WHERE 1=1"
        params = []

        if search:
            query += " AND (business_name LIKE ? OR email LIKE ? OR phone_number LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        if city:
            query += " AND city LIKE ?"
            params.append(f"%{city}%")
        if category:
            query += " AND category LIKE ?"
            params.append(f"%{category}%")

        # Count total
        count_query = query.replace("SELECT *", "SELECT COUNT(*) as cnt")
        cursor.execute(count_query, params)
        total = cursor.fetchone()["cnt"]

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        return jsonify({"records": rows, "total": total, "page": page, "per_page": per_page})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/filters")
def get_filters():
    """Get unique cities and categories for filter dropdowns"""
    try:
        db     = DatabaseManager()
        conn   = db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT city FROM businesses WHERE city != '' ORDER BY city")
        cities = [r["city"] for r in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT category FROM businesses WHERE category != '' ORDER BY category")
        categories = [r["category"] for r in cursor.fetchall()]
        conn.close()
        return jsonify({"cities": cities, "categories": categories})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Download ────────────────────────────────────────────────────────────

@app.route("/api/download/<fmt>")
def download_file(fmt):
    try:
        import pandas as pd
        db     = DatabaseManager()
        conn   = db.connect()
        cursor = conn.cursor()

        search   = request.args.get("search", "")
        city     = request.args.get("city", "")
        category = request.args.get("category", "")

        query  = "SELECT business_name,phone_number,email,website,rating,review_count,address,city,category,source,scraped_date FROM businesses WHERE 1=1"
        params = []
        if search:
            query += " AND (business_name LIKE ? OR email LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if city:
            query += " AND city LIKE ?"
            params.append(f"%{city}%")
        if category:
            query += " AND category LIKE ?"
            params.append(f"%{category}%")

        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        df       = pd.DataFrame(rows)
        os.makedirs("output", exist_ok=True)
        filename = f"gmb_export_{date.today()}"

        if fmt == "csv":
            path = f"output/{filename}.csv"
            df.to_csv(path, index=False, encoding="utf-8-sig")
            return send_file(os.path.abspath(path), as_attachment=True)
        elif fmt == "xlsx":
            path = f"output/{filename}.xlsx"
            df.to_excel(path, index=False)
            return send_file(os.path.abspath(path), as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Scraping ────────────────────────────────────────────────────────────

def run_scraping_thread(business_type, city, target):
    """Run scraping in background thread"""
    global scraping_state
    scraping_state.update({
        "running": True, "progress": 0, "target": target,
        "saved": 0, "skipped": 0, "log": [], "done": False, "error": None
    })

    try:
        from agents.scout_agent  import ScoutAgent
        from agents.detail_agent import DetailAgent
        from agents.saver_agent  import SaverAgent

        db     = DatabaseManager()
        saver  = SaverAgent(business_type=business_type, city=city)
        scout  = ScoutAgent()
        detail = DetailAgent()

        scraping_state["log"].append(f"🔍 Scout Agent starting...")
        raw = scout.collect(business_type, city, target=target)
        scraping_state["log"].append(f"✅ Scout found {len(raw)} businesses")

        scraping_state["log"].append(f"🤖 Detail Agent enriching data...")
        enriched = detail.enrich_all(raw)

        for i, biz in enumerate(enriched):
            name = biz.get("business_name", "")
            if db.is_duplicate(biz):
                scraping_state["skipped"] += 1
                continue
            db.save_business(biz)
            saver.save(biz)
            scraping_state["saved"]   += 1
            scraping_state["progress"] = scraping_state["saved"]
            scraping_state["current"]  = name
            scraping_state["log"].append(
                f"💾 [{scraping_state['saved']}] {name[:40]} | "
                f"{biz.get('phone_number','')[:15]}"
            )
            if len(scraping_state["log"]) > 100:
                scraping_state["log"] = scraping_state["log"][-100:]

        scraping_state["done"]    = True
        scraping_state["running"] = False
        scraping_state["log"].append(f"🎉 Done! Saved: {scraping_state['saved']} | Skipped: {scraping_state['skipped']}")

    except Exception as e:
        scraping_state["error"]   = str(e)
        scraping_state["running"] = False
        scraping_state["done"]    = True
        scraping_state["log"].append(f"❌ Error: {e}")


@app.route("/api/scrape/start", methods=["POST"])
def start_scrape():
    global scraping_state
    if scraping_state["running"]:
        return jsonify({"error": "Scraping already in progress"}), 400

    data          = request.json or {}
    business_type = data.get("business_type", "restaurants")
    city          = data.get("city", "Lahore")
    target        = int(data.get("target", 100))

    thread = threading.Thread(
        target=run_scraping_thread,
        args=(business_type, city, target),
        daemon=True
    )
    thread.start()
    return jsonify({"status": "started"})


@app.route("/api/scrape/status")
def scrape_status():
    return jsonify(scraping_state)


@app.route("/api/scrape/stop", methods=["POST"])
def stop_scrape():
    global scraping_state
    scraping_state["running"] = False
    scraping_state["done"]    = True
    return jsonify({"status": "stopped"})


# ── API: Scheduler ───────────────────────────────────────────────────────────

@app.route("/api/jobs")
def get_jobs():
    return jsonify(load_jobs())


@app.route("/api/jobs/add", methods=["POST"])
def add_job_api():
    data = request.json or {}
    job  = {
        "id":            f"{data.get('business_type','')}_{data.get('city','')}_{data.get('run_time','')}".replace(" ", "_").lower(),
        "business_type": data.get("business_type", ""),
        "city":          data.get("city", ""),
        "run_time":      data.get("run_time", "08:00"),
        "target":        int(data.get("target", 100)),
        "active":        True,
        "created_at":    str(datetime.now()),
        "last_run":      None,
        "total_runs":    0,
        "total_records": 0,
    }
    jobs = load_jobs()
    jobs.append(job)
    save_jobs(jobs)
    return jsonify({"status": "added", "job": job})


@app.route("/api/jobs/delete/<job_id>", methods=["DELETE"])
def delete_job(job_id):
    jobs = [j for j in load_jobs() if j["id"] != job_id]
    save_jobs(jobs)
    return jsonify({"status": "deleted"})


@app.route("/api/jobs/toggle/<job_id>", methods=["POST"])
def toggle_job(job_id):
    jobs = load_jobs()
    for j in jobs:
        if j["id"] == job_id:
            j["active"] = not j.get("active", True)
    save_jobs(jobs)
    return jsonify({"status": "toggled"})


if __name__ == "__main__":
    print("\n" + "="*52)
    print("  GMB HUNTER DASHBOARD")
    print("  Open browser: http://localhost:5000")
    print("="*52 + "\n")
    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)
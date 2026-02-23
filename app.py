"""Flask app for AI Debate Lab."""
import json
from io import BytesIO
from datetime import datetime
from flask import Flask, render_template, request, Response, jsonify, send_file
from debate import run_debate, save_run, list_runs, get_run

app = Flask(__name__)

# Cost protection guardrails
DAILY_DEBATE_LIMIT = 40
MAX_TURNS_PER_DEBATE = 6

# Global daily counter (simple in-memory, resets daily)
daily_debates = {'date': None, 'count': 0}


def generate_debate_pdf(run_data):
    """Generate a PDF report of the debate using reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="DebateTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        name="Speaker",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = styles["Normal"]

    story = []
    topic = run_data.get("topic", "Debate")
    timestamp = run_data.get("timestamp", "")
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        date_str = dt.strftime("%B %d, %Y at %I:%M %p")
    except Exception:
        date_str = timestamp

    def escape_xml(s):
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    story.append(Paragraph("AI Debate Lab — Full Report", title_style))
    story.append(Paragraph(f"<b>Topic:</b> {escape_xml(topic)}", body_style))
    story.append(Paragraph(f"<b>Date:</b> {escape_xml(date_str)}", body_style))
    story.append(Spacer(1, 0.3 * inch))

    for entry in run_data.get("transcript", []):
        speaker = escape_xml(entry.get("speaker", "Speaker"))
        role = entry.get("role", "")
        if role in ["pro", "con"]:
            base = "PRO" if role == "pro" else "CON"
            custom = entry.get("role_label", "")
            if custom and custom != base:
                display_role = f"{base}: {custom}"
            else:
                display_role = base
        else:
            display_role = {"moderator": "Moderator", "judge": "Judge"}.get(role, role)
        text = escape_xml(entry.get("text") or "").replace("\n", "<br/>")
        story.append(Paragraph(f"<b>{speaker}</b> ({display_role})", heading_style))
        story.append(Paragraph(text, body_style))
        story.append(Spacer(1, 0.15 * inch))

    doc.build(story)
    buffer.seek(0)
    return buffer


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/debate/start", methods=["POST"])
def start_debate():
    data = request.get_json() or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    # Check daily debate limit
    today = datetime.now().date()
    global daily_debates
    if daily_debates['date'] != today:
        daily_debates = {'date': today, 'count': 0}
    if daily_debates['count'] >= DAILY_DEBATE_LIMIT:
        return jsonify({"error": "Daily debate limit reached. Try again tomorrow."}), 429
    daily_debates['count'] += 1

    bot_a_name = (data.get("bot_a_name") or "").strip() or None
    bot_b_name = (data.get("bot_b_name") or "").strip() or None
    bot_a_role = (data.get("bot_a_role") or "").strip() or None
    bot_b_role = (data.get("bot_b_role") or "").strip() or None
    max_turns = data.get("max_turns", 4)
    try:
        max_turns = int(max_turns)
        max_turns = max(1, min(MAX_TURNS_PER_DEBATE, max_turns))  # Cap at 6
    except (ValueError, TypeError):
        max_turns = 4

    def generate():
        messages_sent = []

        def on_msg(msg):
            messages_sent.append(msg)

        run_result = run_debate(
            topic,
            on_message=on_msg,
            bot_a_name=bot_a_name,
            bot_b_name=bot_b_name,
            bot_a_role=bot_a_role,
            bot_b_role=bot_b_role,
            max_turns=max_turns,
        )
        save_run(run_result)

        for msg in messages_sent:
            yield f"data: {json.dumps(msg)}\n\n"

        yield f"data: {json.dumps({'done': True, 'run_id': run_result['run_id']})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/debates")
def api_list_debates():
    runs = list_runs()
    return jsonify(runs)


@app.route("/api/debates/<run_id>")
def api_get_debate(run_id):
    run = get_run(run_id)
    if run is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(run)


@app.route("/api/debates/<run_id>/report.pdf")
def api_debate_report_pdf(run_id):
    run = get_run(run_id)
    if run is None:
        return jsonify({"error": "Not found"}), 404
    buffer = generate_debate_pdf(run)
    safe_topic = "".join(c if c.isalnum() or c in " -_" else "_" for c in run.get("topic", "debate")[:50])
    filename = f"debate-report-{safe_topic}-{run_id}.pdf"
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)

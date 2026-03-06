# AI Debate Lab

> A fully deployed, multi-agent AI application where two AI bots debate any topic you throw at them.

---

## Overview

AI Debate Lab is a multi-agent AI application that simulates structured debates between two AI bots on any topic you provide. Simply enter a debatable prompt, customize each bot's name and role, and watch a moderated, judged debate unfold in real time.

Built as a portfolio project to demonstrate real-world AI engineering skills — including multi-agent orchestration, stateful conversation management, and a polished production deployment.

**[Try it live at debate.evankhanna.dev](https://debate.evankhanna.dev)**

---

## Features

- **Custom Debate Setup** — Enter any debatable topic and optionally assign each bot a custom name and persona/role
- **Configurable Turn Count** — Set how many turns the debate runs
- **4-Agent Architecture** — Two debater bots, one moderator bot, and one judge bot all powered by the OpenAI API
- **Live Moderation** — A moderator bot steps in every two turns to guide and steer the conversation
- **AI Judge & Scoring** — At the end of the debate, a judge bot scores each participant, provides a summary, and suggests improvements for each side
- **PDF Export** — Download a formatted, printable, and shareable PDF transcript of the full debate via ReportLab
- **Context-Aware Bots** — All agents maintain full conversational context across turns for coherent, progressive argumentation

---

## How It Works

```
User Input (Topic + Names + Roles + Turns)
           │
           ▼
   ┌───────────────┐
   │  Debater Bot A │◄──────────────────────┐
   └───────┬───────┘                        │
           │ argues FOR                     │
           ▼                                │
   ┌───────────────┐              Every 2 turns
   │  Debater Bot B │                       │
   └───────┬───────┘              ┌─────────┴────────┐
           │ argues AGAINST       │  Moderator Bot   │
           └──────────────────────┤  (guides debate) │
                                  └──────────────────┘
                                           │
                              After all turns complete
                                           │
                                  ┌────────▼────────┐
                                  │   Judge Bot     │
                                  │ Scores + Summary│
                                  │  + Suggestions  │
                                  └────────┬────────┘
                                           │
                                  ┌────────▼────────┐
                                  │  PDF Transcript │
                                  │   (Download)    │
                                  └─────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python, Flask |
| **AI / LLM** | OpenAI API (GPT) |
| **State Management** | Flask Sessions |
| **PDF Generation** | ReportLab |
| **Frontend** | HTML, CSS, JavaScript |
| **Deployment** | Render |
| **Domain / CDN** | Cloudflare |

---

## Getting Started

### Prerequisites

- Python 3.8+
- An [OpenAI API key](https://platform.openai.com/api-keys)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/your-username/ai-debate-lab.git
cd ai-debate-lab
```

2. **Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_openai_api_key_here
FLASK_SECRET_KEY=your_secret_key_here
```

5. **Run the application**

```bash
flask run
```

The app will be available at `http://localhost:5000`.

---

## Usage

1. Navigate to the app in your browser
2. Enter a debatable topic (e.g., *"AI will replace most jobs within 20 years"*)
3. Optionally assign custom names and roles/personas to each bot
4. Set the number of debate turns
5. Click **Start Debate** and watch the bots argue it out
6. Read the judge's final summary and scores
7. Click **Download PDF** to export a formatted transcript

### Example Topics

- *"Universal Basic Income would benefit society"*
- *"Remote work is more productive than in-office work"*
- *"Social media does more harm than good"*
- *"Nuclear energy is the best solution to climate change"*

---

## Project Structure

```
ai-debate-lab/
├── app.py                  # Main Flask application & route handlers
├── agents/
│   ├── debater.py          # Debater bot logic
│   ├── moderator.py        # Moderator bot logic
│   └── judge.py            # Judge bot scoring & summary logic
├── utils/
│   └── pdf_generator.py    # ReportLab PDF transcript generation
├── templates/
│   └── index.html          # Main frontend template
├── static/
│   ├── css/
│   │   └── style.css       # Application styles
│   └── js/
│       └── main.js         # Frontend interaction logic
├── requirements.txt
├── .env.example
└── README.md
```

---

## Configuration

| Variable | Description | Required |
|---|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key | ✅ Yes |
| `FLASK_SECRET_KEY` | Secret key for Flask session management | ✅ Yes |

---

## Agent Design

The application uses **four distinct AI agents**, each with a focused system prompt and role:

- **Debater A** — Argues in favor of the given topic. Can be customized with a name and persona.
- **Debater B** — Argues against the given topic. Can be customized with a name and persona.
- **Moderator** — Intervenes every two turns to keep the debate structured, on-topic, and intellectually rigorous.
- **Judge** — Reviews the full transcript after the final turn and produces a structured evaluation including scores, a summary of each side's performance, and suggested improvements.

All agents receive the full conversation history on each call to maintain contextual awareness throughout the debate.

---

## Use Cases

AI Debate Lab is a versatile tool with applications across many domains:

- **Education** — Classroom debates, exploring multiple sides of an argument
- **Legal Prep** — Stress-testing arguments before a case
- **Business Strategy** — Red-teaming ideas and business decisions
- **Political Science** — Analyzing policy trade-offs from different viewpoints
- **Personal Development** — Sharpening critical thinking and rhetoric skills

---

## Deployment

The application is deployed on **[Render](https://render.com)** with a custom domain managed through **Cloudflare**.

To deploy your own instance on Render:

1. Push your repository to GitHub
2. Create a new **Web Service** on Render and connect your repo
3. Set the build command: `pip install -r requirements.txt`
4. Set the start command: `gunicorn app:app`
5. Add your environment variables (`OPENAI_API_KEY`, `FLASK_SECRET_KEY`) in the Render dashboard

---

## Potential Enhancements

- Support for additional LLM providers (Anthropic Claude, Google Gemini)
- Audience voting / real-time spectator mode
- Debate history saved to a database per user
- Streaming responses for real-time bot typing effect
- Voice mode using text-to-speech for each bot
- Pre-built topic library by category

---

## Author

**Evan A. Khanna**

- Website: [debate.evankhanna.dev](https://debate.evankhanna.dev)
- LinkedIn: [linkedin.com/in/evan-khanna-dareshift](https://www.linkedin.com/in/evan-khanna-dareshift)

---

## License

This project is open source and available under the [MIT License](LICENSE).

---

*Built with curiosity, caffeine, and a lot of multi-agent debugging.*

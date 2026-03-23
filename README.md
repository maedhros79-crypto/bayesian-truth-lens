# Bayesian Truth Lens

A claim assessment tool built on the Examined Uncertainty principle.
Not an oracle. A structured thinking aid.

## What it does

- Classifies any claim into one of 7 epistemic categories
- Returns a confidence tier: LOW / MEDIUM / HIGH (never binary true/false)
- Surfaces the assumptions underneath the assessment
- Flags clever defection in political claims
- Finds the kernel of truth in conspiracy claims before assessing the full claim
- Flags absent evidence as a research lead, not a dead end
- Ends with a Socratic question aimed at your own axioms

## Setup

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Run the app:
```
streamlit run app.py
```

3. Enter your Anthropic API key in the UI when prompted.
   Get one at: https://console.anthropic.com

## Files

- `app.py` — Streamlit UI
- `assessor.py` — Core logic, API calls, response parsing
- `prompts.py` — System prompt embodying the Examined Uncertainty heuristic
- `requirements.txt` — Dependencies

## Notes

- The app uses your Anthropic API key only for the current session
- It never stores your key
- Assessment quality depends on what the model knows — always verify independently
- This is MVP / Quick Assessment mode. Deep Dive mode is the next build phase.

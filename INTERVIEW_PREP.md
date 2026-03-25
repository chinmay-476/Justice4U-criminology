# Criminology Project Interview Prep

## Project One-Liner
Justice4U Criminology is a Flask-based criminal case workflow platform for admins, super-admins, and judges, with accused records, complaint handling, judge decision tracking, and WebRTC-based hearing support.

## Tech Stack
- `Python`
- `Flask`
- `SQLAlchemy`
- `MySQL` / `SQLite` for tests
- `HTML`
- `Bootstrap`
- `Jinja2`
- `JavaScript`
- `WebRTC`
- `Node.js`
- `Socket.IO`
- `Redis`

## Features You Should Mention
- Accused intake and criminal case record management
- Complaint registration tied to case numbers
- Automatic `JudgeDecision` workflow creation from intake and complaint flow
- Structured judge workspace with hearing summary, evidence review, order notes, and family/complainant communication note
- Pending and solved case views for judicial workflow
- Internal video call room creation and validation
- Hybrid realtime design using Flask business APIs plus Node signaling

## Concepts To Learn Before an Interview
- Flask + SQLAlchemy architecture
- ORM models and relationships
- workflow/state machine design
- role-based access control
- secure internal APIs
- WebRTC basics
- STUN vs TURN
- signaling server responsibilities
- why Redis is useful for realtime room state
- database repair / startup migration patterns

## Good Architecture Points To Say
- I kept Flask for case management and auth, but separated realtime signaling concerns to a dedicated Node/WebSocket layer for better reliability.
- I made judge workflow records auto-created from earlier intake stages so cases do not vanish from the pending queue.
- I moved the judge UI toward a decision workspace model to reduce cognitive load and keep punishment lookup, hearing notes, and order drafting in one place.
- I kept old-database compatibility by adding startup schema checks and safe record repair logic.

## Good Interview Questions To Practice
- Why is Flask alone not ideal for scalable realtime signaling?
- What is the role of TURN in a WebRTC architecture?
- How does your judicial workflow avoid missing pending decisions?
- How do you store structured judge notes without breaking old data?
- How would you harden this system for real production court usage?

from datetime import datetime

from sqlalchemy import func

from extensions import db
from models import JudgeDecision


WORKFLOW_STAGE_ORDER = {
    'Filed': 0,
    'Complaint Registered': 1,
    'Pending Judge Review': 2,
    'Order Prepared': 3,
    'Closed': 4,
}


def normalize_case_no(case_no):
    return (case_no or '').strip().lower()


def get_judge_decision_for_case(case_no):
    key = normalize_case_no(case_no)
    if not key:
        return None
    return (
        JudgeDecision.query
        .filter(func.lower(func.trim(JudgeDecision.case_no)) == key)
        .first()
    )


def promote_stage(current_stage, desired_stage):
    if not desired_stage:
        return current_stage or 'Filed'
    current_rank = WORKFLOW_STAGE_ORDER.get(current_stage or 'Filed', -1)
    desired_rank = WORKFLOW_STAGE_ORDER.get(desired_stage, -1)
    return desired_stage if desired_rank >= current_rank else current_stage


def ensure_judge_decision(case_no, status='Pending', workflow_stage='Filed'):
    cleaned_case_no = (case_no or '').strip()
    if not cleaned_case_no:
        return None

    decision = get_judge_decision_for_case(cleaned_case_no)
    if decision:
        if status == 'Solved':
            decision.status = 'Solved'
        elif (decision.status or '').strip().title() not in {'Pending', 'Solved'}:
            decision.status = 'Pending'

        decision.workflow_stage = promote_stage(decision.workflow_stage, workflow_stage)
        if not decision.decided_at:
            decision.decided_at = datetime.now()
        return decision

    decision = JudgeDecision(
        case_no=cleaned_case_no,
        status=status,
        workflow_stage=workflow_stage or 'Filed',
        decided_at=datetime.now(),
    )
    db.session.add(decision)
    return decision

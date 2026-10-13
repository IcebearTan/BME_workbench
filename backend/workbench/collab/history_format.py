"""Independent appointment presentation; mirrors the source history contract."""
import json
from datetime import date


def covered_years(row, today=None):
    today = today or date.today()
    if row.term_start and row.term_end:
        return list(range(row.term_start.year, row.term_end.year + 1))
    if row.status == 'active' and row.term_start:
        return list(range(row.term_start.year, max(today.year, row.term_start.year) + 1))
    return sorted({d.year for d in (row.term_start, row.term_end) if d} |
                  ({row.historical_year} if row.historical_year else set()))


def serialize_history(records, events, year=None, operator_names=None):
    by_officer = {}
    for event in events:
        if not event.kind.startswith('officer_'):
            continue
        try:
            detail = json.loads(event.detail_json or '{}')
        except (ValueError, TypeError):
            detail = {}
        by_officer.setdefault(event.officer_id, []).append({
            'id': event.id, 'kind': event.kind,
            'occurred_at': event.occurred_at.isoformat() if event.occurred_at else None,
            'operator_id': event.operator_id,
            'operator_name': (operator_names or {}).get(event.operator_id), 'detail': detail,
        })
    years = sorted({y for r in records for y in covered_years(r)}, reverse=True)
    output = []
    for row in sorted(records, key=lambda r: (r.term_start or date.min, r.id), reverse=True):
        spans = covered_years(row)
        if year is not None and year not in spans:
            continue
        dates = [row.term_start, row.term_end]
        precision = 'day' if row.term_start and (row.term_end or row.status == 'active') else 'partial' if any(dates) else 'year' if row.historical_year else 'unknown'
        output.append({
            'id': row.id, 'user_id': row.user_id, 'person_id': row.person_id,
            'title': row.title, 'department': row.department, 'org_slot': row.org_slot_snapshot,
            'term_start': row.term_start.isoformat() if row.term_start else None,
            'term_end': row.term_end.isoformat() if row.term_end else None,
            'status': row.status,
            'display_status': 'scheduled' if row.status == 'active' and row.term_start and row.term_start > date.today() else row.status,
            'end_reason': row.end_reason, 'scope_note': row.scope_note,
            'record_source': row.record_source, 'source_note': row.source_note,
            'historical_year': row.historical_year, 'date_precision': precision,
            'appointed_at': row.appointed_at.isoformat() if row.appointed_at else None,
            'ended_at': row.ended_at.isoformat() if row.ended_at else None,
            'recorded_at': row.created_at.isoformat() if row.created_at else None,
            'years': spans, 'events': by_officer.get(row.id, []),
        })
    return {'records': output, 'years': years, 'undated_count': sum(not covered_years(r) for r in records)}

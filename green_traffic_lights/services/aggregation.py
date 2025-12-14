from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from itertools import groupby
from typing import Iterable, List, Sequence

from flask import current_app

from ..extensions import db
from ..models import TrafficLightPass, TrafficLightRange


def _normalize_day(target_day: date | None) -> date:
    if target_day:
        return target_day

    # Aggregate the previous day by default to avoid partial data from the
    # current in-progress day.
    return datetime.now(timezone.utc).date() - timedelta(days=1)


def _day_bounds(target_day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(target_day, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _to_ranges(events: Iterable[TrafficLightPass], target_day: date) -> list[TrafficLightRange]:
    ranges: list[TrafficLightRange] = []

    for light_identifier, items in groupby(events, key=lambda event: event.light_identifier):
        current_range: TrafficLightRange | None = None

        for event in items:
            if current_range is None or current_range.color != event.pass_color:
                if current_range is not None:
                    ranges.append(current_range)

                current_range = TrafficLightRange(
                    light_identifier=light_identifier,
                    color=event.pass_color,
                    start_time=event.pass_timestamp,
                    end_time=event.pass_timestamp,
                    day=target_day,
                )
            else:
                current_range.end_time = event.pass_timestamp

        if current_range is not None:
            ranges.append(current_range)

    return ranges


def aggregate_passes_for_day(target_day: date | None = None) -> Sequence[TrafficLightRange]:
    """Aggregate traffic light passes into continuous ranges for a given day.

    The aggregation groups consecutive passes for the same light and color into
    consolidated ranges. Existing ranges for the day are replaced to keep the
    results idempotent.
    """

    day = _normalize_day(target_day)
    start, end = _day_bounds(day)

    query = (
        TrafficLightPass.query.filter(
            TrafficLightPass.pass_timestamp >= start,
            TrafficLightPass.pass_timestamp < end,
        )
        .order_by(TrafficLightPass.light_identifier, TrafficLightPass.pass_timestamp)
        .all()
    )

    # Clear existing data for the day to avoid stale ranges when re-running the
    # job.
    TrafficLightRange.query.filter(TrafficLightRange.day == day).delete(
        synchronize_session=False
    )

    ranges = _to_ranges(query, day)
    db.session.add_all(ranges)
    db.session.commit()

    current_app.logger.info(
        "Aggregated %d ranges for %d passes on %s", len(ranges), len(query), day.isoformat()
    )

    return ranges


def get_ranges_for_light(light_identifier: str, day: date | None = None) -> List[TrafficLightRange]:
    """Fetch aggregated ranges for a specific light and day (defaults to previous UTC day)."""

    normalized_day = _normalize_day(day)

    return (
        TrafficLightRange.query.filter(
            TrafficLightRange.light_identifier == light_identifier,
            TrafficLightRange.day == normalized_day,
        )
        .order_by(TrafficLightRange.start_time)
        .all()
    )

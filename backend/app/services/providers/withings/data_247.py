import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.config import settings
from app.database import DbSession
from app.repositories import UserConnectionRepository
from app.schemas.enums import HealthScoreCategory, ProviderName, SeriesType
from app.schemas.model_crud.activities import (
    EventRecordCreate,
    EventRecordDetailCreate,
    HealthScoreCreate,
    ScoreComponent,
    TimeSeriesSampleCreate,
)
from app.services.event_record_service import event_record_service
from app.services.health_score_service import health_score_service
from app.services.providers.api_client import make_authenticated_request
from app.services.providers.templates.base_247_data import Base247DataTemplate
from app.services.providers.templates.base_oauth import BaseOAuthTemplate
from app.services.timeseries_service import timeseries_service
from app.utils.structured_logging import log_structured

logger = logging.getLogger(__name__)


WITHINGS_MEASURE_TYPES: dict[int, SeriesType] = {
    1: SeriesType.weight,
    5: SeriesType.lean_body_mass,
    6: SeriesType.body_fat_percentage,
    8: SeriesType.body_fat_mass,
    9: SeriesType.blood_pressure_diastolic,
    10: SeriesType.blood_pressure_systolic,
    11: SeriesType.heart_rate,
    12: SeriesType.body_temperature,
    54: SeriesType.oxygen_saturation,
    71: SeriesType.body_temperature,
    73: SeriesType.skin_temperature,
    76: SeriesType.skeletal_muscle_mass,
}

SLEEP_DATA_FIELDS = ",".join(
    [
        "total_timeinbed",
        "total_sleep_time",
        "asleepduration",
        "wakeupduration",
        "lightsleepduration",
        "deepsleepduration",
        "remsleepduration",
        "wakeupcount",
        "sleep_efficiency",
        "sleep_latency",
        "wakeup_latency",
        "waso",
        "nb_rem_episodes",
        "out_of_bed_count",
        "durationtosleep",
        "durationtowakeup",
        "hr_average",
        "hr_min",
        "hr_max",
        "rr_average",
        "rr_min",
        "rr_max",
        "breathing_disturbances_intensity",
        "breathing_quality_assessment",
        "snoring",
        "snoringepisodecount",
        "sleep_score",
        "night_events",
        "mvt_score_avg",
        "mvt_active_duration",
        "rmssd_start_avg",
        "rmssd_end_avg",
        "chest_movement_rate_wellness_average",
        "chest_movement_rate_wellness_min",
        "chest_movement_rate_wellness_max",
        "breathing_sounds",
        "breathing_sounds_episode_count",
        "core_body_temperature_min",
        "core_body_temperature_max",
        "core_body_temperature_avg",
        "core_body_temperature_status",
    ]
)

INTRADAY_DATA_FIELDS = ",".join(
    [
        "heart_rate",
        "spo2_auto",
        "core_body_temperature",
        "rr",
        "rmssd",
        "sdnn1",
        "hrv_quality",
        "chest_movement_rate",
    ]
)


class Withings247Data(Base247DataTemplate):
    """Withings pull-based clinical metrics and daily activity sync."""

    def __init__(
        self,
        provider_name: str,
        api_base_url: str,
        oauth: BaseOAuthTemplate,
    ):
        super().__init__(provider_name, api_base_url, oauth)
        self.connection_repo = UserConnectionRepository()

    def _make_api_request(
        self,
        db: DbSession,
        user_id: UUID,
        endpoint: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        response = make_authenticated_request(
            db=db,
            user_id=user_id,
            connection_repo=self.connection_repo,
            oauth=self.oauth,
            api_base_url=self.api_base_url,
            provider_name=self.provider_name,
            endpoint=endpoint,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            form_data=params,
        )
        if not isinstance(response, dict):
            raise HTTPException(status_code=502, detail="Unexpected Withings API response")
        status = response.get("status")
        if status not in (0, "0", None):
            raise HTTPException(status_code=502, detail=f"Withings API error: {response}")
        return response.get("body", response)

    def get_sleep_data(
        self,
        db: DbSession,
        user_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        body = self._make_api_request(
            db,
            user_id,
            "/v2/sleep",
            {
                "action": "getsummary",
                "startdateymd": start_time.strftime("%Y-%m-%d"),
                "enddateymd": end_time.strftime("%Y-%m-%d"),
                "data_fields": SLEEP_DATA_FIELDS,
            },
        )
        return body.get("series", [])

    def normalize_sleep(
        self,
        raw_sleep: list[dict[str, Any]],
        user_id: UUID,
    ) -> list[tuple[EventRecordCreate, EventRecordDetailCreate, HealthScoreCreate | None]]:
        normalized: list[tuple[EventRecordCreate, EventRecordDetailCreate, HealthScoreCreate | None]] = []
        for item in raw_sleep:
            start_dt = self._recorded_at_from_epoch(item.get("startdate"))
            end_dt = self._recorded_at_from_epoch(item.get("enddate"))
            if not start_dt or not end_dt:
                continue

            data = item.get("data") or {}
            sleep_id = uuid4()
            external_id = str(item.get("id")) if item.get("id") is not None else None
            duration_seconds = max(0, int((end_dt - start_dt).total_seconds()))

            wakeup_seconds = self._int_value(data.get("wakeupduration")) or 0
            light_seconds = self._int_value(data.get("lightsleepduration")) or 0
            deep_seconds = self._int_value(data.get("deepsleepduration")) or 0
            rem_seconds = self._int_value(data.get("remsleepduration")) or 0
            total_sleep_seconds = (
                light_seconds
                + deep_seconds
                + rem_seconds
                or self._int_value(data.get("total_sleep_time"))
                or self._int_value(data.get("asleepduration"))
                or 0
            )
            time_in_bed_seconds = (
                self._int_value(data.get("total_timeinbed")) or duration_seconds or (total_sleep_seconds + wakeup_seconds)
            )

            record = EventRecordCreate(
                id=sleep_id,
                category="sleep",
                type="sleep_session",
                source_name="Withings",
                duration_seconds=duration_seconds or None,
                start_datetime=start_dt,
                end_datetime=end_dt,
                external_id=external_id,
                provider=ProviderName.WITHINGS,
                source=ProviderName.WITHINGS.value,
                user_id=user_id,
            )
            detail = EventRecordDetailCreate(
                record_id=sleep_id,
                sleep_total_duration_minutes=total_sleep_seconds // 60 if total_sleep_seconds else None,
                sleep_time_in_bed_minutes=time_in_bed_seconds // 60 if time_in_bed_seconds else None,
                sleep_efficiency_score=self._decimal_value(data.get("sleep_efficiency"))
                or self._decimal_value(data.get("sleep_score")),
                sleep_deep_minutes=deep_seconds // 60 if deep_seconds else None,
                sleep_light_minutes=light_seconds // 60 if light_seconds else None,
                sleep_rem_minutes=rem_seconds // 60 if rem_seconds else None,
                sleep_awake_minutes=wakeup_seconds // 60 if wakeup_seconds else None,
            )

            score: HealthScoreCreate | None = None
            sleep_score = self._int_value(data.get("sleep_score"))
            if sleep_score is not None:
                components = {
                    key: ScoreComponent(value=value)
                    for key, value in {
                        "wakeup_count": self._int_value(data.get("wakeupcount")),
                        "heart_rate_average": self._int_value(data.get("hr_average")),
                        "respiratory_rate_average": self._int_value(data.get("rr_average")),
                        "breathing_disturbances_intensity": self._int_value(
                            data.get("breathing_disturbances_intensity")
                        ),
                    }.items()
                    if value is not None
                }
                score = HealthScoreCreate(
                    id=uuid4(),
                    user_id=user_id,
                    provider=ProviderName.WITHINGS,
                    category=HealthScoreCategory.SLEEP,
                    value=sleep_score,
                    recorded_at=start_dt,
                    components=components or None,
                    sleep_record_id=sleep_id,
                )

            normalized.append((record, detail, score))
        return normalized

    def get_recovery_data(
        self,
        db: DbSession,
        user_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        return []

    def normalize_recovery(self, raw_recovery: dict[str, Any], user_id: UUID) -> dict[str, Any]:
        return raw_recovery

    def get_activity_samples(
        self,
        db: DbSession,
        user_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        body = self._make_api_request(
            db,
            user_id,
            "/measure",
            {
                "action": "getmeas",
                "category": "1",
                "startdate": str(int(start_time.timestamp())),
                "enddate": str(int(end_time.timestamp())),
                "meastypes": ",".join(str(k) for k in sorted(WITHINGS_MEASURE_TYPES)),
            },
        )
        return body.get("measuregrps", [])

    def normalize_activity_samples(
        self,
        raw_samples: list[dict[str, Any]],
        user_id: UUID,
    ) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for group in raw_samples:
            recorded_at = self._recorded_at_from_epoch(group.get("date"))
            if not recorded_at:
                continue
            external_id = str(group.get("grpid")) if group.get("grpid") is not None else None
            for measure in group.get("measures", []):
                series_type = WITHINGS_MEASURE_TYPES.get(measure.get("type"))
                if not series_type:
                    continue
                value = self._measure_value(measure)
                if value is None:
                    continue
                if not self._is_valid_measure_value(series_type, value):
                    continue
                result.setdefault(series_type.value, []).append(
                    {
                        "recorded_at": recorded_at,
                        "value": value,
                        "external_id": external_id,
                    }
                )
        return result

    def get_daily_activity_statistics(
        self,
        db: DbSession,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        body = self._make_api_request(
            db,
            user_id,
            "/v2/measure",
            {
                "action": "getactivity",
                "startdateymd": start_date.strftime("%Y-%m-%d"),
                "enddateymd": end_date.strftime("%Y-%m-%d"),
                "data_fields": "steps,distance,calories,totalcalories,hr_average",
            },
        )
        return body.get("activities", [])

    def get_intraday_activity_samples(
        self,
        db: DbSession,
        user_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        samples: list[dict[str, Any]] = []
        cursor = start_time
        while cursor < end_time:
            chunk_end = min(cursor + timedelta(hours=24), end_time)
            body = self._make_api_request(
                db,
                user_id,
                "/v2/measure",
                {
                    "action": "getintradayactivity",
                    "startdate": str(int(cursor.timestamp())),
                    "enddate": str(int(chunk_end.timestamp())),
                    "data_fields": INTRADAY_DATA_FIELDS,
                },
            )
            series = body.get("series", {})
            if isinstance(series, dict):
                for timestamp, values in series.items():
                    if isinstance(values, dict):
                        samples.append({"timestamp": timestamp, **values})
            cursor = chunk_end
        return samples

    def normalize_intraday_activity_samples(
        self,
        raw_samples: list[dict[str, Any]],
        user_id: UUID,
    ) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        mapping = {
            "heart_rate": SeriesType.heart_rate,
            "spo2_auto": SeriesType.oxygen_saturation,
            "core_body_temperature": SeriesType.body_temperature,
            "rr": SeriesType.respiratory_rate,
            "rmssd": SeriesType.heart_rate_variability_rmssd,
            "sdnn1": SeriesType.heart_rate_variability_sdnn,
            "chest_movement_rate": SeriesType.respiratory_rate,
        }
        for item in raw_samples:
            recorded_at = self._recorded_at_from_epoch(item.get("timestamp"))
            if not recorded_at:
                continue
            for field, series_type in mapping.items():
                value = self._decimal_value(item.get(field))
                if value is None:
                    continue
                if not self._is_valid_measure_value(series_type, value):
                    continue
                result.setdefault(series_type.value, []).append(
                    {
                        "recorded_at": recorded_at,
                        "value": value,
                        "external_id": f"intraday:{field}:{item.get('timestamp')}",
                    }
                )
        return result

    def normalize_daily_activity(
        self,
        raw_stats: dict[str, Any],
        user_id: UUID,
    ) -> dict[str, Any]:
        day = raw_stats.get("date")
        recorded_at = None
        if day:
            try:
                recorded_at = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                recorded_at = None
        return {
            "recorded_at": recorded_at,
            "steps": raw_stats.get("steps"),
            "distance": raw_stats.get("distance"),
            "energy": raw_stats.get("calories"),
            "total_energy": raw_stats.get("totalcalories"),
            "heart_rate": raw_stats.get("hr_average"),
            "external_id": day,
        }

    def load_and_save_all(
        self,
        db: DbSession,
        user_id: UUID,
        start_time: datetime,
        end_time: datetime,
        is_first_sync: bool = False,
    ) -> dict[str, int]:
        measure_groups = self.get_activity_samples(db, user_id, start_time, end_time)
        daily_activity = self.get_daily_activity_statistics(db, user_id, start_time, end_time)
        intraday_activity: list[dict[str, Any]] = []
        try:
            intraday_activity = self.get_intraday_activity_samples(db, user_id, start_time, end_time)
        except Exception as e:
            log_structured(
                logger,
                "warning",
                "Withings intraday activity sync skipped",
                provider=self.provider_name,
                user_id=str(user_id),
                error=str(e),
            )

        samples = self._build_measure_samples(user_id, measure_groups)
        samples.extend(self._build_daily_activity_samples(user_id, daily_activity))
        samples.extend(self._build_intraday_activity_samples(user_id, intraday_activity))

        if samples:
            timeseries_service.bulk_create_samples(db, samples)

        sleep_sessions: list[dict[str, Any]] = []
        try:
            sleep_sessions = self.get_sleep_data(db, user_id, start_time, end_time)
        except Exception as e:
            log_structured(
                logger,
                "warning",
                "Withings sleep sync skipped",
                provider=self.provider_name,
                user_id=str(user_id),
                error=str(e),
            )

        sleep_count = self._save_sleep_sessions(db, user_id, sleep_sessions)
        if samples or sleep_count:
            db.commit()

        return {
            "samples": len(samples),
            "measure_groups": len(measure_groups),
            "daily_activity_days": len(daily_activity),
            "intraday_activity_samples": len(intraday_activity),
            "sleep_sessions": sleep_count,
        }

    def _save_sleep_sessions(
        self,
        db: DbSession,
        user_id: UUID,
        raw_sleep: list[dict[str, Any]],
    ) -> int:
        count = 0
        scores: list[HealthScoreCreate] = []
        for record, detail, score in self.normalize_sleep(raw_sleep, user_id):
            try:
                event_record_service.create_or_merge_sleep(db, user_id, record, detail, settings.sleep_end_gap_minutes)
                count += 1
                if score:
                    scores.append(score)
            except Exception as e:
                log_structured(
                    logger,
                    "warning",
                    "Failed to save Withings sleep session",
                    provider=self.provider_name,
                    user_id=str(user_id),
                    error=str(e),
                )
        if scores:
            health_score_service.bulk_create(db, scores)
        return count

    def _build_measure_samples(
        self,
        user_id: UUID,
        measure_groups: list[dict[str, Any]],
    ) -> list[TimeSeriesSampleCreate]:
        samples: list[TimeSeriesSampleCreate] = []
        normalized = self.normalize_activity_samples(measure_groups, user_id)
        for series_name, items in normalized.items():
            series_type = SeriesType(series_name)
            for item in items:
                samples.append(
                    TimeSeriesSampleCreate(
                        id=uuid4(),
                        user_id=user_id,
                        source=self.provider_name,
                        provider=self.provider_name,
                        recorded_at=item["recorded_at"],
                        value=item["value"],
                        series_type=series_type,
                        external_id=item.get("external_id"),
                    )
                )
        return samples

    def _build_intraday_activity_samples(
        self,
        user_id: UUID,
        intraday_activity: list[dict[str, Any]],
    ) -> list[TimeSeriesSampleCreate]:
        samples: list[TimeSeriesSampleCreate] = []
        normalized = self.normalize_intraday_activity_samples(intraday_activity, user_id)
        for series_name, items in normalized.items():
            series_type = SeriesType(series_name)
            for item in items:
                samples.append(
                    TimeSeriesSampleCreate(
                        id=uuid4(),
                        user_id=user_id,
                        source=self.provider_name,
                        provider=self.provider_name,
                        recorded_at=item["recorded_at"],
                        value=item["value"],
                        series_type=series_type,
                        external_id=item.get("external_id"),
                    )
                )
        return samples

    def _build_daily_activity_samples(
        self,
        user_id: UUID,
        daily_activity: list[dict[str, Any]],
    ) -> list[TimeSeriesSampleCreate]:
        samples: list[TimeSeriesSampleCreate] = []
        mapping = {
            "steps": SeriesType.steps,
            "distance": SeriesType.distance_walking_running,
            "energy": SeriesType.energy,
            "heart_rate": SeriesType.heart_rate,
        }
        for item in daily_activity:
            normalized = self.normalize_daily_activity(item, user_id)
            recorded_at = normalized.get("recorded_at")
            if not recorded_at:
                continue
            for field, series_type in mapping.items():
                value = normalized.get(field)
                if value is None:
                    continue
                try:
                    samples.append(
                        TimeSeriesSampleCreate(
                            id=uuid4(),
                            user_id=user_id,
                            source=self.provider_name,
                            provider=self.provider_name,
                            recorded_at=recorded_at,
                            value=Decimal(str(value)),
                            series_type=series_type,
                            external_id=normalized.get("external_id"),
                        )
                    )
                except Exception as e:
                    log_structured(
                        logger,
                        "warning",
                        "Failed to normalize Withings daily activity sample",
                        provider=self.provider_name,
                        field=field,
                        error=str(e),
                    )
        return samples

    def _recorded_at_from_epoch(self, value: Any) -> datetime | None:
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

    def _measure_value(self, measure: dict[str, Any]) -> Decimal | None:
        try:
            raw_value = Decimal(str(measure["value"]))
            unit = int(measure.get("unit", 0))
            return raw_value * (Decimal(10) ** unit)
        except Exception:
            return None

    def _decimal_value(self, value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def _int_value(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(Decimal(str(value)))
        except Exception:
            return None

    def _is_valid_measure_value(self, series_type: SeriesType, value: Decimal) -> bool:
        if series_type == SeriesType.oxygen_saturation:
            return Decimal("50") <= value <= Decimal("100")
        if series_type == SeriesType.heart_rate:
            return value > 0
        if series_type in (SeriesType.body_temperature, SeriesType.skin_temperature):
            return Decimal("20") <= value <= Decimal("45")
        return True

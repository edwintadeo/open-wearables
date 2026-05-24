from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.schemas.enums import SeriesType
from app.services.providers.withings import data_247 as withings_data_module
from app.services.providers.withings.data_247 import Withings247Data


def _data_247() -> Withings247Data:
    return Withings247Data(
        provider_name="withings",
        api_base_url="https://wbsapi.withings.net",
        oauth=None,  # type: ignore[arg-type]
    )


def test_normalize_measure_groups() -> None:
    user_id = uuid4()
    normalized = _data_247().normalize_activity_samples(
        [
            {
                "grpid": 1001,
                "date": 1_700_000_000,
                "measures": [
                    {"type": 1, "value": 82500, "unit": -3},
                    {"type": 10, "value": 121, "unit": 0},
                    {"type": 9, "value": 78, "unit": 0},
                    {"type": 12, "value": 366, "unit": -1},
                    {"type": 54, "value": 0, "unit": 0},
                    {"type": 54, "value": 983, "unit": -1},
                    {"type": 73, "value": 325, "unit": -1},
                    {"type": 999, "value": 1, "unit": 0},
                ],
            }
        ],
        user_id,
    )

    assert normalized[SeriesType.weight.value][0]["value"] == Decimal("82.500")
    assert normalized[SeriesType.blood_pressure_systolic.value][0]["value"] == Decimal("121")
    assert normalized[SeriesType.blood_pressure_diastolic.value][0]["value"] == Decimal("78")
    assert normalized[SeriesType.body_temperature.value][0]["value"] == Decimal("36.6")
    assert normalized[SeriesType.oxygen_saturation.value][0]["value"] == Decimal("98.3")
    assert normalized[SeriesType.skin_temperature.value][0]["value"] == Decimal("32.5")
    assert SeriesType.blood_glucose.value not in normalized


def test_normalize_sleep_summary() -> None:
    user_id = uuid4()
    normalized = _data_247().normalize_sleep(
        [
            {
                "id": 123,
                "startdate": 1_700_000_000,
                "enddate": 1_700_028_800,
                "data": {
                    "lightsleepduration": 14_400,
                    "deepsleepduration": 5_400,
                    "remsleepduration": 7_200,
                    "wakeupduration": 1_800,
                    "wakeupcount": 2,
                    "sleep_score": 82,
                    "hr_average": 58,
                    "rr_average": 14,
                    "breathing_disturbances_intensity": 8,
                },
            }
        ],
        user_id,
    )

    record, detail, score = normalized[0]
    assert record.category == "sleep"
    assert record.source_name == "Withings"
    assert record.external_id == "123"
    assert detail.sleep_total_duration_minutes == 450
    assert detail.sleep_time_in_bed_minutes == 480
    assert detail.sleep_deep_minutes == 90
    assert detail.sleep_light_minutes == 240
    assert detail.sleep_rem_minutes == 120
    assert detail.sleep_awake_minutes == 30
    assert detail.sleep_efficiency_score == Decimal("82")
    assert score is not None
    assert score.value == 82
    assert score.components is not None
    assert score.components["breathing_disturbances_intensity"].value == 8


def test_normalize_daily_activity() -> None:
    normalized = _data_247().normalize_daily_activity(
        {
            "date": "2026-05-23",
            "steps": 6800,
            "distance": 5200,
            "calories": 410,
            "totalcalories": 2100,
            "hr_average": 72,
        },
        uuid4(),
    )

    assert normalized["recorded_at"] == datetime(2026, 5, 23, tzinfo=timezone.utc)
    assert normalized["steps"] == 6800
    assert normalized["distance"] == 5200
    assert normalized["energy"] == 410
    assert normalized["heart_rate"] == 72


def test_withings_requests_use_form_encoded_post(monkeypatch) -> None:
    captured = {}

    def fake_make_authenticated_request(**kwargs):
        captured.update(kwargs)
        return {"status": 0, "body": {"ok": True}}

    monkeypatch.setattr(withings_data_module, "make_authenticated_request", fake_make_authenticated_request)

    body = _data_247()._make_api_request(  # noqa: SLF001
        db=None,  # type: ignore[arg-type]
        user_id=uuid4(),
        endpoint="/measure",
        params={"action": "getmeas"},
    )

    assert body == {"ok": True}
    assert captured["method"] == "POST"
    assert captured["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert captured["form_data"] == {"action": "getmeas"}
    assert "params" not in captured or captured["params"] is None


def test_normalize_intraday_activity_samples_filters_invalid_spo2() -> None:
    user_id = uuid4()
    normalized = _data_247().normalize_intraday_activity_samples(
        [
            {
                "timestamp": 1_700_000_000,
                "heart_rate": 63,
                "spo2_auto": 0,
                "core_body_temperature": 36.8,
                "rr": 14,
                "rmssd": 42,
                "sdnn1": 31,
            },
            {
                "timestamp": 1_700_000_060,
                "spo2_auto": 97,
            },
        ],
        user_id,
    )

    assert normalized[SeriesType.heart_rate.value][0]["value"] == Decimal("63")
    assert normalized[SeriesType.body_temperature.value][0]["value"] == Decimal("36.8")
    assert normalized[SeriesType.respiratory_rate.value][0]["value"] == Decimal("14")
    assert normalized[SeriesType.heart_rate_variability_rmssd.value][0]["value"] == Decimal("42")
    assert normalized[SeriesType.heart_rate_variability_sdnn.value][0]["value"] == Decimal("31")
    assert len(normalized[SeriesType.oxygen_saturation.value]) == 1
    assert normalized[SeriesType.oxygen_saturation.value][0]["value"] == Decimal("97")
